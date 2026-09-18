"""Pydantic contract models for the Compras module.

Compras is the single source of truth for imputacion (rubro/centro de
costo/destino/campania) across the system (FR-005) — no other module may
redefine these fields. When a value is missing in Det_Compras it MUST be
returned explicitly as null, never omitted or defaulted (FR-006).

Los modelos de alta/edición (006-carga-compras) escriben exclusivamente
contra `WC` — ver `execute_write_transaction` en `src/db/connection.py`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class VencimientoCompra(BaseModel):
    idVencimiento: int
    fechaVencimiento: date | None = None


class CompraDetalle(BaseModel):
    idCompra: int
    fecha: date | None = None
    proveedor: Proveedor | None = None
    tipo: str | None = None
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None
    moneda: str | None = None
    tipoDeCambio: float | None = None
    conceptosNoGravados: float | None = None
    ingresosBrutos: float | None = None
    guias: float | None = None
    comision: float | None = None
    financiacion: float | None = None
    gastosVarios: float | None = None
    leyDeSellos: float | None = None
    resGral4169: float | None = None
    ajustaTipoCambio: bool | None = None
    documentoOriginal: str | None = None
    lineas: list[LineaCompra]
    vencimientos: list[VencimientoCompra] = []


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


class CentroCosto(BaseModel):
    idCentroCosto: int
    centroCosto: str | None = None


class Rubro(BaseModel):
    idRubro: int
    rubro: str | None = None


class Destino(BaseModel):
    idDestino: int
    destino: str | None = None


class UnidadMedida(BaseModel):
    unidad: str


class Campania(BaseModel):
    idCampania: int
    campania: str | None = None


class FiltrosComprasResponse(BaseModel):
    """Catálogos para los filtros de búsqueda y para los combos de línea del alta (006)."""

    centrosCosto: list[CentroCosto]
    rubros: list[Rubro]
    destinos: list[Destino] = []
    unidadesMedida: list[UnidadMedida] = []
    campañas: list[Campania] = []


# --- Alta controlada de catálogos (006-carga-compras): los combos de línea
# restringen la carga a valores existentes; agregar uno nuevo pasa por
# confirmación explícita en el frontend antes de llamar a estos endpoints. ---


class RubroNuevoRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=50)  # Rubros.Rubro nvarchar(50)


class CentroCostoNuevoRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=20)  # [Centro de costos].[Centro de costos] nvarchar(20)


class DestinoNuevoRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)  # DestinoCompras.Destino nvarchar(255)


class CampaniaNuevaRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=9)  # Campañas.Campaña nvarchar(9)


class DocumentoRelacionado(BaseModel):
    idCompra: int
    fecha: date | None = None
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None


class DocumentoRelacionadoRequest(BaseModel):
    idCompraRelacionada: int


class RubroCreado(BaseModel):
    idRubro: int
    rubro: str


class CentroCostoCreado(BaseModel):
    idCentroCosto: int
    centroCosto: str


class DestinoCreado(BaseModel):
    idDestino: int
    destino: str


class CampaniaCreada(BaseModel):
    idCampania: int
    campania: str


# --- Alta/edición (006-carga-compras) ---

TipoComprobante = Literal["A", "B", "C", "M", "X"]
TipoDocumentoCompra = Literal[
    "Factura", "Nota de Crédito", "Nota de Débito", "C. Deposito Cereales"
]
Moneda = Literal["Pesos", "Dolares"]


class LineaInput(BaseModel):
    productoServicio: str = Field(min_length=1)
    cantidad: float
    precioUnitario: float
    iva: float
    unidad: str | None = None
    idCentroCosto: int | None = None
    idDestino: int | None = None
    idRubro: int | None = None
    campaña: str | None = None
    ajusteFinanciero: bool = False


class VencimientoInput(BaseModel):
    fechaVencimiento: date


class CompraAltaRequest(BaseModel):
    idContacto: int
    fecha: date
    tipo: TipoComprobante
    tipoDocumento: TipoDocumentoCompra
    numeroDocumento: str = Field(min_length=1, max_length=15)
    moneda: Moneda
    tipoDeCambio: float | None = None
    ingresosBrutos: float = 0
    conceptosNoGravados: float = 0
    guias: float = 0
    comision: float = 0
    financiacion: float = 0
    gastosVarios: float = 0
    leyDeSellos: float = 0
    resGral4169: float = 0
    ajustaTipoCambio: bool = False
    documentoOriginal: str | None = None
    lineas: list[LineaInput] = Field(min_length=1)
    vencimientos: list[VencimientoInput] = []


class CompraEditRequest(CompraAltaRequest):
    """Mismo contrato que el alta — PUT reemplaza cabecera+líneas+vencimientos por completo."""


class PesificadoBlock(BaseModel):
    subtotalNeto: float
    ivaCabecera: float
    importeTotal: float


class LineaCalculada(LineaInput):
    idDetalleCompra: int | None = None
    subtotal: float
    importeIva: float


class VencimientoCalculado(VencimientoInput):
    idVencimiento: int | None = None


class CompraDetalleResponse(BaseModel):
    idCompra: int
    idContacto: int
    fecha: date
    tipo: TipoComprobante
    tipoDocumento: TipoDocumentoCompra
    numeroDocumento: str
    moneda: Moneda
    tipoDeCambio: float | None = None
    ingresosBrutos: float
    conceptosNoGravados: float
    guias: float
    comision: float
    financiacion: float
    gastosVarios: float
    leyDeSellos: float
    resGral4169: float
    ajustaTipoCambio: bool
    documentoOriginal: str | None = None
    subtotalNeto: float
    ivaCabecera: float
    importeTotal: float
    pesificado: PesificadoBlock | None = None
    lineas: list[LineaCalculada]
    vencimientos: list[VencimientoCalculado]
    warnings: list[str] = []


class LockRequest(BaseModel):
    lockToken: str
    # "Forzar edición" del frontend — ver docstring de `adquirir_lock`.
    force: bool = False


class LockResponse(BaseModel):
    idCompra: int
    lockToken: str
    expiresAt: datetime


class RubroSugeridoResponse(BaseModel):
    idRubro: int | None = None
    rubro: str | None = None
    frecuencia: int = 0
