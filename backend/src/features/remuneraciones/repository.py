"""Parameterized, read-only SQL queries for the Remuneraciones module.

`importe` of a liquidación is computed in SQL as the sum of every
monetary concept column on the row (no single "total" column exists in
the source table) — see data-model.md Nota de implementación.
"""

from __future__ import annotations

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
            c.[Razon Social] AS empleado,
            r.IdContacto AS idContacto,
            r.[Fecha de pago] AS fechaPago,
            r.[Periodo liquidado] AS periodoLiquidado,
            ({_IMPORTE_SQL}) AS importe
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
