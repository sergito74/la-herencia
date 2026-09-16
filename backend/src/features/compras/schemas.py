"""Pydantic contract models for the Compras module (read-only).

Compras is the single source of truth for imputacion (rubro/centro de
costo/destino/campania) across the system (FR-005) — no other module may
redefine these fields. When a value is missing in Det_Compras it MUST be
returned explicitly as null, never omitted or defaulted (FR-006).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Proveedor(BaseModel):
    idContacto: int
    razonSocial: str | None = None


class Compra(BaseModel):
    idCompra: int
    fecha: date | None = None
    proveedor: Proveedor | None = None
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None


class ComprasListResponse(BaseModel):
    items: list[Compra]
    page: int
    pageSize: int
    total: int


class Imputacion(BaseModel):
    idRubro: int | None = None
    rubro: str | None = None
    idCentroCosto: int | None = None
    centroCosto: str | None = None
    idDestino: int | None = None
    destino: str | None = None
    idCampania: int | None = None
    campania: str | None = None


class LineaCompra(BaseModel):
    idDetalleCompra: int
    productoServicio: str | None = None
    cantidad: float | None = None
    precioUnitario: float | None = None
    iva: float | None = None
    imputacion: Imputacion | None = None


class CompraDetalle(BaseModel):
    idCompra: int
    fecha: date | None = None
    proveedor: Proveedor | None = None
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None
    conceptosNoGravados: float | None = None
    ingresosBrutos: float | None = None
    lineas: list[LineaCompra]


class MovimientoTrazabilidad(BaseModel):
    origenTipo: str | None = None
    idOrigen: int
    documento: str | None = None
    fecha: date | None = None
    importe: float | None = None
    tipoImporte: str | None = None


class TrazabilidadCompra(BaseModel):
    idCompra: int
    movimientos: list[MovimientoTrazabilidad]
