"""Schemas de reasignación de contacto (022) — ver contracts/api.md."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReasignarRequest(BaseModel):
    origen: str
    idOrigen: int
    idContactoNuevo: int
    motivo: str | None = None


class Reasignacion(BaseModel):
    idReasignacion: int
    origen: str
    idOrigen: int
    idContactoAnterior: int
    idContactoNuevo: int
    contactoAnterior: str | None = None
    contactoNuevo: str | None = None
    motivo: str | None = None
    usuario: str
    fecha: datetime


class HistorialResponse(BaseModel):
    items: list[Reasignacion]


class Candidato(BaseModel):
    origen: str
    idOrigen: int
    fecha: datetime
    descripcion: str | None = None
    importe: float
    idContactoActual: int
    contactoActual: str | None = None
    idContactoSugerido: int
    contactoSugerido: str | None = None


class CandidatosResponse(BaseModel):
    candidatos: list[Candidato]


class DescartarCandidatoRequest(BaseModel):
    origen: str
    idOrigen: int
    idContactoSugerido: int
