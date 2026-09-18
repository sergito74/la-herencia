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
    origen: str
    deuda: float
    credito: float
    saldoAcumulado: float


class MovimientoPagoCandidato(BaseModel):
    """Fila de `Movimientos BNA`/`Movimientos Galicia` con `IdContacto`
    apuntando a esta tarjeta — candidata a ser el pago de un resumen
    (punto 6 del feedback del usuario, 2026-09-19)."""

    origen: str
    idMovimiento: int
    fecha: date
    importe: float
    concepto: str | None = None


class MovimientosTarjetaResponse(BaseModel):
    idTarjeta: int
    tarjeta: str
    movimientos: list[MovimientoTarjeta]
