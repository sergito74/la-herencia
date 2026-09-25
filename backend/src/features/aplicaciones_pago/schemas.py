"""Schemas de aplicación de pagos/cobros (019) — ver
contracts/api-aplicaciones-pago.md."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

TipoDocumento = str  # "CompraDeuda" | "VentaHacienda" | "VentaGranos"


class DocumentoPendiente(BaseModel):
    tipoDocumento: str
    idDocumento: int
    fecha: date | None = None
    numeroDocumento: str | None = None
    importeTotal: float
    aplicado: float
    saldoPendiente: float


class SugerenciaItem(BaseModel):
    tipoDocumento: str
    idDocumento: int
    fecha: date | None = None
    saldoPendiente: float
    importeSugerido: float


class SugerirRequest(BaseModel):
    origenMovimiento: str
    idMovimientoOrigen: int


class SugerenciaAplicacionResponse(BaseModel):
    importeMovimiento: float
    sugerencias: list[SugerenciaItem]
    saldoSinAsignar: float


class AplicacionItem(BaseModel):
    tipoDocumento: str
    idDocumento: int
    importeAplicado: float


class ConfirmarAplicacionRequest(BaseModel):
    origenMovimiento: str
    idMovimientoOrigen: int
    aplicaciones: list[AplicacionItem]


class AnularAplicacionRequest(BaseModel):
    motivo: str


class AplicacionHistorial(BaseModel):
    idAplicacion: int
    origenMovimiento: str
    idMovimientoOrigen: int
    importeAplicado: float
    fecha: datetime
    usuario: str
    anulada: bool
    motivoAnulacion: str | None = None
    usuarioAnulacion: str | None = None
    fechaAnulacion: datetime | None = None


class EstadoDocumentoResponse(BaseModel):
    importeTotal: float
    aplicado: float
    saldoPendiente: float
    estado: str
    aplicaciones: list[AplicacionHistorial]


class AplicacionVigente(BaseModel):
    idAplicacion: int
    tipoDocumento: str
    idDocumentoAplicado: int
    importeAplicado: float


class EstadoMovimientoResponse(BaseModel):
    importe: float
    aplicado: float
    saldoSinAplicar: float
    aplicaciones: list[AplicacionVigente]
