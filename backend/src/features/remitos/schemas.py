"""Cuerpos de entrada de los endpoints de Remitos y stock."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class RenglonIn(BaseModel):
    idDetalle: int | None = None
    idProducto: int
    cantidad: float
    unidad: str
    vencimiento: date | None = None
    # Solo al remitar por primera vez un producto: su unidad base y, si se remita en una
    # presentación (bolsa, bidón…), cuántas unidades base tiene una.
    unidadBase: str | None = None
    factorUnidad: float | None = None


class RemitoIn(BaseModel):
    fecha: date
    idProveedor: int
    nroRemito: str
    idEstablecimiento: int | None = None
    observaciones: str | None = None
    archivo: str | None = None
    renglones: list[RenglonIn] = Field(min_length=1)
    # El usuario confirmó las advertencias (número duplicado o con otro formato).
    confirmar: bool = False


class ValidarRemitoIn(BaseModel):
    idProveedor: int
    nroRemito: str
    idExcluir: int | None = None


class AnularIn(BaseModel):
    motivo: str


class VinculoItem(BaseModel):
    idDetalleRemito: int
    idDetalleCompra: int
    cantidad: float


class VincularIn(BaseModel):
    items: list[VinculoItem] = Field(min_length=1)


class FacturaIn(BaseModel):
    idCompra: int


class UnidadBaseIn(BaseModel):
    unidad: str


class EquivalenciaIn(BaseModel):
    unidad: str
    factor: float


class ConfirmarUnidadesIn(BaseModel):
    ids: list[int] = Field(min_length=1)


class BajaRenglonIn(BaseModel):
    idProducto: int
    cantidad: float
    unidad: str | None = None


class BajaIn(BaseModel):
    fecha: date
    motivo: str
    detalle: str | None = None
    idRubro: int
    idCentro: int
    renglones: list[BajaRenglonIn] = Field(min_length=1)
    confirmar: bool = False


class AjusteIn(BaseModel):
    fecha: date
    idProducto: int
    cantidad: float  # con signo: + sobrante, − faltante
    unidad: str | None = None
    costoUnitario: float | None = None
    motivo: str
    confirmar: bool = False
