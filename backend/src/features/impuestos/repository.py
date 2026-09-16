"""Parameterized, read-only SQL queries for the Impuestos module.

Column/table names come from data-model.md, confirmed against the real
schema (INFORMATION_SCHEMA) on 2026-09-16. No writes are issued here
(constitution principle II, FR-008).
"""

from __future__ import annotations

from datetime import date

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime


def search_impuestos(
    organismo: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    where_clauses: list[str] = []
    params: list = []

    if organismo:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{organismo}%")
    if fecha_desde:
        where_clauses.append("i.Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("i.Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.Impuestos i
        LEFT JOIN dbo.Contactos c ON c.IdContacto = i.IdOrganismo
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            i.IdImpuesto AS idImpuesto,
            i.Fecha AS fecha,
            ti.[Nombre Impuesto] AS tipoImpuesto,
            i.[Periodo liquidado] AS periodoLiquidado,
            i.[Numero de documento] AS numeroDocumento,
            i.Importe AS importe,
            c.IdContacto AS idOrganismo,
            c.[Razon Social] AS organismo
        FROM dbo.Impuestos i
        LEFT JOIN dbo.[Tipo Impuesto] ti ON ti.IdTipoImpuesto = i.IdTipoImpuesto
        LEFT JOIN dbo.Contactos c ON c.IdContacto = i.IdOrganismo
        {where_sql}
        ORDER BY i.Fecha DESC, i.IdImpuesto DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return rows, total


def get_impuesto_referencia(id_impuesto: int) -> dict | None:
    """Referencia mínima de un impuesto para resolver `Origen`/`IdOrigen`."""
    sql = """
        SELECT
            i.IdImpuesto AS idImpuesto,
            ti.[Nombre Impuesto] AS tipoImpuesto,
            i.Importe AS importe
        FROM dbo.Impuestos i
        LEFT JOIN dbo.[Tipo Impuesto] ti ON ti.IdTipoImpuesto = i.IdTipoImpuesto
        WHERE i.IdImpuesto = ?
    """
    return fetch_one(sql, (id_impuesto,))


def search_retenciones(
    contacto: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
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
        FROM dbo.Retenciones r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            r.IdRetencionSQL AS idRetencion,
            r.[Numero Certificado] AS numeroCertificado,
            r.Fecha AS fecha,
            c.IdContacto AS idContacto,
            c.[Razon Social] AS contacto,
            r.Importe AS importe
        FROM dbo.Retenciones r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        {where_sql}
        ORDER BY r.Fecha DESC, r.IdRetencionSQL DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return rows, total


def get_retencion_referencia(id_retencion: int) -> dict | None:
    sql = """
        SELECT IdRetencionSQL AS idRetencion, [Numero Certificado] AS numeroCertificado, Importe AS importe
        FROM dbo.Retenciones
        WHERE IdRetencionSQL = ?
    """
    return fetch_one(sql, (id_retencion,))
