"""Parameterized, read-only SQL queries for the Remuneraciones module.

`importe` of a liquidación is computed in SQL as the sum of every
monetary concept column on the row (no single "total" column exists in
the source table) — see data-model.md Nota de implementación.
"""

from __future__ import annotations

import glob
import re
from pathlib import Path

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for

_CONCEPTOS_MONETARIOS = (
    "[Sueldo basico]",
    "[Adic futuros aumentos]",
    "Ajuste",
    "Vacaciones",
    "[Dia Gremio]",
    "Antiguedad",
    "[Ajuste No Remunerativo]",
    "Aguinaldo",
    "Jubilacion",
    "[Ley 19032]",
    "[Obra Social]",
    "[Obra Social Acuerdos]",
    "[Aporte Sindical]",
    "[Servicio de Sepelio]",
    "Redondeo",
    "[Bonificacion adicional]",
)

_IMPORTE_SQL = " + ".join(f"ISNULL(r.{col}, 0)" for col in _CONCEPTOS_MONETARIOS)


def search_remuneraciones(
    empleado: str | None,
    periodo_liquidado: str | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    where_clauses: list[str] = []
    params: list = []

    if empleado:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{empleado}%")
    if periodo_liquidado:
        where_clauses.append("r.[Periodo liquidado] = ?")
        params.append(periodo_liquidado)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.Remuneraciones r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            r.IdSalario AS idSalario,
            c.IdContacto AS idContacto,
            c.[Razon Social] AS empleado,
            r.[Fecha de pago] AS fechaPago,
            r.[Periodo liquidado] AS periodoLiquidado,
            ({_IMPORTE_SQL}) AS importe,
            r.Recibo AS recibo
        FROM dbo.Remuneraciones r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        {where_sql}
        ORDER BY r.[Fecha de pago] DESC, r.IdSalario DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return rows, total


def get_remuneracion_referencia(id_salario: int) -> dict | None:
    sql = f"""
        SELECT
            r.IdSalario AS idSalario,
            c.[Razon Social] AS empleado,
            r.[Periodo liquidado] AS periodoLiquidado,
            ({_IMPORTE_SQL}) AS importe
        FROM dbo.Remuneraciones r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        WHERE r.IdSalario = ?
    """
    return fetch_one(sql, (id_salario,))


# Backlog post-025, punto 3: carpeta real donde viven los recibos de
# sueldo escaneados (PDF), confirmada contra el disco 2026-09-30 — un
# archivo por empleado y período dentro de una carpeta por año, siempre
# con prefijo "YYYY MM" pero con el nombre después muy inconsistente entre
# años reales: "2026 01 Armando Mori.pdf" (espacios), "2025 11_MarceloSierra.pdf"
# (guion bajo, nombre pegado), "2019 01_Armando Mori.pdf" (guion bajo +
# espacio), "2023 01_DarioGuinea.PDF" (mayúsculas). Nunca asumir un único
# formato — tokenizar por CamelCase (mayúscula = inicio de palabra) cubre
# los tres casos sin depender del separador.
CARPETA_RECIBOS = r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Personal\Recibos"

_TOKEN_RE = re.compile(r"[A-ZÀ-Þ][a-zà-ÿ]*")


def get_recibo_referencia(id_salario: int) -> dict | None:
    return fetch_one(
        "SELECT r.[Fecha de pago] AS fechaPago, c.[Razon Social] AS empleado "
        "FROM dbo.Remuneraciones r LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto "
        "WHERE r.IdSalario = ?",
        (id_salario,),
    )


def buscar_archivo_recibo(fecha_pago, empleado: str) -> Path | None:
    """Ubica el PDF del recibo en `CARPETA_RECIBOS` para una liquidación.

    El nombre del archivo no siempre coincide exacto con la [Razon Social]
    del contacto (ej. "Armando Mori" en el archivo vs "Armando Oscar Mori"
    en Contactos) — se resuelve tokenizando ambos por CamelCase (cada
    palabra con mayúscula inicial) y exigiendo que todos los tokens del
    archivo aparezcan como palabra completa entre los tokens del empleado.
    Mismo criterio que `tesoreria/matching.py::_resolver_contacto_por_texto`:
    nunca elige uno al azar — si hay 0 o más de 1 candidato, devuelve None.
    """
    patron = str(Path(CARPETA_RECIBOS) / f"{fecha_pago.year}" / f"{fecha_pago.year} {fecha_pago.month:02d}*.pdf")
    candidatos = glob.glob(patron)
    tokens_empleado = {t.lower() for t in _TOKEN_RE.findall(empleado)}
    coincidencias = []
    for ruta in candidatos:
        tokens_archivo = [t.lower() for t in _TOKEN_RE.findall(Path(ruta).stem)]
        if tokens_archivo and all(t in tokens_empleado for t in tokens_archivo):
            coincidencias.append(ruta)
    if len(coincidencias) != 1:
        return None
    return Path(coincidencias[0])


def search_pagos_remuneracion(page: int, page_size: int) -> tuple[list[dict], int]:
    """Pagos de remuneraciones, como listado independiente.

    Corrección 2026-09-17: `Pagos Remuneraciones.IdEmpleado` NO es una FK
    hacia `Contactos` — confirmado contra datos reales (rango 1-6,
    resuelve a contactos tipo "Proveedor", mientras que los empleados
    reales de `Remuneraciones.IdContacto` van de 46 a 632). No existe
    vínculo confiable hacia un empleado ni hacia una liquidación
    específica (constitution principio IV: no inventar trazabilidad
    donde los datos no la respaldan). Ver research.md.
    """
    count_row = fetch_one("SELECT COUNT(*) AS total FROM dbo.[Pagos Remuneraciones]")
    total = count_row["total"] if count_row else 0

    offset = offset_for(page, page_size)
    sql = """
        SELECT
            IdPago AS idPago,
            Fecha AS fecha,
            Cuenta AS cuenta,
            Caja AS caja,
            [Importe imputado] AS importe
        FROM dbo.[Pagos Remuneraciones]
        ORDER BY Fecha DESC, IdPago DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(sql, (offset, page_size))
    return rows, total
