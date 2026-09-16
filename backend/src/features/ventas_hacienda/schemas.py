"""Pydantic contract models for the Ventas de Hacienda module (read-only).

`Retenciones Ventas Hacienda` has no reliable key back to a specific
`Venta Hacienda` (confirmed against real data — see
specs/005-egresos-y-ventas-menores/research.md), so it is modeled and
queried as an independent entity, never nested under a venta.

`Det_Ventas Hacienda` has two "Precio unitario" columns (A/B). CORRECTED
2026-09-17: inspecting the real Access form (`Subformulario Detalle Venta
Feria Hacienda`, control `TxtTotal`) revealed the actual business rule —
`importe = cantidad * (precioUnitarioA + precioUnitarioB)` — which this
schema now exposes as `importe`, matching the production system exactly
instead of leaving the two prices uncombined.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LineaVentaHacienda(BaseModel):
    idDetalleVenta: int
    idComprador: int | None = None
    comprador: str | None = None
    tipoHacienda: str | None = None
    cantidad: float | None = None
    unidadMedida: str | None = None
    pesoTotal: float | None = None
    precioUnitarioA: float | None = None
    precioUnitarioB: float | None = None
    importe: float | None = None


class VentaHacienda(BaseModel):
    idVenta: int
    fecha: date | None = None
    idConsignatario: int | None = None
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
    idContacto: int | None = None
    contacto: str | None = None
    documento: str | None = None
    numeroDocumento: str | None = None
    importe: float | None = None


class RetencionesVentaHaciendaListResponse(BaseModel):
    items: list[RetencionVentaHacienda]
    page: int
    pageSize: int
    total: int
