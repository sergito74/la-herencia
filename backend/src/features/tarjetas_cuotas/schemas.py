"""Compras en cuotas (Historia 3, 008-tarjetas) — **solo lectura** desde
2026-09-19 (feedback del usuario, punto 5: estructura obsoleta, ver
repository.py). Cabecera `dbo.[Tarjetas de Credito]` + detalle
`dbo.[Cuotas Tarjetas de Credito]`.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


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
