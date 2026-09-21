"""Resúmenes de tarjeta (Historia 1, 008-tarjetas) — cabecera
`dbo.Tarjetas_Resumenes` + líneas `dbo.Tarjetas_Resumenes_Lineas`. Escribe
exclusivamente contra `WC` vía `execute_write_transaction`.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class LineaConsumoInput(BaseModel):
    fechaCompra: date
    detalle: str = Field(min_length=1, max_length=255)
    importe: float
    fechaVencimientoCompra: date | None = None
    idContacto: int | None = None
    nroDocumento: str | None = Field(default=None, max_length=50)


class CompraVinculada(BaseModel):
    """Factura/NC/ND real (`Compras`, `IdDeuda`) que documenta total o
    parcialmente una línea de consumo — puede haber varias por línea
    (más de un proveedor, o cuotas de un mismo consumo)."""

    idVinculo: int
    idCompra: int
    proveedor: str | None = None
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None
    fechaCompra: date | None = None
    importeCompra: float | None = None
    importeImputado: float


class VincularCompraRequest(BaseModel):
    idCompra: int
    importeImputado: float


class LineaConsumo(LineaConsumoInput):
    idLineaConsumo: int | None = None
    comprasVinculadas: list[CompraVinculada] = []
    # Resolución manual sin documentos (009): "SinDocumento" o "DiferenciaAceptada".
    estadoLinea: str | None = None
    motivoEstado: str | None = None
    detalleEstado: str | None = None
    importeDiferencia: float | None = None


class ResumenAltaRequest(BaseModel):
    idTarjeta: int
    codigo: str = Field(min_length=1, max_length=80)
    fechaCierre: date
    fechaVencimiento: date
    urlResumenOriginal: str | None = None
    impuestoSellos: float = 0
    gastosAdmin: float = 0
    mantCuenta: float = 0
    renovAnual: float = 0
    promocionBNA: float = 0
    creditoContingente: float = 0
    intFinanc: float = 0
    intCompens: float = 0
    iva105: float = 0
    percepIVA105: float = 0
    iva21: float = 0
    percepIVA21: float = 0
    percepIIBB: float = 0
    ajusteResAnterior: float = 0
    lineas: list[LineaConsumoInput] = []


class ResumenEditRequest(ResumenAltaRequest):
    """Mismo contrato que el alta — PUT reemplaza cabecera+líneas por completo."""


class PagoResumen(BaseModel):
    idPago: int
    fecha: date
    importe: float
    origen: str | None = None
    idMovimientoOrigen: int | None = None


class ResumenDetalleResponse(BaseModel):
    idResumen: int
    idTarjeta: int
    tarjeta: str | None = None
    codigo: str
    fechaCierre: date
    fechaVencimiento: date
    urlResumenOriginal: str | None = None
    impuestoSellos: float
    gastosAdmin: float
    mantCuenta: float
    renovAnual: float
    promocionBNA: float
    creditoContingente: float
    intFinanc: float
    intCompens: float
    iva105: float
    percepIVA105: float
    iva21: float
    percepIVA21: float
    percepIIBB: float
    ajusteResAnterior: float
    totalCalculado: float
    lineas: list[LineaConsumo] = []
    pagos: list[PagoResumen] = []
    warnings: list[str] = []


class ResumenListItem(BaseModel):
    idResumen: int
    idTarjeta: int
    tarjeta: str | None = None
    codigo: str
    fechaCierre: date | None = None
    fechaVencimiento: date | None = None
    urlResumenOriginal: str | None = None
    totalCalculado: float
    soloCabecera: bool
    pagoConciliado: bool
    # totalCalculado - pagado, con signo — positiva: falta pagar esa
    # diferencia; negativa: sobre-pago. Dentro de ±0.10 se considera
    # ruido de redondeo (research: 293 resúmenes reales, ver
    # TOLERANCIA_CONCILIACION en repository.py), pero se expone siempre,
    # nunca se oculta silenciosamente (trazabilidad financiera).
    diferenciaRedondeo: float
    lineasTotal: int
    lineasVinculadas: int


class ResumenesListResponse(BaseModel):
    items: list[ResumenListItem]
    page: int
    pageSize: int
    total: int


class VincularPagoRequest(BaseModel):
    """Confirma un movimiento candidato (`origen`/`idMovimiento`) como el
    pago de este resumen, o registra un pago manual si no viene de un
    movimiento bancario cargado (`origen`/`idMovimiento` en `None`)."""

    fecha: date
    importe: float
    origen: str | None = None
    idMovimientoOrigen: int | None = None


class LockRequest(BaseModel):
    lockToken: str
    force: bool = False


class LockResponse(BaseModel):
    idResumen: int
    lockToken: str
    expiresAt: datetime


class DocumentoCandidato(BaseModel):
    """Factura/NC/ND del proveedor de una línea, con su importe pesificado
    (con el tipo de cambio propio del documento) para poder compararlo con el
    resumen, que siempre viene en pesos. Las NC tienen importe negativo."""

    idCompra: int
    fecha: date | None = None
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None
    moneda: str | None = None
    tipoDeCambio: float | None = None
    importeOriginal: float
    importePesos: float
    proveedor: str | None = None
    vinculosPrevios: int = 0
    # Nota de crédito/débito que ajusta el tipo de cambio de una factura en dólares.
    ajustaTipoCambio: bool = False


class ImputacionDocumento(BaseModel):
    idCompra: int
    importeImputado: float


class ConciliacionCalculo(BaseModel):
    # "exacta": en pesos y dentro de $0,10. "aproximada": con dólares, el tipo
    # de cambio implícito difiere del del documento en hasta 2%. "parcial": el
    # resto (la línea paga una parte, o no cierra).
    estado: str
    diferencia: float
    pagoParcial: bool = False
    tcImplicito: float | None = None
    tcReferencia: float | None = None
    desvioTc: float | None = None
    imputados: list[ImputacionDocumento]


class SugerenciaConciliacion(ConciliacionCalculo):
    idsCompra: list[int]


class LineaContexto(BaseModel):
    idLineaConsumo: int
    idResumen: int
    resumenCodigo: str | None = None
    tarjeta: str | None = None
    fechaCompra: date | None = None
    detalle: str | None = None
    importe: float
    idContacto: int | None = None
    proveedor: str | None = None
    nroDocumento: str | None = None
    urlResumenOriginal: str | None = None


class LineaHermana(BaseModel):
    idLineaConsumo: int
    idResumen: int
    resumenCodigo: str | None = None
    fechaCompra: date | None = None
    detalle: str | None = None
    importe: float


class EstadoLinea(BaseModel):
    idLineaConsumo: int
    estado: str
    motivo: str
    detalle: str | None = None
    importeDiferencia: float | None = None


class CandidatosLineaResponse(BaseModel):
    idLineaConsumo: int
    importeLinea: float
    fechaLinea: date | None = None
    idContacto: int | None = None
    linea: LineaContexto
    estado: EstadoLinea | None = None
    hermanas: list[LineaHermana] = []
    documentos: list[DocumentoCandidato]
    sugerencias: list[SugerenciaConciliacion]


class ConciliacionPreviewResponse(ConciliacionCalculo):
    documentos: list[DocumentoCandidato]


class AceptarDiferencia(BaseModel):
    # AjusteTipoCambioSinNota | Redondeo | Otro (con detalle)
    motivo: str
    detalle: str | None = None


class VincularLoteRequest(BaseModel):
    idsCompra: list[int] = Field(min_length=1)
    aceptarDiferencia: AceptarDiferencia | None = None


class SinDocumentoRequest(BaseModel):
    # Impuesto | Interes | CompraNoCargada | Otro (con detalle)
    motivo: str
    detalle: str | None = None


class DocumentoResumido(BaseModel):
    idCompra: int
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None
    moneda: str | None = None
    importeOriginal: float
    importePesos: float
    proveedor: str | None = None


class SugerenciaPendiente(BaseModel):
    idsCompra: list[int]
    estado: str
    unica: bool
    documentos: list[DocumentoResumido]


class LineaPendiente(BaseModel):
    idLineaConsumo: int
    idResumen: int
    resumenCodigo: str | None = None
    idTarjeta: int
    tarjeta: str | None = None
    fechaCierre: date | None = None
    fechaCompra: date | None = None
    detalle: str | None = None
    importe: float
    idContacto: int | None = None
    proveedor: str | None = None
    nroDocumento: str | None = None
    urlResumenOriginal: str | None = None
    cantidadDocumentos: int
    sugerencia: SugerenciaPendiente | None = None


class PendientesResponse(BaseModel):
    items: list[LineaPendiente]
    page: int
    pageSize: int
    total: int
    totalConSugerencia: int


class AceptarExactasRequest(BaseModel):
    idsLineas: list[int] = Field(min_length=1)


class AceptarExactasResponse(BaseModel):
    aplicadas: int
    omitidas: list[int]


class RepartoItem(BaseModel):
    idLinea: int
    idCompra: int
    importe: float


class RepartoPropuestaRequest(BaseModel):
    idsLineas: list[int] = Field(min_length=1)
    idsCompra: list[int] = Field(min_length=1)


class RepartoLinea(BaseModel):
    idLinea: int
    importe: float
    fechaCompra: date | None = None


class RepartoPropuestaResponse(BaseModel):
    lineas: list[RepartoLinea]
    documentos: list[DocumentoCandidato]
    reparto: list[RepartoItem]
    diferencias: dict[int, float]


class ConciliarRepartoRequest(BaseModel):
    reparto: list[RepartoItem] = Field(min_length=1)
    aceptarDiferencia: AceptarDiferencia | None = None


class ConciliarRepartoResponse(BaseModel):
    lineas: int
    vinculos: int
