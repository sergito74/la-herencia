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


class FlujoCajaPorRubroResponse(BaseModel):
    periodos: list[str]
    saldoInicial: float
    ingresos: SeccionIngresos
    egresos: SeccionEgresos
