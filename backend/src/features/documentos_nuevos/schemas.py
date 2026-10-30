"""Esquemas de `/api/documentos-nuevos` (043, contracts/api.md)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Modulo = Literal["compras", "impuestos", "ventas", "tesoreria", "cuentas_corrientes", "sin_clasificar", "pagos"]


class Resumen(BaseModel):
    pagos: int = 0
    compras: int = 0
    impuestos: int = 0
    ventas: int = 0
    tesoreria: int = 0
    cuentasCorrientes: int = 0
    sinClasificar: int = 0
    total: int = 0


class Renglon(BaseModel):
    detalle: str | None = None
    rubro: str | None = None
    centroCosto: str | None = None
    importe: float | None = None
    iva: float | None = None


class Item(BaseModel):
    idDocumentoNuevo: int
    origen: str
    origenDetalle: str | None = None
    tipo: str
    modulo: Modulo
    estado: Literal["cargado_solo", "para_cargar"]
    motivo: str | None = None
    contacto: str | None = None
    idContacto: int | None = None
    fecha: str | None = None
    numero: str | None = None
    total: float | None = None
    archivo: str
    ruta: str
    idRegistro: int | None = None
    enlace: str | None = None
    renglones: list[Renglon] | None = None


class Lista(BaseModel):
    items: list[Item]
    total: int


class CambioModulo(BaseModel):
    modulo: Modulo


class CorridaRutina(BaseModel):
    inicio: str | None = None
    fin: str | None = None
    estado: str
    cuentasCorridas: int = 0
    cuentasConProblemas: int = 0
    mailsLeidos: int = 0
    documentosNuevos: int = 0
    cargadosSolos: int = 0
    paraCargarAMano: int = 0
    mensaje: str | None = None


class EstadoRutina(BaseModel):
    proxima: str | None = None
    activa: bool = True
    ultima: CorridaRutina | None = None
