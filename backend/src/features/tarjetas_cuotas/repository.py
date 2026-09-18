"""Parameterized SQL queries for the Tarjetas_Cuotas module — **solo
lectura** desde 2026-09-19 (feedback del usuario, punto 5): la estructura
real (`[Tarjetas de Credito]`/`[Cuotas Tarjetas de Credito]`) está
obsoleta (18 compras, ninguna posterior a diciembre de 2015 — confirmado
contra `WC`). El mecanismo de financiación en cuotas vigente (AgroNacion)
factura cada cuota como una línea repetida en el resumen mensual
(`tarjetas_resumenes`, `CreditoContingente`/`InteresPagoDiferido` por
línea), no acá. Se conserva como catálogo histórico de referencia.
`Cobrado` es `nvarchar(1)` ('S'/'N'), no `bit` — mapeado explícitamente.
"""

from __future__ import annotations

from datetime import date

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime


def _cobrado_bool(valor) -> bool:
    return valor == "S"


def search_compras(
    id_contacto: int | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """Sin ningún filtro, no ejecuta la query principal (devuelve vacío)."""
    if not (id_contacto or fecha_desde or fecha_hasta):
        return [], 0

    where_clauses: list[str] = []
    params: list = []
    if id_contacto:
        where_clauses.append("t.IdContacto = ?")
        params.append(id_contacto)
    if fecha_desde:
        where_clauses.append("t.Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("t.Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}"

    total_row = fetch_one(
        f"SELECT COUNT(*) AS total FROM dbo.[Tarjetas de Credito] t {where_sql}", tuple(params)
    )
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            t.IdPagoTarjeta AS idPagoTarjeta, t.IdContacto AS idContacto, c.[Razon Social] AS contacto,
            t.Fecha AS fecha, t.[Nro Comprobante] AS nroComprobante, t.Cuotas AS cantidadCuotas
        FROM dbo.[Tarjetas de Credito] t
        LEFT JOIN dbo.Contactos c ON c.IdContacto = t.IdContacto
        {where_sql}
        ORDER BY t.Fecha DESC, t.IdPagoTarjeta DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    items = []
    for row in rows:
        cuotas = get_cuotas(row["idPagoTarjeta"])
        cobradas = sum(1 for c in cuotas if c["cobrado"])
        items.append(
            {
                **row,
                "cuotasCobradas": cobradas,
                "cuotasPendientes": len(cuotas) - cobradas,
            }
        )
    return items, total


def get_detalle(id_pago_tarjeta: int) -> dict | None:
    sql = """
        SELECT
            t.IdPagoTarjeta AS idPagoTarjeta, t.IdContacto AS idContacto, c.[Razon Social] AS contacto,
            t.Fecha AS fecha, t.[Nro Comprobante] AS nroComprobante, t.Cuotas AS cantidadCuotas
        FROM dbo.[Tarjetas de Credito] t
        LEFT JOIN dbo.Contactos c ON c.IdContacto = t.IdContacto
        WHERE t.IdPagoTarjeta = ?
    """
    return fetch_one(sql, (id_pago_tarjeta,))


def get_cuotas(id_pago_tarjeta: int) -> list[dict]:
    sql = """
        SELECT
            IdAuto AS idCuota, [Cuota nro] AS numeroCuota, [Fecha Vencimiento] AS fechaVencimiento,
            Importe AS importe, Cobrado AS cobrado
        FROM dbo.[Cuotas Tarjetas de Credito]
        WHERE IdPagoTarjeta = ?
        ORDER BY [Cuota nro] ASC
    """
    rows = fetch_all(sql, (id_pago_tarjeta,))
    return [{**row, "cobrado": _cobrado_bool(row["cobrado"])} for row in rows]
