"""Parameterized, read-only SQL queries for the Ventas de Hacienda module.

`Retenciones Ventas Hacienda` has no reliable key back to a `Venta
Hacienda` (confirmed against real data — see research.md), so it is
queried independently, never joined to a venta.
"""

from __future__ import annotations

from datetime import date

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime


def search_ventas_hacienda(
    consignatario: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    where_clauses: list[str] = []
    params: list = []

    if consignatario:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{consignatario}%")
    if fecha_desde:
        where_clauses.append("v.Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("v.Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.[Venta Hacienda] v
        LEFT JOIN dbo.Contactos c ON c.IdContacto = v.IdConsignatario
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            v.IdVenta AS idVenta,
            v.Fecha AS fecha,
            c.[Razon Social] AS consignatario,
            v.[Nro documento] AS numeroDocumento
        FROM dbo.[Venta Hacienda] v
        LEFT JOIN dbo.Contactos c ON c.IdContacto = v.IdConsignatario
        {where_sql}
        ORDER BY v.Fecha DESC, v.IdVenta DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    ventas = []
    for row in rows:
        venta = dict(row)
        venta["lineas"] = get_lineas_venta(row["idVenta"])
        ventas.append(venta)
    return ventas, total


def get_lineas_venta(id_venta: int) -> list[dict]:
    sql = """
        SELECT
            d.IdDetalleVenta AS idDetalleVenta,
            c.[Razon Social] AS comprador,
            th.[Tipo de Hacienda] AS tipoHacienda,
            d.Cantidad AS cantidad,
            d.[Unidad de medida] AS unidadMedida,
            d.[Peso Total] AS pesoTotal,
            d.[Precio unitario (A)] AS precioUnitarioA,
            d.[Precio unitario (B)] AS precioUnitarioB
        FROM dbo.[Det_Ventas Hacienda] d
        LEFT JOIN dbo.Contactos c ON c.IdContacto = d.IdComprador
        LEFT JOIN dbo.[Tipo Hacienda] th ON th.IdTipoHacienda = d.IdTipoProducto
        WHERE d.IdVenta = ?
        ORDER BY d.IdDetalleVenta ASC
    """
    return fetch_all(sql, (id_venta,))


def get_venta_hacienda_referencia(id_venta: int) -> dict | None:
    sql = """
        SELECT
            v.IdVenta AS idVenta,
            c.[Razon Social] AS consignatario,
            v.[Nro documento] AS numeroDocumento
        FROM dbo.[Venta Hacienda] v
        LEFT JOIN dbo.Contactos c ON c.IdContacto = v.IdConsignatario
        WHERE v.IdVenta = ?
    """
    return fetch_one(sql, (id_venta,))


def search_retenciones_venta_hacienda(
    contacto: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """Listado independiente — MUST NOT join a `Venta Hacienda` (sin clave confiable)."""
    where_clauses: list[str] = []
    params: list = []

    if contacto:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{contacto}%")
    if fecha_desde:
        where_clauses.append("r.Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("r.Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.[Retenciones Ventas Hacienda] r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            r.Id AS idRetencion,
            r.Fecha AS fecha,
            c.[Razon Social] AS contacto,
            r.Documento AS documento,
            r.[Nro Documento] AS numeroDocumento,
            r.Importe AS importe
        FROM dbo.[Retenciones Ventas Hacienda] r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        {where_sql}
        ORDER BY r.Fecha DESC, r.Id DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return rows, total


def get_retencion_venta_hacienda_referencia(id_retencion: int) -> dict | None:
    sql = """
        SELECT Id AS idRetencion, Documento AS documento, [Nro Documento] AS numeroDocumento, Importe AS importe
        FROM dbo.[Retenciones Ventas Hacienda]
        WHERE Id = ?
    """
    return fetch_one(sql, (id_retencion,))
