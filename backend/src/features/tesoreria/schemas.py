"""Pydantic contract models for the Tesoreria module (read-only).

Each medio (BNA, Galicia, efectivo, valores propios/recibidos, tarjetas)
keeps its own shape (FR-002) — no generic/unified movimiento model. Columns
of centro de costos/rubro/destino from `Movimientos Galicia` MUST NOT be
exposed here (FR-006).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

MEDIOS = (
    "bna",
    "galicia",
    "efectivo",
    "valores-propios",
    "valores-recibidos",
    "tarjetas",
)


class MediosResponse(BaseModel):
    medios: list[str]


class MovimientoBNA(BaseModel):
    idMovimientoBNA: int
    fechaHora: datetime | None = None
    concepto: str | None = None
    importe: float | None = None
    idContacto: int | None = None
    contacto: str | None = None
    idCarga: int | None = None


class MovimientoGalicia(BaseModel):
    idMovimiento: int
    fecha: date | None = None
    descripcion: str | None = None
    debitos: float | None = None
    creditos: float | None = None
    saldo: float | None = None
    idContacto: int | None = None
    contacto: str | None = None
    idCarga: int | None = None


class PagoEfectivo(BaseModel):
    idPagoEfectivo: int
    idContacto: int | None = None
    fecha: date | None = None
    cuenta: str | None = None
    caja: str | None = None
    numeroDocumento: float | None = None
    importeImputado: float | None = None
    idOperacion: int | None = None


class ValorPropio(BaseModel):
    idValor: int
    # Legacy columns: "Numero cheque" and "Cobrado" are stored as
    # float/"S"|"N" in SQL Server, not as a clean string/bool — kept as-is
    # rather than silently coerced (principle IV, explicit financial data).
    numeroCheque: float | str | None = None
    fechaEmision: date | None = None
    fechaVencimiento: date | None = None
    importe: float | None = None
    cobrado: str | None = None
    fechaCobro: date | None = None
    numeroCuenta: str | None = None


class ValorRecibido(BaseModel):
    idValor: int
    numeroValor: int | str | None = None
    banco: str | None = None
    fechaEmision: date | None = None
    fechaVencimiento: date | None = None
    fechaCobro: date | None = None
    idEmisor: int | None = None
    idReceptor: int | None = None
    importe: float | None = None
    destino: str | None = None


class LineaResumenTarjeta(BaseModel):
    idLineaConsumo: int
    idResumen: int
    fechaCompra: date | None = None
    detalle: str | None = None
    importe: float | None = None
    idContacto: int | None = None
    numeroDocumento: str | None = None


class MovimientosResponse(BaseModel):
    items: list
    page: int
    pageSize: int
    total: int


class CompraCandidata(BaseModel):
    idCompra: int
    numeroDocumento: str | None = None
    proveedor: str | None = None
    fecha: date | None = None
    importe: float | None = None


class ReferenciaOrigen(BaseModel):
    estado: str
    candidatas: list[CompraCandidata]


class MovimientoExcelBNA(BaseModel):
    fecha: date | None = None
    comprobante: str | None = None
    concepto: str | None = None
    importe: float | None = None
    saldo: float | None = None


class MovimientoExcelGalicia(BaseModel):
    fecha: date | None = None
    descripcion: str | None = None
    debitos: float | None = None
    creditos: float | None = None
    numeroComprobante: str | None = None
    leyendas: list[str | None]
    saldo: float | None = None


class ExcelValidacionResponse(BaseModel):
    medioDetectado: str | None = None
    valido: bool
    errores: list[str]
    movimientosPrevisualizados: list


class ResumenConfirmacion(BaseModel):
    nuevos: int
    omitidosDuplicado: int
    omitidosIncompletos: int
    total: int


class ExcelPrevisualizacionConfirmacionResponse(BaseModel):
    medioDetectado: str | None = None
    valido: bool
    errores: list[str]
    movimientosPrevisualizados: list = []
    resumen: ResumenConfirmacion | None = None


class ExcelConfirmacionResponse(BaseModel):
    valido: bool
    errores: list[str] = []
    banco: str | None = None
    idCarga: int | None = None
    insertados: int | None = None
    omitidosDuplicado: int | None = None
    omitidosIncompletos: int | None = None
    total: int | None = None


class CargaResumen(BaseModel):
    idCarga: int
    nombreArchivo: str
    fechaHoraCarga: datetime
    insertados: int
    omitidosDuplicado: int
    omitidosIncompletos: int


class CargasResponse(BaseModel):
    items: list[CargaResumen]
