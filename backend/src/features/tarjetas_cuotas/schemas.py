"""Compras en cuotas (Historia 3, 008-tarjetas) — cabecera
`dbo.[Tarjetas de Credito]` + detalle `dbo.[Cuotas Tarjetas de Credito]`.
No vinculada a una tarjeta del catálogo (data-model.md). Escribe
exclusivamente contra `WC` vía `execute_write_transaction`.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class CompraCuotasAltaRequest(BaseModel):
    idContacto: int
    fecha: date
    nroComprobante: int
    importeTotal: float
    cantidadCuotas: int = Field(ge=1)


class CompraCuotasEditRequest(CompraCuotasAltaRequest):
    """Mismo contrato que el alta — PUT regenera el cronograma completo
    siempre (FR-007a, Clarifications 2026-09-18), sin excepción."""


class CuotaResponse(BaseModel):
    idCuota: int
    numeroCuota: int
    fechaVencimiento: date
    importe: float
    cobrado: bool


class CompraCuotasDetalleResponse(BaseModel):
    idPagoTarjeta: int
    idContacto: int
    contacto: str | None = None
    fecha: date
    nroComprobante: int
    cantidadCuotas: int
    importeTotal: float
    cuotas: list[CuotaResponse] = []


class CompraCuotasListItem(BaseModel):
    idPagoTarjeta: int
    idContacto: int
    contacto: str | None = None
    fecha: date
    nroComprobante: int
    cantidadCuotas: int
    cuotasCobradas: int
    cuotasPendientes: int


class ComprasCuotasListResponse(BaseModel):
    items: list[CompraCuotasListItem]
    page: int
    pageSize: int
    total: int


class MarcarCobradaRequest(BaseModel):
    cobrado: bool


class LockRequest(BaseModel):
    lockToken: str
    force: bool = False


class LockResponse(BaseModel):
    idPagoTarjeta: int
    lockToken: str
    expiresAt: datetime
