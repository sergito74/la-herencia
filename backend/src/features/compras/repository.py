"""Parameterized, read-only SQL queries for the Compras module.

Column/table names come from data-model.md, confirmed against the real
schema (INFORMATION_SCHEMA) on 2026-09-16. No writes are issued here
(constitution principle II, FR-010).
"""

from __future__ import annotations

from datetime import date

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for


def _row_to_compra(row: dict) -> dict:
    return {
        "idCompra": row["idCompra"],
        "fecha": row["fecha"],
        "proveedor": {
            "idContacto": row["idContacto"],
            "razonSocial": row["razonSocial"],
        }
        if row.get("idContacto") is not None
        else None,
        "tipoDocumento": row["tipoDocumento"],
        "numeroDocumento": row["numeroDocumento"],
    }


def search_compras(
    proveedor: str | None,
    numero_documento: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """Search/list compras with optional filters, ordered by fecha desc."""
    where_clauses: list[str] = []
    params: list = []

    if proveedor:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{proveedor}%")
    if numero_documento:
        where_clauses.append("cmp.[Nro Documento] LIKE ?")
        params.append(f"%{numero_documento}%")
    if fecha_desde:
        where_clauses.append("cmp.Fecha >= ?")
        params.append(fecha_desde)
    if fecha_hasta:
        where_clauses.append("cmp.Fecha <= ?")
        params.append(fecha_hasta)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.Compras cmp
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            cmp.IdDeuda AS idCompra,
            cmp.Fecha AS fecha,
            c.IdContacto AS idContacto,
            c.[Razon Social] AS razonSocial,
            cmp.[Tipo documento] AS tipoDocumento,
            cmp.[Nro Documento] AS numeroDocumento
        FROM dbo.Compras cmp
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        {where_sql}
        ORDER BY cmp.Fecha DESC, cmp.IdDeuda DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return [_row_to_compra(row) for row in rows], total


def get_compra_cabecera(id_compra: int) -> dict | None:
    sql = """
        SELECT
            cmp.IdDeuda AS idCompra,
            cmp.Fecha AS fecha,
            c.IdContacto AS idContacto,
            c.[Razon Social] AS razonSocial,
            cmp.[Tipo documento] AS tipoDocumento,
            cmp.[Nro Documento] AS numeroDocumento,
            cmp.[Conceptos no gravados] AS conceptosNoGravados,
            cmp.[Ingresos Brutos] AS ingresosBrutos
        FROM dbo.Compras cmp
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        WHERE cmp.IdDeuda = ?
    """
    row = fetch_one(sql, (id_compra,))
    if row is None:
        return None
    cabecera = _row_to_compra(row)
    cabecera["conceptosNoGravados"] = row.get("conceptosNoGravados")
    cabecera["ingresosBrutos"] = row.get("ingresosBrutos")
    return cabecera


def get_lineas_compra(id_compra: int) -> list[dict]:
    sql = """
        SELECT
            dc.IdDetalleCompra AS idDetalleCompra,
            dc.[Producto/Servicio] AS productoServicio,
            dc.Cantidad AS cantidad,
            dc.[Precio Unitario] AS precioUnitario,
            dc.IVA AS iva,
            dc.IdRubro AS idRubro,
            r.Rubro AS rubro,
            dc.IdCentroCostos AS idCentroCosto,
            cc.[Centro de costos] AS centroCosto,
            dc.IdDestino AS idDestino,
            d.Destino AS destino,
            dc.IdCampaña AS idCampania,
            dc.Campaña AS campania
        FROM dbo.Det_Compras dc
        LEFT JOIN dbo.Rubros r ON r.IdRubro = dc.IdRubro
        LEFT JOIN dbo.[Centro de costos] cc ON cc.IdCentro = dc.IdCentroCostos
        LEFT JOIN dbo.DestinoCompras d ON d.IdDestino = dc.IdDestino
        WHERE dc.IdCompra = ?
        ORDER BY dc.IdDetalleCompra ASC
    """
    rows = fetch_all(sql, (id_compra,))
    lineas = []
    for row in rows:
        tiene_imputacion = any(
            row.get(key) is not None
            for key in ("idRubro", "idCentroCosto", "idDestino", "idCampania")
        )
        imputacion = None
        if tiene_imputacion:
            imputacion = {
                "idRubro": row.get("idRubro"),
                "rubro": row.get("rubro"),
                "idCentroCosto": row.get("idCentroCosto"),
                "centroCosto": row.get("centroCosto"),
                "idDestino": row.get("idDestino"),
                "destino": row.get("destino"),
                "idCampania": row.get("idCampania"),
                "campania": row.get("campania"),
            }
        lineas.append(
            {
                "idDetalleCompra": row["idDetalleCompra"],
                "productoServicio": row.get("productoServicio"),
                "cantidad": row.get("cantidad"),
                "precioUnitario": row.get("precioUnitario"),
                "iva": row.get("iva"),
                "imputacion": imputacion,
            }
        )
    return lineas


def get_trazabilidad_compra(id_compra: int) -> list[dict]:
    """Movimientos de cuenta corriente/tesorería originados por la compra.

    `IdOrigen = idCompra` en `vw_MovimientosCuenta_Base` (FR-008). Si no hay
    filas, el llamador MUST exponer "sin movimientos asociados" (FR-009).
    """
    sql = """
        SELECT
            Origen AS origenTipo,
            IdOrigen AS idOrigen,
            Documento AS documento,
            Fecha AS fecha,
            Deuda AS deuda,
            Credito AS credito
        FROM dbo.vw_MovimientosCuenta_Base
        WHERE IdOrigen = ?
        ORDER BY Fecha ASC
    """
    rows = fetch_all(sql, (id_compra,))
    movimientos = []
    for row in rows:
        deuda = row.get("deuda")
        credito = row.get("credito")
        if deuda:
            importe, tipo_importe = deuda, "Deuda"
        else:
            importe, tipo_importe = credito, "Credito"
        movimientos.append(
            {
                "origenTipo": row.get("origenTipo"),
                "idOrigen": row["idOrigen"],
                "documento": row.get("documento"),
                "fecha": row.get("fecha"),
                "importe": importe,
                "tipoImporte": tipo_importe,
            }
        )
    return movimientos
