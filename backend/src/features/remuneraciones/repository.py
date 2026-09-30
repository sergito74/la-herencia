"""SQL queries for the Remuneraciones module — lectura y alta (028).

`importe` se computa en SQL como haberes menos descuentos (no existe una
columna "total" en la tabla origen) — ver `calcular_importe_neto` y
`specs/028-alta-liquidacion-remuneraciones/research.md` §1.
"""

from __future__ import annotations

import glob
import re
from pathlib import Path

from src.db.connection import execute_insert_returning_id, execute_write, fetch_all, fetch_one
from src.db.pagination import offset_for
from src.features.remuneraciones.schemas import NuevaLiquidacionRequest

# Columnas monetarias reales de dbo.Remuneraciones, siempre cargadas en
# positivo (confirmado contra datos reales 2026-09-30, ej. Armando Oscar
# Mori: Sueldo basico=85096.38, Jubilacion=18631.02 en positivo) — los
# "haberes" suman al neto, los "descuentos" restan. Misma fórmula que ya
# usa `vw_MovimientosCuenta_Base` (rama Remuneraciones) para la cuenta
# corriente del empleado; antes de esta corrección, `_IMPORTE_SQL` sumaba
# los descuentos en vez de restarlos (bug real, FR-015).
_CONCEPTOS_HABERES = (
    "[Sueldo basico]",
    "Antiguedad",
    "[Adic futuros aumentos]",
    "[Dia Gremio]",
    "Aguinaldo",
    "Vacaciones",
    "Ajuste",
    "[Ajuste No Remunerativo]",
    "Redondeo",
    "[Bonificacion adicional]",
)
_CONCEPTOS_DESCUENTOS = (
    "Jubilacion",
    "[Ley 19032]",
    "[Obra Social]",
    "[Obra Social Acuerdos]",
    "[Aporte Sindical]",
    "[Servicio de Sepelio]",
)
_CONCEPTOS_MONETARIOS = _CONCEPTOS_HABERES + _CONCEPTOS_DESCUENTOS

_IMPORTE_SQL = " + ".join(f"ISNULL(r.{col}, 0)" for col in _CONCEPTOS_HABERES) + " - (" + (
    " + ".join(f"ISNULL(r.{col}, 0)" for col in _CONCEPTOS_DESCUENTOS)
) + ")"


def calcular_importe_neto(conceptos: dict) -> float:
    """Suma de haberes menos suma de descuentos — ambos siempre positivos
    en la entrada (research.md §1). `conceptos` usa las claves reales de
    columna (con corchetes, ej. "[Sueldo basico]"), mismo formato que
    `_CONCEPTOS_MONETARIOS`, para poder reusarse tanto con filas de SQL
    como con un `NuevaLiquidacionRequest` ya mapeado a columnas."""
    haberes = sum(float(conceptos.get(c) or 0) for c in _CONCEPTOS_HABERES)
    descuentos = sum(float(conceptos.get(c) or 0) for c in _CONCEPTOS_DESCUENTOS)
    return haberes - descuentos


# Campo de NuevaLiquidacionRequest -> columna real de dbo.Remuneraciones.
_REQUEST_A_COLUMNA = {
    "sueldoBasico": "[Sueldo basico]",
    "antiguedad": "Antiguedad",
    "adicFuturosAumentos": "[Adic futuros aumentos]",
    "diaGremio": "[Dia Gremio]",
    "aguinaldo": "Aguinaldo",
    "vacaciones": "Vacaciones",
    "ajuste": "Ajuste",
    "ajusteNoRemunerativo": "[Ajuste No Remunerativo]",
    "redondeo": "Redondeo",
    "bonificacionAdicional": "[Bonificacion adicional]",
    "jubilacion": "Jubilacion",
    "ley19032": "[Ley 19032]",
    "obraSocial": "[Obra Social]",
    "obraSocialAcuerdos": "[Obra Social Acuerdos]",
    "aporteSindical": "[Aporte Sindical]",
    "servicioDeSepelio": "[Servicio de Sepelio]",
}


