"""Schemas de la cola de revisión de Cajas Giamigli (027) — ver contracts/api.md."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CasoARevisar(BaseModel):
    idRevision: int
    hoja: str
    numeroFila: int
    motivo: str
    datosCrudos: str | None = None
    fechaCarga: datetime
    resuelto: bool


class ListaCasosARevisarResponse(BaseModel):
    items: list[CasoARevisar]
    total: int
