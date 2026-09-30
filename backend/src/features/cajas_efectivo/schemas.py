"""Schemas de cajas de efectivo (027) — ver contracts/api.md."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class MovimientoCajaEfectivo(BaseModel):
    idMovimiento: int
    fecha: date
    concepto: str | None = None
    detalle: str | None = None
    importe: float
    cuenta: str | None = None
    formaPago: str | None = None
    numeroDocumento: str | None = None
    idContactoRelacionado: int | None = None


class SaldoCaja(BaseModel):
    caja: str
    saldo: float


class MovimientosCajaResponse(BaseModel):
    items: list[MovimientoCajaEfectivo]
    page: int
    pageSize: int
    total: int
