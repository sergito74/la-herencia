"""Catálogo de tarjetas (solo lectura, Historia 4) y cuenta corriente por
tarjeta (Historia 2) — 008-tarjetas.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Tarjeta(BaseModel):
    idTarjeta: int
    nombre: str
    banco: str | None = None
    activa: bool


class MovimientoTarjeta(BaseModel):
    idResumen: int
    fecha: date | None = None
    codigo: str
    deuda: float
    credito: float
    saldoAcumulado: float


class MovimientosTarjetaResponse(BaseModel):
    idTarjeta: int
    tarjeta: str
    movimientos: list[MovimientoTarjeta]
