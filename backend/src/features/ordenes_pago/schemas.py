from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Dinero = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
Estado = Literal['Borrador', 'Emitida', 'Pagada', 'Anulada']


class Estricto(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class FacturaInput(Estricto):
    idCompra: int = Field(gt=0)
    importe: Dinero


class MedioInput(Estricto):
    medio: Literal['Transferencia', 'Efectivo', 'Cheque']
    cuenta: str = Field(min_length=1, max_length=150)
    importe: Dinero


class OrdenInput(Estricto):
    idContacto: int = Field(gt=0)
    fecha: date
    fechaPago: date
    moneda: Literal['ARS'] = 'ARS'
    observaciones: str = Field(default='', max_length=1000)
    facturas: list[FacturaInput] = Field(min_length=1, max_length=100)
    medios: list[MedioInput] = Field(min_length=1, max_length=30)
    version: int | None = Field(default=None, gt=0)

    @model_validator(mode='after')
    def totales(self):
        if len({f.idCompra for f in self.facturas}) != len(self.facturas):
            raise ValueError('Una factura no puede repetirse')
        if sum(f.importe for f in self.facturas) != sum(m.importe for m in self.medios):
            raise ValueError('Los medios previstos deben sumar el importe de las facturas')
        return self


class AplicacionInput(FacturaInput):
    origenMovimiento: Literal['galicia', 'bna', 'efectivo']
    idMovimiento: int = Field(gt=0)


class VincularInput(Estricto):
    idContacto: int = Field(gt=0)
    numero: str = Field(min_length=1, max_length=50)
    fecha: date
    total: Dinero
    moneda: Literal['ARS'] = 'ARS'
    idOrdenPago: int | None = Field(default=None, gt=0)
    aplicaciones: list[AplicacionInput] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def totales(self):
        claves = [(a.origenMovimiento, a.idMovimiento, a.idCompra) for a in self.aplicaciones]
        if len(set(claves)) != len(claves):
            raise ValueError('No repitas el mismo pago y factura')
        if sum(a.importe for a in self.aplicaciones) != self.total:
            raise ValueError('Las aplicaciones deben sumar el total del recibo')
        return self


class OrdenResumen(BaseModel):
    idOrdenPago: int
    idContacto: int
    proveedor: str
    fecha: date
    fechaPago: date
    importeTotal: float
    moneda: str
    estado: Estado
    observaciones: str | None
    version: int


class FacturaDetalle(BaseModel):
    idCompra: int
    numero: str | None
    importe: float


class MedioDetalle(BaseModel):
    medio: str
    cuenta: str
    importe: float


class Orden(OrdenResumen):
    facturas: list[FacturaDetalle]
    medios: list[MedioDetalle]


class ListaOrdenes(BaseModel):
    items: list[OrdenResumen]
    total: int


class FacturaPendiente(BaseModel):
    idCompra: int
    numero: str | None
    fecha: date | None
    total: float
    pagado: float
    saldo: float
    reservado: float
    disponible: float


class Movimiento(BaseModel):
    origenMovimiento: str
    idMovimiento: int
    fecha: date | None
    importe: float
    disponible: float
