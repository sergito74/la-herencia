"""Cajas de efectivo (027) — Giamigli SA y caja chica del campo. 100% de
solo lectura en esta iteración (spec FR-011): no hay ningún endpoint ni
función de escritura acá, la migración inserta directo vía script."""

from __future__ import annotations

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for


def _f(value) -> float:
    return float(value) if value is not None else 0.0


def calcular_saldo(caja: str) -> float:
    fila = fetch_one(
        "SELECT SUM(Importe) AS saldo FROM dbo.MovimientosCajaEfectivo WHERE Caja = ?",
        (caja,),
    )
    return round(_f(fila["saldo"] if fila else None), 2)


def listar_movimientos(caja: str, page: int, page_size: int) -> tuple[list[dict], int]:
    total_row = fetch_one(
        "SELECT COUNT(*) AS total FROM dbo.MovimientosCajaEfectivo WHERE Caja = ?",
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
        WHERE Caja = ?
        ORDER BY Fecha ASC, IdMovimiento ASC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """,
        (caja, offset, page_size),
    )
    return [{**f, "importe": _f(f["importe"])} for f in filas], total
