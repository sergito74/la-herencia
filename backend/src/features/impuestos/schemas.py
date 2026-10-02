"""Pydantic contract models for the Impuestos module (boletas: alta/edición/baja desde 033)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


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


# --- 033-alta-impuestos ---------------------------------------------------


class TipoImpuestoOpcion(BaseModel):
    idTipoImpuesto: int
    nombre: str


class OrganismoOpcion(BaseModel):
    idContacto: int
    nombre: str
    tipos: list[TipoImpuestoOpcion]


class CatalogoImpuestos(BaseModel):
    organismos: list[OrganismoOpcion]


class ImpuestoInput(BaseModel):
    idOrganismo: int
    idTipoImpuesto: int
    fecha: date
    periodoLiquidado: str | None = Field(default=None, max_length=255)
    numeroDocumento: str | None = Field(default=None, max_length=255)
    importe: float
    documentoOriginal: str | None = None


class ImpuestoDetalle(BaseModel):
    idImpuesto: int
    fecha: date | None = None
    idOrganismo: int | None = None
    organismo: str | None = None
    idTipoImpuesto: int | None = None
    tipoImpuesto: str | None = None
    periodoLiquidado: str | None = None
    numeroDocumento: str | None = None
    importe: float | None = None
    documentoOriginal: str | None = None
