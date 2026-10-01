"""Schemas del flujo de caja real (018) — ver contracts/api-flujo-caja.md."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

Granularidad = str  # "mensual" | "semanal"


class CuentaResumen(BaseModel):
    banco: str
    numeroCuenta: str
    ingresos: float
    egresos: float
    neto: float


class MovimientosInternos(BaseModel):
    ingresos: float
    egresos: float
    total: float


class SinClasificar(BaseModel):
    cantidad: int
    importeAbsoluto: float


class PeriodoResumen(BaseModel):
    periodo: str
    porCuenta: list[CuentaResumen]
    totalIngresos: float
    totalEgresos: float
    totalNeto: float
    movimientosInternos: MovimientosInternos
    sinClasificar: SinClasificar


class UltimaCarga(BaseModel):
    banco: str
    numeroCuenta: str
    fecha: datetime | None = None


class ResumenFlujoCajaResponse(BaseModel):
    periodos: list[PeriodoResumen]
    ultimaCarga: list[UltimaCarga]


class MovimientoFlujoCaja(BaseModel):
    fecha: datetime
    banco: str
    origenMovimiento: str | None = None
    idMovimientoOrigen: int | None = None
    numeroCuentaBancaria: str | None = None
    concepto: str | None = None
    importe: float
    idContacto: int | None = None
    contacto: str | None = None
    esInterno: bool


class DetalleFlujoCajaResponse(BaseModel):
    movimientos: list[MovimientoFlujoCaja]


class FilaRubro(BaseModel):
    rubro: str
    valores: dict[str, float]
    total: float


class GrupoCentroCosto(BaseModel):
    centroCosto: str
    rubros: list[FilaRubro]
    subtotalPorPeriodo: dict[str, float]
    subtotal: float


class SeccionIngresos(BaseModel):
    rubros: list[FilaRubro]
    totalPorPeriodo: dict[str, float]


class SeccionEgresos(BaseModel):
    centrosCosto: list[GrupoCentroCosto]
    totalPorPeriodo: dict[str, float]


class SaldoCuenta(BaseModel):
    cuenta: str
    importe: float | None
    aclaracion: str | None = None


class SaldoInicial(BaseModel):
    cuentas: list[SaldoCuenta]
    total: float | None


class CeldaSinTipoCambio(BaseModel):
    periodo: str
    seccion: str
    centroCosto: str | None = None
    rubro: str
    cantidad: int
    importeArs: float


class TraspasoSinContraparte(BaseModel):
    fecha: date
    cuenta: str
    importe: float
    idMovimiento: int | None = None


class FlujoCajaPorRubroResponse(BaseModel):
    """030 — contracts/api.md. `saldoInicial` pasó de número a objeto por cuenta."""

    moneda: str
    periodos: list[str]
    saldoInicial: SaldoInicial
    ingresos: SeccionIngresos
    egresos: SeccionEgresos
    netoOperativoPorPeriodo: dict[str, float]
    internos: SeccionIngresos
    saldoFinalPorPeriodo: dict[str, float | None]
    saldoFinalPorCuenta: dict[str, dict[str, float | None]]
    sinTipoCambio: list[CeldaSinTipoCambio]
    saldosSinTipoCambio: list[str]
    traspasosSinContraparte: list[TraspasoSinContraparte]
    ultimaFechaCotizacion: date | None = None


class DocumentoAplicado(BaseModel):
    tipo: str
    id: int
    via: str = "aplicacion"


class ParteMovimiento(BaseModel):
    fecha: date
    cuenta: str
    concepto: str | None = None
    contacto: str | None = None
    seccion: str
    rubro: str
    centroCosto: str | None = None
    importeArs: float
    importeMovimiento: float
    documentoAplicado: DocumentoAplicado | None = None
    cotizacion: float | None = None
    fechaCotizacion: date | None = None
    importeUsd: float | None = None
    origenMovimiento: str | None = None
    idMovimiento: int | None = None
    sinContraparte: bool = False


class DetalleCeldaRubroResponse(BaseModel):
    total: float
    items: list[ParteMovimiento]
