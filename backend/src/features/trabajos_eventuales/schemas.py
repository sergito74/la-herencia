from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

Dinero = Annotated[Decimal, Field(max_digits=18, decimal_places=2)]


class TrabajoInput(BaseModel):
    idContacto: int = Field(gt=0)
    fecha: date
    descripcion: str = Field(min_length=1, max_length=500)
    dias: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    jornal: Dinero = Field(ge=0)
    viaticos: Dinero = Field(default=Decimal(0), ge=0)
    redondeo: Dinero = Decimal(0)
    estadoPago: Literal["Pendiente", "Pagado"] = "Pendiente"
    numeroRecibo: str | None = Field(default=None, max_length=40)
    observaciones: str | None = Field(default=None, max_length=1000)

    @field_validator("descripcion")
    @classmethod
    def sin_blancos(cls, valor):
        if not valor.strip():
            raise ValueError("Completá la descripción del trabajo")
        return valor.strip()


class VinculoInput(BaseModel):
    idSalario: int = Field(gt=0)
    importe: Dinero = Field(gt=0)


class Vinculo(BaseModel):
    idSalario: int
    importe: float
    periodo: str | None = None
    fecha: date | None = None


class Trabajo(BaseModel):
    idTrabajo: int
    idContacto: int
    trabajador: str
    fecha: date
    descripcion: str
    dias: float
    jornal: float
    viaticos: float
    redondeo: float
    total: float
    estadoPago: str
    numeroRecibo: str | None = None
    observaciones: str | None = None
    vinculado: float
    sinVincular: float
    origen: str | None = None
    vinculos: list[Vinculo] = Field(default_factory=list)


class Resumen(BaseModel):
    cantidad: int
    totalTrabajos: float
    totalVinculado: float
    sinVincular: float


class Lista(BaseModel):
    items: list[Trabajo]
    total: int
    page: int
    pageSize: int
    resumen: Resumen


class Liquidacion(BaseModel):
    idSalario: int
    periodo: str | None = None
    fecha: date | None = None
    neto: float
    disponible: float
