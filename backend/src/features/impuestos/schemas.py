"""Pydantic contract models for the Impuestos module (read-only)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Impuesto(BaseModel):
    idImpuesto: int
    fecha: date | None = None
    tipoImpuesto: str | None = None
    periodoLiquidado: str | None = None
    numeroDocumento: str | None = None
    importe: float | None = None
    idOrganismo: int | None = None
    organismo: str | None = None


class ImpuestosListResponse(BaseModel):
    items: list[Impuesto]
    page: int
    pageSize: int
    total: int


class Retencion(BaseModel):
    idRetencion: int
    numeroCertificado: str | None = None
    fecha: date | None = None
    idContacto: int | None = None
    contacto: str | None = None
    importe: float | None = None


class RetencionesListResponse(BaseModel):
    items: list[Retencion]
    page: int
    pageSize: int
    total: int
