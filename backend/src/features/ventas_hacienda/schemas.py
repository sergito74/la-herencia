"""Pydantic contract models for the Ventas de Hacienda module (read-only).

`Retenciones Ventas Hacienda` has no reliable key back to a specific
`Venta Hacienda` (confirmed against real data — see
specs/005-egresos-y-ventas-menores/research.md), so it is modeled and
queried as an independent entity, never nested under a venta.

`Det_Ventas Hacienda` has two unrelated "Precio unitario" columns (A/B),
both populated in almost every real row with very different scales.
There is no confirmed rule for combining them into a single "importe", so
both are exposed as-is (constitution principle IV: do not invent a
derived figure the source data does not support).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LineaVentaHacienda(BaseModel):
    idDetalleVenta: int
    comprador: str | None = None
    tipoHacienda: str | None = None
    cantidad: float | None = None
    unidadMedida: str | None = None
    pesoTotal: float | None = None
    precioUnitarioA: float | None = None
    precioUnitarioB: float | None = None


class VentaHacienda(BaseModel):
    idVenta: int
    fecha: date | None = None
    consignatario: str | None = None
    numeroDocumento: str | None = None
    lineas: list[LineaVentaHacienda] = Field(min_length=1)


class VentasHaciendaListResponse(BaseModel):
    items: list[VentaHacienda]
    page: int
    pageSize: int
    total: int


class RetencionVentaHacienda(BaseModel):
    idRetencion: int
    fecha: date | None = None
    contacto: str | None = None
    documento: str | None = None
    numeroDocumento: str | None = None
    importe: float | None = None


class RetencionesVentaHaciendaListResponse(BaseModel):
    items: list[RetencionVentaHacienda]
    page: int
    pageSize: int
    total: int
