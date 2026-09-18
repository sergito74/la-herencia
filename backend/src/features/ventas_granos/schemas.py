"""Pydantic contract models for the Ventas de Granos module.

Dominio 100% nuevo (007-ventas-hacienda-granos) — nunca antes leído ni
escrito por este sistema. Cabecera única (`dbo.[Venta Granos]`), sin
tabla de líneas de producto separada (a diferencia de Hacienda/Compras)
— ver research.md §3. Escribe exclusivamente contra `WC`.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class Consignatario(BaseModel):
    idContacto: int
    razonSocial: str | None = None


class AjusteGranos(BaseModel):
    idAjuste: int
    concepto: str | None = None
    importe: float | None = None
    alicuotaIVA: float | None = None


class DeduccionGranos(BaseModel):
    idDeduccion: int
    idConcepto: int | None = None
    concepto: str | None = None
    detalle: str | None = None
    porc: float | None = None
    baseCalculo: float | None = None
    alicuota: float | None = None


class VentaGranos(BaseModel):
    idVenta: int
    fecha: date | None = None
    consignatario: Consignatario | None = None
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None
    grano: str | None = None
    campania: str | None = None


class VentaGranosListResponse(BaseModel):
    items: list[VentaGranos]
    page: int
    pageSize: int
    total: int


class VentaGranosDetalleResponse(BaseModel):
    idVenta: int
    idConsignatario: int
    idTipoDocumento: int
    numeroDocumento: str
    fecha: date
    precioUnitario: float
    tipoCambio: float | None = None
    gradoOperacion: str | None = None
    idProducto: int
    tipoDeGrano: str | None = None
    campania: str | None = None
    flete: float
    nroDeposito: str | None = None
    gradoMercaderia: str | None = None
    factor: float
    contProteico: float | None = None
    cantidadEntregada: float
    cantidadVendida: float
    alicuotaIVA: float
    retencionIVA: float
    retIG: float
    percepciones: float
    otraRetenciones: float
    sellado: float
    derechoRegistro: float
    honorariosCamara: float
    aCuentaCalidad: float
    iibb: float
    documentoOriginal: str | None = None
    ajustes: list[AjusteGranos]
    deducciones: list[DeduccionGranos]
    precioKg: float
    subTotal: float
    iva: float
    importeConIVA: float
    totalOperacion: float
    totalRetenciones: float
    totalDeducciones: float
    importeNetoAPercibir: float
    warnings: list[str] = []


# --- Alta/edición ---


class AjusteInput(BaseModel):
    concepto: str = Field(min_length=1)
    importe: float
    alicuotaIVA: float = 0


class DeduccionInput(BaseModel):
    idConcepto: int
    detalle: str | None = None
    porc: float
    baseCalculo: float
    alicuota: float = 0


class VentaGranosAltaRequest(BaseModel):
    idConsignatario: int
    idTipoDocumento: int
    idProducto: int
    numeroDocumento: str = Field(min_length=1, max_length=255)
    fecha: date
    precioUnitario: float
    tipoCambio: float | None = None
    gradoOperacion: str | None = Field(default=None, max_length=5)
    tipoDeGrano: str | None = None
    campania: str | None = Field(default=None, max_length=10)
    flete: float = 0
    nroDeposito: str | None = None
    gradoMercaderia: str | None = Field(default=None, max_length=5)
    factor: float = 100
    contProteico: float | None = None
    cantidadEntregada: float
    cantidadVendida: float
    alicuotaIVA: float = 0
    retencionIVA: float = 0
    retIG: float = 0
    percepciones: float = 0
    otraRetenciones: float = 0
    sellado: float = 0
    derechoRegistro: float = 0
    honorariosCamara: float = 0
    aCuentaCalidad: float = 0
    iibb: float = 0
    documentoOriginal: str | None = None
    ajustes: list[AjusteInput] = []
    deducciones: list[DeduccionInput] = []


class VentaGranosEditRequest(VentaGranosAltaRequest):
    """Mismo contrato que el alta — PUT reemplaza cabecera+ajustes+deducciones por completo."""


class LockRequest(BaseModel):
    lockToken: str
    force: bool = False


class LockResponse(BaseModel):
    idVenta: int
    lockToken: str
    expiresAt: datetime


class GranoItem(BaseModel):
    idGrano: int
    grano: str | None = None


class TipoDocumentoItem(BaseModel):
    idTipoDocumento: int
    tipoDocumento: str | None = None


class ConceptoDeduccionItem(BaseModel):
    idConcepto: int
    concepto: str | None = None


class FiltrosVentaGranosResponse(BaseModel):
    granos: list[GranoItem]
    tiposDocumento: list[TipoDocumentoItem]
    conceptosDeducciones: list[ConceptoDeduccionItem]
