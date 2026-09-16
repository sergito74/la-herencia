"""Parameterized, read-only SQL queries for the Cuentas corrientes module.

Column/table names come from data-model.md. No writes are issued here
(constitution principle II, FR-010).
"""

from __future__ import annotations

from datetime import date

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime


def search_contactos(q: str | None, tipo_contacto: str | None) -> list[dict]:
    """Search contactos by razon social and/or tipo (FR-001, FR-002).

    `DISTINCT` porque un contacto tipo "Multiple" puede tener más de una
    fila asociada en joins usados por otras vistas — acá no hay join, pero
    se mantiene por consistencia con FR-014 y para no exponer duplicados
    si la tabla base llegara a tenerlos.
    """
    where_clauses: list[str] = []
    params: list = []

    if q:
        where_clauses.append("[Razon Social] LIKE ?")
        params.append(f"%{q}%")
    if tipo_contacto:
        where_clauses.append("[Tipo Contacto] = ?")
        params.append(tipo_contacto)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    sql = f"""
        SELECT DISTINCT
            IdContacto AS idContacto,
            [Razon Social] AS razonSocial,
            [Tipo Contacto] AS tipoContacto
        FROM dbo.Contactos
        {where_sql}
        ORDER BY [Razon Social] ASC
    """
    rows = fetch_all(sql, tuple(params))
    return [
        {
            "idContacto": row["idContacto"],
            "razonSocial": row.get("razonSocial"),
            "tipoContacto": row.get("tipoContacto"),
        }
        for row in rows
    ]


def get_saldo(id_contacto: int) -> dict | None:
    """Saldo actual del contacto (FR-003). Fuente de verdad, sin recalcular."""
    sql = """
        SELECT
            IdContacto AS idContacto,
            SaldoParcial AS saldoParcial
        FROM dbo.vw_MovimientosCuenta_Saldo
        WHERE IdContacto = ?
    """
    row = fetch_one(sql, (id_contacto,))
    if row is None:
        return None
    return {"idContacto": row["idContacto"], "saldoParcial": row.get("saldoParcial")}


def get_movimientos(
    id_contacto: int,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """Movimientos de cuenta corriente del contacto (FR-004, FR-005, FR-012, FR-014).

    Deduplicado a nivel SQL vía DISTINCT — necesario para contactos tipo
    "Multiple" per FR-014.
    """
    where_clauses = ["IdContacto = ?"]
    params: list = [id_contacto]

    if fecha_desde:
        where_clauses.append("Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}"

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM (
            SELECT DISTINCT Fecha, Documento, [Nro Documento], Deuda, Credito, Origen, IdOrigen
            FROM dbo.vw_MovimientosCuenta_Base
            {where_sql}
        ) AS dedup
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT DISTINCT
            Fecha AS fecha,
            Documento AS documento,
            [Nro Documento] AS numeroDocumento,
            Deuda AS deuda,
            Credito AS credito,
            Origen AS origenTipo,
            IdOrigen AS idOrigen
        FROM dbo.vw_MovimientosCuenta_Base
        {where_sql}
        ORDER BY Fecha ASC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    movimientos = [
        {
            "fecha": row.get("fecha"),
            "documento": row.get("documento"),
            "numeroDocumento": row.get("numeroDocumento"),
            "deuda": row.get("deuda"),
            "credito": row.get("credito"),
            "origenTipo": row.get("origenTipo"),
            "idOrigen": row.get("idOrigen"),
        }
        for row in rows
    ]
    return movimientos, total


def get_compra_referencia(id_compra: int) -> dict | None:
    """Referencia mínima de una compra para resolver `Origen`/`IdOrigen`."""
    sql = """
        SELECT
            cmp.IdDeuda AS idCompra,
            cmp.[Nro Documento] AS numeroDocumento,
            c.[Razon Social] AS proveedor
        FROM dbo.Compras cmp
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        WHERE cmp.IdDeuda = ?
    """
    return fetch_one(sql, (id_compra,))


def get_bna_referencia(id_movimiento: int) -> dict | None:
    sql = """
        SELECT
            IdMovimientoBNA AS idMovimiento,
            [Fecha / Hora Mov#] AS fecha,
            Importe AS importe
        FROM dbo.[Movimientos BNA]
        WHERE IdMovimientoBNA = ?
    """
    return fetch_one(sql, (id_movimiento,))


def get_galicia_referencia(id_movimiento: int) -> dict | None:
    sql = """
        SELECT
            IdMovimiento AS idMovimiento,
            Fecha AS fecha,
            Débitos AS debitos,
            Créditos AS creditos
        FROM dbo.[Movimientos Galicia]
        WHERE IdMovimiento = ?
    """
    row = fetch_one(sql, (id_movimiento,))
    if row is None:
        return None
    importe = row.get("debitos") or row.get("creditos")
    return {"idMovimiento": row["idMovimiento"], "fecha": row.get("fecha"), "importe": importe}


def get_efectivo_referencia(id_pago: int) -> dict | None:
    sql = """
        SELECT
            IdPagoEfectivo AS idMovimiento,
            Fecha AS fecha,
            [Importe imputado] AS importe
        FROM dbo.[Pagos efectivo]
        WHERE IdPagoEfectivo = ?
    """
    return fetch_one(sql, (id_pago,))


def get_valores_recibidos_referencia(id_valor: int) -> dict | None:
    sql = """
        SELECT
            IdValor AS idMovimiento,
            [Fecha Emision] AS fecha,
            Importe AS importe
        FROM dbo.[Valores Recibidos]
        WHERE IdValor = ?
    """
    return fetch_one(sql, (id_valor,))
