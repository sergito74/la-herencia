"""Schemas de cuentas de socios (021) — ver contracts/api.md."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class CompraParticularCandidata(BaseModel):
    idCompra: int
    fecha: date
    proveedor: str | None = None
    numeroDocumento: str | None = None
    importePersonal: float


class MovimientoCuentaSocio(BaseModel):
    idMovimiento: int
    tipo: str
    importe: float
    importeUSD: float = 0.0
    importeKgCarne: float = 0.0
    fecha: datetime
    origen: str | None = None
    idOrigen: int | None = None
    proveedorOrigen: str | None = None
    numeroDocumentoOrigen: str | None = None
    medio: str | None = None
    motivo: str | None = None
    usuario: str
    anulada: bool
    motivoAnulacion: str | None = None
    huerfano: bool = False


class DeudaActualizada(BaseModel):
    """Como la planilla Cajas Giamigli: kg × novillo + US$ × dólar de hoy;
    el mutuo en dólares va aparte. Positivo: el socio debe; negativo: a su favor."""
    kgCarne: float = 0.0
    dolares: float = 0.0
    valorKgCarne: float = 0.0
    valorDolares: float = 0.0
    deudaActualizada: float = 0.0
    mutuoUSD: float = 0.0
    mutuoPesos: float = 0.0
    novillo: float = 0.0
    fechaNovillo: date | None = None
    dolar: float = 0.0
    fechaDolar: date | None = None


class SocioConSaldo(BaseModel):
    idSocio: int
    nombre: str
    saldo: float
    actualizada: DeudaActualizada | None = None


class ListaSociosResponse(BaseModel):
    socios: list[SocioConSaldo]


class ListaCandidatasResponse(BaseModel):
    compras: list[CompraParticularCandidata]


class DetalleSocioResponse(BaseModel):
    idSocio: int
    nombre: str
    saldo: float
    saldoUSD: float = 0.0
    saldoKgCarne: float = 0.0
    actualizada: DeudaActualizada | None = None
    movimientos: list[MovimientoCuentaSocio]


class AsignarGastoRequest(BaseModel):
    idCompra: int
    motivo: str | None = None


class AnularMovimientoRequest(BaseModel):
    motivo: str


class DevolucionRequest(BaseModel):
    importe: float
    fecha: date
    medio: str
    motivo: str
