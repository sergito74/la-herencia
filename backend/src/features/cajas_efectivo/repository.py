"""Lecturas 027/038 de caja. Escrituras coordinadas en service/operaciones.py."""

from __future__ import annotations

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for


def _f(value) -> float:
    return float(value) if value is not None else 0.0


def calcular_saldo(caja: str) -> float:
    fila = fetch_one(
        "SELECT SUM(Importe) AS saldo FROM dbo.MovimientosCajaEfectivo WHERE Caja = ? AND Anulada = 0",
        (caja,),
    )
    return round(_f(fila["saldo"] if fila else None), 2)


def listar_movimientos(caja: str, page: int, page_size: int) -> tuple[list[dict], int]:
    total_row = fetch_one(
        "SELECT COUNT(*) AS total FROM dbo.MovimientosCajaEfectivo WHERE Caja = ? AND Anulada = 0",
        (caja,),
    )
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    filas = fetch_all(
        """
        SELECT
            IdMovimiento AS idMovimiento,
            Fecha AS fecha,
            Concepto AS concepto,
            Detalle AS detalle,
            Importe AS importe,
            Cuenta AS cuenta,
            FormaPago AS formaPago,
            NumeroDocumento AS numeroDocumento,
            IdContactoRelacionado AS idContactoRelacionado
        FROM dbo.MovimientosCajaEfectivo
        WHERE Caja = ? AND Anulada = 0
        ORDER BY Fecha ASC, IdMovimiento ASC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """,
        (caja, offset, page_size),
    )
    return [{**f, "importe": _f(f["importe"])} for f in filas], total


def consultar_movimientos(
    caja,
    page,
    page_size,
    desde=None,
    hasta=None,
    tipo=None,
    contacto=None,
    socio=None,
    incluir_anuladas=False,
):
    """Window on the entire box BEFORE filtering rows or paginating."""
    from src.features.cajas_efectivo import operaciones as db

    where = ["1=1"]
    params = [caja]
    if not incluir_anuladas:
        where.append("Anulada=0")
    for value, condition in (
        (desde, "CAST(Fecha AS date)>=?"),
        (hasta, "CAST(Fecha AS date)<=?"),
        (tipo, "Tipo=?"),
        (contacto, "IdContactoRelacionado=?"),
    ):
        if value is not None:
            where.append(condition)
            params.append(value)
    if socio:
        where.append(
            "EXISTS (SELECT 1 FROM dbo.EfectosOperacionCaja e "
            "JOIN dbo.MovimientosCuentaSocio s ON s.IdMovimiento=e.IdRegistro "
            "WHERE e.IdOperacion=base.IdOperacionCaja AND e.TipoEfecto='MovimientoSocio' AND s.IdSocio=?)"
        )
        params.append(socio)
    cte = """WITH base AS (
        SELECT *,SUM(CASE WHEN Anulada=0 THEN Importe ELSE 0 END)
        OVER (ORDER BY Fecha,IdMovimiento ROWS UNBOUNDED PRECEDING) saldoReal
        FROM dbo.MovimientosCajaEfectivo WHERE Caja=?) """
    filter_sql = " AND ".join(where)
    totals = db.one(
        cte
        + "SELECT COUNT(*) total,ISNULL(SUM(CASE WHEN Anulada=0 THEN Importe ELSE 0 END),0) subtotal "
        "FROM base WHERE " + filter_sql,
        params,
    )
    rows = db.read(
        cte
        + """SELECT IdMovimiento idMovimiento,Fecha fecha,Concepto concepto,Detalle detalle,
        Importe importe,Cuenta cuenta,FormaPago formaPago,NumeroDocumento numeroDocumento,
        IdContactoRelacionado idContactoRelacionado,IdOperacionCaja idOperacion,Tipo tipo,Anulada anulada,
        CONVERT(varchar(40),CAST(saldoReal AS decimal(19,2))) saldoCorridoDecimal
        FROM base WHERE """
        + filter_sql
        + " ORDER BY Fecha ASC, IdMovimiento ASC "
        "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        (*params, offset_for(page, page_size), page_size),
    )
    previous = (
        db.one(
            "SELECT ISNULL(SUM(Importe),0) saldo FROM dbo.MovimientosCajaEfectivo "
            "WHERE Caja=? AND Anulada=0 AND CAST(Fecha AS date)<?",
            (caja, desde),
        )
        if desde
        else {"saldo": 0}
    )
    return {
        "items": [{**row, "importe": float(row["importe"])} for row in rows],
        "page": page,
        "pageSize": page_size,
        "total": totals["total"],
        "saldoAnteriorDecimal": f"{previous['saldo']:.2f}",
        "subtotalFiltradoDecimal": f"{totals['subtotal']:.2f}",
    }
