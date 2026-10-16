"""Contratos de /api/descarga-peajes (specs/037-descarga-peajes/contracts/api.md)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class PortalConfiguracion(BaseModel):
    portal: str
    credenciales: bool


class TareaSemanal(BaseModel):
    instalada: bool
    proximaCorrida: str | None = None
    ultimoResultado: str | None = None


class EjecucionEnCurso(BaseModel):
    idEjecucion: int
    inicio: datetime
    origen: str


class Estado(BaseModel):
    portales: list[PortalConfiguracion]
    tarea: TareaSemanal
    enCurso: EjecucionEnCurso | None = None


class PortalResultado(BaseModel):
    portal: str
    estado: str
    nuevos: int
    existentes: int
    cargados: int
    pendientes: int
    error: str | None = None


class Documento(BaseModel):
    idDocumento: int
    portal: str
    proveedor: str
    idContacto: int | None = None
    fechaDocumento: date | None = None
    numeroDocumento: str | None = None
    totalImpreso: float | None = None
    ruta: str | None = None
    nombreArchivo: str | None = None
    estadoCarga: str
    motivo: str | None = None
    idCompra: int | None = None
    idEjecucion: int | None = None


class Ejecucion(BaseModel):
    idEjecucion: int
    origen: str
    usuario: str | None = None
    inicio: datetime
    fin: datetime | None = None
    estado: str
    mensaje: str | None = None
    portales: list[PortalResultado] = []


class EjecucionDetalle(Ejecucion):
    documentos: list[Documento] = []


class EjecucionesPagina(BaseModel):
    items: list[Ejecucion]
    total: int


class DocumentosPagina(BaseModel):
    items: list[Documento]
    total: int


class EjecucionIniciada(BaseModel):
    idEjecucion: int


class ResumenContador(BaseModel):
    pendientes: int
    portalesConError: int
