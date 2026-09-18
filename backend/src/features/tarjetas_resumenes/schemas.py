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
    totalCalculado: float
    soloCabecera: bool


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
