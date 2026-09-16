"""Heuristic origin reference: tesoreria movimiento -> compra candidata(s).

Pure, read-only matching by IdContacto + fecha + importe against
dbo.Compras (via vw_MovimientosCuenta_Base for the debt amount actually
posted for that compra). No explicit foreign key links tesoreria to
compras, so this never picks a single candidate by default (FR-005).

`valores-propios` has no contact column at all (confirmed against
INFORMATION_SCHEMA 2026-09-16) and MUST always return "sin_coincidencia"
without running any query (clarification 2026-09-16).
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import fetch_all
from src.db.params import as_sql_datetime
from src.features.tesoreria.repository import get_movimiento

SIN_COINCIDENCIA = "sin_coincidencia"
COINCIDENCIA_UNICA = "coincidencia_unica"
AMBIGUA = "ambigua"


def _anchor_bna(row: dict) -> tuple[int | None, date | None, float | None]:
    fecha_hora = row.get("fechaHora")
    fecha = fecha_hora.date() if isinstance(fecha_hora, datetime) else fecha_hora
    importe = row.get("importe")
    return row.get("idContacto"), fecha, abs(float(importe)) if importe is not None else None


def _anchor_galicia(row: dict) -> tuple[int | None, date | None, float | None]:
    importe = row.get("debitos") or row.get("creditos")
    return row.get("idContacto"), row.get("fecha"), importe


def _anchor_efectivo(row: dict) -> tuple[int | None, date | None, float | None]:
    return row.get("idContacto"), row.get("fecha"), row.get("importeImputado")


def _anchor_valores_recibidos(row: dict) -> tuple[int | None, date | None, float | None]:
    return row.get("idEmisor"), row.get("fechaEmision"), row.get("importe")


def _anchor_tarjetas(row: dict) -> tuple[int | None, date | None, float | None]:
    return row.get("idContacto"), row.get("fechaCompra"), row.get("importe")


_ANCHOR_BY_MEDIO = {
    "bna": _anchor_bna,
    "galicia": _anchor_galicia,
    "efectivo": _anchor_efectivo,
    "valores-recibidos": _anchor_valores_recibidos,
    "tarjetas": _anchor_tarjetas,
}


def _buscar_candidatas(id_contacto: int, fecha: date, importe: float) -> list[dict]:
    sql = """
        SELECT
            cmp.IdDeuda AS idCompra,
            cmp.[Nro Documento] AS numeroDocumento,
            c.[Razon Social] AS proveedor,
            v.Fecha AS fecha,
            v.Deuda AS importe
        FROM dbo.Compras cmp
        JOIN dbo.vw_MovimientosCuenta_Base v
            ON v.IdOrigen = cmp.IdDeuda AND v.Origen = 'Compras'
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        WHERE cmp.IdContacto = ? AND v.Fecha = ? AND v.Deuda = ?
    """
    return fetch_all(sql, (id_contacto, as_sql_datetime(fecha), importe))


def buscar_referencia(medio: str, id_movimiento: int) -> dict:
    if medio == "valores-propios":
        return {"estado": SIN_COINCIDENCIA, "candidatas": []}

    row = get_movimiento(medio, id_movimiento)
    if row is None:
        return {"estado": SIN_COINCIDENCIA, "candidatas": []}

    id_contacto, fecha, importe = _ANCHOR_BY_MEDIO[medio](row)
    if id_contacto is None or fecha is None or importe is None:
        return {"estado": SIN_COINCIDENCIA, "candidatas": []}

    # pyodbc cannot bind Decimal parameters reliably (SQLBindParameter);
    # normalize to float before querying.
    candidatas = _buscar_candidatas(id_contacto, fecha, float(importe))

    if not candidatas:
        estado = SIN_COINCIDENCIA
    elif len(candidatas) == 1:
        estado = COINCIDENCIA_UNICA
    else:
        estado = AMBIGUA

    return {"estado": estado, "candidatas": candidatas}
