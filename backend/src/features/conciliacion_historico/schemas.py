"""Schemas de conciliación histórica (020) — ver contracts/api.md."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ResumenContacto(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    aplicadosExactos: int
    aplicadosMejorEsfuerzo: int
    revisionManual: int
    fueraDeAlcance: int


class ResumenResponse(BaseModel):
    contactos: list[ResumenContacto]


class AplicacionAutomatica(BaseModel):
    idAplicacion: int
    origen: str
    origenMovimiento: str
    idMovimientoOrigen: int
    tipoDocumento: str
    idDocumentoAplicado: int
    importeAplicado: float
    notaConciliacion: str | None = None


class ExcepcionMovimiento(BaseModel):
    origenMovimiento: str
    idMovimientoOrigen: int
    subcategoria: str
    motivo: str | None = None


class DetalleContactoResponse(BaseModel):
    idContacto: int
    aplicaciones: list[AplicacionAutomatica]
    excepciones: list[ExcepcionMovimiento]


class ComparacionSaldo(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    saldoActual: float
    saldoReferencia: float
    fechaCorteReferencia: date
    diferencia: float
    estado: str


class SaldosResponse(BaseModel):
    contactos: list[ComparacionSaldo]
