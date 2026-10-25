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
    # 041: cargas vigentes a socios (vacío si no hay)
    aCargoDe: list[dict] = []
    estadoDevolucion: str | None = None
    pendienteNominal: str | None = None


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


# --- 041 impuestos particulares (contracts/api.md) ---------------------------------------------------------------

from uuid import UUID  # noqa: E402


class CargaInput(BaseModel):
    claveIdempotencia: UUID
    idSocio: int
    importe: str | None = None
    porcentaje: str | None = None
    motivo: str = Field(min_length=1, max_length=255)
    partida: str | None = Field(default=None, max_length=60)
    titularOscar: bool = False
    reemplazarMovimientoManual: int | None = None
    confirmarCuentaCerrada: bool = False
    ignorarManuales: bool = False


class DevolucionInput(BaseModel):
    claveIdempotencia: UUID
    idMovimientoSocio: int | None = None
    importe: str
    fecha: date | None = None
    medio: str | None = Field(default=None, max_length=100)
    motivo: str | None = Field(default=None, max_length=255)


class AnularInput(BaseModel):
    motivo: str = Field(min_length=1, max_length=255)
