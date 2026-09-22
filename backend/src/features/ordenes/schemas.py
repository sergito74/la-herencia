"""Cuerpos de entrada de los endpoints de Órdenes de Trabajo."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class DistribIn(BaseModel):
    idLote: int
    idCultivo: int
    idCampania: int
    dosisHa: float
    superficie: float
    aplicar: bool = True


class RenglonInsumoIn(BaseModel):
    idProducto: int
    unidad: str
    cantidadTotal: float
    distribuciones: list[DistribIn] = Field(min_length=1)


class OrdenIn(BaseModel):
    fecha: date
    idTipoLabor: int
    idContratistaContacto: int | None = None
    renglones: list[RenglonInsumoIn] = Field(min_length=1)
    idRubro: int | None = None
    idCentroCostos: int | None = None
    observaciones: str | None = None
    # El usuario confirmó las advertencias (consumo mayor al stock disponible).
    confirmar: bool = False


class EjecutarIn(BaseModel):
    fechaEjecucion: date


class AnularIn(BaseModel):
    motivo: str


class DevolucionIn(BaseModel):
    fecha: date
    cantidad: float
    observaciones: str | None = None


class MaquinariaIn(BaseModel):
    descripcion: str
    costoPorHectarea: float
    tipoCambioBna: float | None = None


class FacturaContratistaIn(BaseModel):
    idCompra: int


class TipoLaborIn(BaseModel):
    nombre: str
