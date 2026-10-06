"""Esquemas de la cuenta de tarjetas, el control y los cruces — 034
(specs/034-cuenta-corriente-tarjetas/contracts/tarjetas-cuenta-api.md)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

AVISO_SALDO = "El saldo es información de gestión: no sirve para IVA ni para impuestos."


class TarjetaSaldo(BaseModel):
    idTarjeta: int
    tarjeta: str
    banco: str | None = None
    activa: bool
    idContacto: int
    deuda: float
    credito: float
    # Criterio de la vista: crédito − deuda (negativo = se debe).
    saldo: float
    pendienteNeto: float
    # |saldo + pendienteNeto| cuando `hasta` es hoy; `None` si se consulta una fecha pasada.
    diferenciaConModuloTarjetas: float | None = None
    ultimoMovimiento: date | None = None
    cuotasAVencer: int = 0


class TotalTarjetas(BaseModel):
    deuda: float
    credito: float
    saldo: float


class TarjetaSinContacto(BaseModel):
    idTarjeta: int
    tarjeta: str
    motivo: str


class ResumenTarjetasResponse(BaseModel):
    hasta: date
    tarjetas: list[TarjetaSaldo]
    total: TotalTarjetas
    tarjetasSinContacto: list[TarjetaSinContacto]
    avisoSaldo: str = AVISO_SALDO


class ReferenciaFila(BaseModel):
    tipo: str  # linea-consumo | resumen | movimiento-bancario | cruce
    idLineaConsumo: int | None = None
    idResumen: int | None = None
    medio: str | None = None
    idMovimiento: int | None = None
    idCruce: int | None = None


class FilaCuenta(BaseModel):
    fecha: date | None = None
    origen: str  # Consumo | Cargo del resumen | Pago | Devolución
    idResumen: int | None = None
    codigo: str | None = None
    detalle: str | None = None
    proveedor: str | None = None
    deuda: float
    credito: float
    saldo: float
    # Solo en consumos: vinculado | resto-con-proveedor | sin-proveedor | cruzado-con-devolucion
    estadoVinculo: str | None = None
    referencia: ReferenciaFila | None = None


class CuotaAVencer(BaseModel):
    fechaVencimiento: date
    importe: float
    idCompra: int | None = None


class DetalleSaldo(BaseModel):
    """FR-023: a la fecha `hasta`, `exigible + noResumido` = saldo de la cuenta."""

    exigible: float
    noResumido: float


class Apertura(BaseModel):
    idContactoAnterior: int | None = None
    contactoAnterior: str | None = None
    informativo: bool = True


class CuentaTarjetaResponse(BaseModel):
    idTarjeta: int
    tarjeta: str
    idContacto: int
    desde: date | None = None
    hasta: date | None = None
    saldoInicial: float
    filas: list[FilaCuenta]
    saldoFinal: float
    detalleSaldo: DetalleSaldo
    cuotasAVencer: list[CuotaAVencer]
    apertura: Apertura
    avisoSaldo: str = AVISO_SALDO
    generado: datetime | None = None


class HallazgoControl(BaseModel):
    categoria: str
    idTarjeta: int | None = None
    tarjeta: str | None = None
    medio: str | None = None
    idMovimiento: int | None = None
    idResumen: int | None = None
    idLineaConsumo: int | None = None
    fecha: date | None = None
    importe: float | None = None
    motivo: str


class ControlResponse(BaseModel):
    generado: datetime
    resumenPorCategoria: dict[str, int]
    hallazgos: list[HallazgoControl]


class MovimientoRef(BaseModel):
    medio: str
    idMovimiento: int


class AltaCruce(BaseModel):
    tipo: str
    idTarjeta: int
    sugerido: bool = False
    origen: MovimientoRef
    destino: MovimientoRef | None = None
    idLineaConsumo: int | None = None


class CruceCreado(BaseModel):
    idCruce: int
    tipo: str
    importe: float
    usuario: str
    fecha: datetime


class Cruce(BaseModel):
    idCruce: int
    tipo: str
    idTarjeta: int
    medioOrigen: str
    idMovimientoOrigen: int
    medioDestino: str | None = None
    idMovimientoDestino: int | None = None
    idLineaConsumo: int | None = None
    importe: float
    sugerido: bool
    usuario: str | None = None
    fecha: datetime | None = None
    deshecho: bool
    usuarioDeshecho: str | None = None
    fechaDeshecho: datetime | None = None
