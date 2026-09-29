"""Schemas de Traspasos internos de Tesorería (024) — ver
contracts/traspasos-internos-api.md."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class VincularRequest(BaseModel):
    medioB: str
    idMovimientoB: int


class MovimientoReferencia(BaseModel):
    medio: str
    idMovimiento: int
    fecha: datetime
    descripcion: str | None = None
    importe: float


class EstadoTraspasoInterno(BaseModel):
    vinculado: bool
    contraparte: MovimientoReferencia | None = None
    candidatas: list[MovimientoReferencia] = []
    idEvento: int | None = None
    usuario: str | None = None
    fecha: datetime | None = None