def existe_contacto_empleado(id_contacto: int) -> bool:
    """FR-001: solo Contactos de tipo Empleado pueden ser sujeto de una
    liquidación nueva — mismo criterio que `existe_contacto_consignatario`
    en `ventas_granos/repository.py`."""
    row = fetch_one(
        "SELECT 1 FROM dbo.Contactos WHERE IdContacto = ? AND [Tipo Contacto] = 'Empleado'",
        (id_contacto,),
    )
    return row is not None


def existe_liquidacion_periodo(id_contacto: int, periodo_liquidado: str) -> int | None:
    """FR-004: coincidencia de texto EXACTO del período (sin normalizar
    mes/año, research.md §3) — devuelve el `IdSalario` ya existente, o
    `None` si no hay ninguno para ese empleado+período."""
    row = fetch_one(
        "SELECT IdSalario FROM dbo.Remuneraciones WHERE IdContacto = ? AND [Periodo liquidado] = ?",
        (id_contacto, periodo_liquidado),
    )
    return row["IdSalario"] if row else None


def crear_liquidacion(request: NuevaLiquidacionRequest) -> dict:
    """Inserta una liquidación nueva contra `WC` (FR-003) y devuelve su
    `idSalario` nuevo junto con el importe neto ya calculado (FR-014)."""
    columnas_concepto = list(_REQUEST_A_COLUMNA.values())
    valores_concepto = [getattr(request, campo) for campo in _REQUEST_A_COLUMNA]

    columnas = ["IdContacto", "[Fecha de pago]", "[Periodo liquidado]", *columnas_concepto]
    placeholders = ", ".join("?" for _ in columnas)
    columnas_sql = ", ".join(columnas)
    sql = (
        f"INSERT INTO dbo.Remuneraciones ({columnas_sql}) "
        f"OUTPUT INSERTED.IdSalario VALUES ({placeholders})"
    )
    params = (request.idContacto, request.fechaPago, request.periodoLiquidado, *valores_concepto)
    id_salario = execute_insert_returning_id(sql, params)

    conceptos = dict(zip(columnas_concepto, valores_concepto, strict=True))
    return {"idSalario": id_salario, "importeNeto": calcular_importe_neto(conceptos)}


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


def nombre_archivo_recibo(fecha_pago, empleado: str) -> str:
    """Nombre estandarizado para un recibo nuevo (028, research.md §2):
    a diferencia del histórico (formatos muy inconsistentes entre años,
    ver `buscar_archivo_recibo`), todo lo que genera esta feature de acá
    en adelante usa un único formato con espacios, que el propio matching
    CamelCase ya resuelve sin ambigüedad."""
    return f"{fecha_pago.year} {fecha_pago.month:02d} {empleado}.pdf"


def guardar_recibo(id_salario: int, fecha_pago, empleado: str, contenido: bytes) -> str:
    """Guarda el PDF del recibo en `CARPETA_RECIBOS/{año}/` y escribe su
    ruta relativa en `dbo.Remuneraciones.Recibo` (FR-006/FR-007) — mismo
    formato ya usado por ~262 registros históricos reales
    (`Personal\\Recibos\\{año}\\{archivo}.pdf`, sin la carpeta base)."""
    if not contenido.startswith(b"%PDF"):
        raise ValueError("El archivo no es un PDF válido.")

    nombre = nombre_archivo_recibo(fecha_pago, empleado)
    carpeta_anio = Path(CARPETA_RECIBOS) / f"{fecha_pago.year}"
    carpeta_anio.mkdir(parents=True, exist_ok=True)
    (carpeta_anio / nombre).write_bytes(contenido)

    ruta_relativa = f"Personal\\Recibos\\{fecha_pago.year}\\{nombre}"
    execute_write(
        "UPDATE dbo.Remuneraciones SET Recibo = ? WHERE IdSalario = ?",
        (ruta_relativa, id_salario),
    )
    return ruta_relativa


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
