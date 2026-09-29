"""Schemas de Conciliación de Tesorería (023) — ver
contracts/conciliacion-tesoreria-api.md."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, model_validator

OrigenDocumento = Literal["Compras", "Impuestos", "Remuneraciones", "Alquileres"]


class ReferenciaDocumento(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origen: OrigenDocumento
    idOrigen: int = Field(ge=-(2**63), le=2**63 - 1)


class MotivoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    motivo: str = Field(min_length=1, max_length=30)
    detalle: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def otro_con_detalle(self):
        if self.motivo == "Otro" and not self.detalle:
            raise ValueError("Otro requiere detalle.")
        return self


class ConciliarLoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documentos: list[ReferenciaDocumento] = Field(min_length=1, max_length=20)
    aceptarDiferencia: MotivoRequest | None = None

    @model_validator(mode="after")
    def sin_repetidos(self):
        keys = {(d.origen, d.idOrigen) for d in self.documentos}
        if len(keys) != len(self.documentos):
            raise ValueError("Hay documentos repetidos.")
        return self


class Documento(ReferenciaDocumento):
    model_config = ConfigDict(extra="ignore")
    fecha: datetime | None = None
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None
    moneda: str | None = None
    tipoDeCambio: float | None = None
    importeOriginal: float
    importePesos: float
    idContacto: int | None = None
    contraparte: str | None = None
    saldoPendiente: float
    vinculosPrevios: int = 0


class Imputado(ReferenciaDocumento):
    importeImputado: float


class Calculo(BaseModel):
    estado: Literal["exacta", "parcial"]
    diferencia: float
    pagoParcial: bool
    permiteParcial: bool
    imputados: list[Imputado]
    tcImplicito: float | None = None
    tcReferencia: float | None = None
    desvioTc: float | None = None


class Sugerencia(Calculo):
    documentos: list[ReferenciaDocumento]


class Candidatos(BaseModel):
    documentos: list[Documento]
    sugerencias: list[Sugerencia]


class Auditoria(BaseModel):
    idEstado: int
    estado: str
    motivo: str
    detalle: str | None
    importeDiferencia: float | None
    usuario: str
    fecha: datetime


class ConciliarRequest(BaseModel):
    idContacto: int
    importe: float = Field(gt=0)


class Conciliacion(BaseModel):
    idConciliacion: int
    idContacto: int
    contacto: str | None = None
    importe: float
    usuario: str
    fecha: datetime
    tipoOrigenDocumento: OrigenDocumento | None = None
    idOrigenDocumento: int | None = None


class EstadoConciliacion(BaseModel):
    estado: str  # sin_conciliar | parcialmente_conciliado | conciliado | ya_reconocido
    importeTotal: float
    saldoPendiente: float
    conciliaciones: list[Conciliacion]
    # Solo poblados cuando estado == "ya_reconocido" (FR-008/US3): el
    # contacto que ya tiene este movimiento por su origen automático
    # habitual, para que el frontend pueda linkear a su cuenta corriente
    # en vez de ofrecer conciliar de nuevo.
    idContactoReconocido: int | None = None
    contactoReconocido: str | None = None
    auditoria: Auditoria | None = None
