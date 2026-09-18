"""Pydantic contract models for the Ventas de Hacienda module.

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

Desde 007-ventas-hacienda-granos se agregan alta/edición/eliminación,
que escriben exclusivamente contra `WC` (ver src/db/connection.py).
"""

from __future__ import annotations

from datetime import date, datetime

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


# --- Alta/edición (007-ventas-hacienda-granos) — escriben exclusivamente
# contra `WC` vía `execute_write_transaction` (ver src/db/connection.py). ---


class LineaVentaHaciendaInput(BaseModel):
    idComprador: int
    idTipoProducto: int
    cantidad: float
    unidadMedida: str | None = None
    pesoTotal: float | None = None
    precioUnitarioA: float
    precioUnitarioB: float = 0


class VencimientoVentaInput(BaseModel):
    fecha: date
    importe: float


class VentaHaciendaAltaRequest(BaseModel):
    idConsignatario: int
    idEstablecimiento: int
    idTipoDocumento: int
    numeroDocumento: str = Field(min_length=1, max_length=50)
    fecha: date
    porcComision: float = 0
    visMunicipal: float = 0
    balanza: float = 0
    gsVsNoGravados: float = 0
    alicuotaIVA: float = 0
    retencionGanancias: float = 0
    retencionIVA: float = 0
    ingresosBrutos: float = 0
    leyDeSellos: float = 0
    flete: float = 0
    gastosVarios: float = 0
    complemento: float = 0
    documentoOriginal: str | None = None
    lineas: list[LineaVentaHaciendaInput] = Field(min_length=1)
    vencimientos: list[VencimientoVentaInput] = []


class VentaHaciendaEditRequest(VentaHaciendaAltaRequest):
    """Mismo contrato que el alta — PUT reemplaza cabecera+líneas+vencimientos por completo."""


class LineaVentaHaciendaCalculada(LineaVentaHaciendaInput):
    """Para lectura/prefill de edición — a diferencia de `LineaVentaHaciendaInput`
    (el contrato de escritura), acepta `idComprador` nulo: datos históricos
    reales tienen líneas cargadas sin comprador asignado (ver sweep de
    todas las ventas reales, 2026-09-17). El formulario de edición debe
    forzar a completarlo antes de poder guardar."""

    idComprador: int | None = None
    comprador: str | None = None
    idDetalleVenta: int | None = None
    importe: float


class VencimientoVentaCalculado(VencimientoVentaInput):
    idVencimientoVenta: int | None = None


class VentaHaciendaDetalleResponse(BaseModel):
    idVenta: int
    idConsignatario: int
    consignatario: str | None = None
    idEstablecimiento: int
    idTipoDocumento: int
    numeroDocumento: str
    fecha: date
    porcComision: float
    visMunicipal: float
    balanza: float
    gsVsNoGravados: float
    alicuotaIVA: float
    retencionGanancias: float
    retencionIVA: float
    ingresosBrutos: float
    leyDeSellos: float
    flete: float
    gastosVarios: float
    complemento: float
    documentoOriginal: str | None = None
    subTotal: float
    subtotalB: float
    comision: float
    iva: float
    importe: float
    importeTotal: float
    lineas: list[LineaVentaHaciendaCalculada]
    vencimientos: list[VencimientoVentaCalculado]
    warnings: list[str] = []


class LockRequest(BaseModel):
    lockToken: str
    force: bool = False


class LockResponse(BaseModel):
    idVenta: int
    lockToken: str
    expiresAt: datetime


class DocumentoRelacionado(BaseModel):
    idVenta: int
    fecha: date | None = None
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None


class DocumentoRelacionadoRequest(BaseModel):
    idVentaRelacionada: int


class EstablecimientoItem(BaseModel):
    idEstablecimiento: int
    establecimiento: str | None = None


class TipoDocumentoItem(BaseModel):
    idTipoDocumento: int
    tipoDocumento: str | None = None


class TipoHaciendaItem(BaseModel):
    idTipoHacienda: int
    tipoHacienda: str | None = None


class FiltrosVentaHaciendaResponse(BaseModel):
    establecimientos: list[EstablecimientoItem]
    tiposDocumento: list[TipoDocumentoItem]
    tiposHacienda: list[TipoHaciendaItem]
