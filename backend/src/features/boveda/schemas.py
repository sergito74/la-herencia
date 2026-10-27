"""Esquemas de /api/boveda (042, contracts/api.md). Ninguna respuesta lleva secretos salvo `Revelado`."""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

TipoPortal = Literal["organismo", "proveedor", "cliente", "banco", "otro"]
Titular = Literal["empresa", "socio"]


class DatoEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    secreto: bool = False
    # En un dato secreto existente, vacío = conservar el valor guardado.
    valor: Optional[str] = Field(default=None, max_length=200)


class CredencialNueva(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    titular: Titular = "empresa"
    idSocio: Optional[int] = None
    usuario: Optional[str] = Field(default=None, max_length=120)
    clave: Optional[str] = Field(default=None, max_length=200)
    datos: list[DatoEntrada] = []

    def __repr__(self) -> str:
        return f"CredencialNueva(nombre={self.nombre!r}, clave=***)"


class CredencialEdicion(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=80)
    usuario: Optional[str] = Field(default=None, max_length=120)
    datos: Optional[list[DatoEntrada]] = None


class ClaveNueva(BaseModel):
    clave: str = Field(min_length=1, max_length=200)

    def __repr__(self) -> str:
        return "ClaveNueva(***)"


class PedidoRevelar(BaseModel):
    campo: str = Field(pattern=r"^(clave|dato:.{1,60})$")


class Revelado(BaseModel):
    valor: str


class DatoCredencial(BaseModel):
    nombre: str
    secreto: bool
    valor: Optional[str]


class CredencialSalida(BaseModel):
    idCredencial: int
    nombre: str
    titular: str
    idSocio: Optional[int]
    usuario: Optional[str]
    claveConfigurada: bool
    rechazada: bool
    datos: list[DatoCredencial]
    portales: list[int]


def _validar_url(v: Optional[str]) -> Optional[str]:
    if v is not None and not (v.startswith("https://") or v.startswith("http://")):
        raise ValueError("El enlace debe empezar con http:// o https://")
    return v


class PortalEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=8, max_length=400)
    tipo: TipoPortal
    idContacto: Optional[int] = None
    idCredencial: Optional[int] = None
    credencialNueva: Optional[CredencialNueva] = None
    codigoConector: Optional[str] = Field(default=None, max_length=30)
    notas: Optional[str] = Field(default=None, max_length=1000)

    _url = field_validator("url")(_validar_url)


class PortalEdicion(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=80)
    url: Optional[str] = Field(default=None, min_length=8, max_length=400)
    tipo: Optional[TipoPortal] = None
    idContacto: Optional[int] = None
    idCredencial: Optional[int] = None
    codigoConector: Optional[str] = Field(default=None, max_length=30)
    notas: Optional[str] = Field(default=None, max_length=1000)

    _url = field_validator("url")(_validar_url)

    @field_validator("nombre", "url", "tipo", mode="before")
    @classmethod
    def _no_nulo(cls, v):
        if v is None:
            raise ValueError("No puede quedar vacío")
        return v


class CredencialResumen(BaseModel):
    idCredencial: int
    nombre: str
    usuario: Optional[str]
    claveConfigurada: bool
    estado: Literal["ok", "faltante", "rechazada"]


class ConectorInfo(BaseModel):
    codigo: Optional[str]
    nombre: Optional[str] = None
    disponible: bool
    estadoCuenta: bool = False
    cargaCompras: bool = False


class Autorizacion(BaseModel):
    vigente: bool
    fecha: Optional[date] = None
    autorizadoPor: Optional[str] = None
    fuente: Optional[str] = None
    alcance: str = "solo_lectura_descarga"


class Programacion(BaseModel):
    frecuencia: str
    diaSemana: Optional[int]
    diaMes: Optional[int]
    hora: str
    proximaCorrida: Optional[str]
    suspendida: bool
    motivoSuspension: Optional[str]


class CorridaResumen(BaseModel):
    idCorrida: int
    inicio: str
    fin: Optional[str] = None
    estado: str
    nuevos: int
    existentes: int = 0
    cargados: int = 0
    pendientes: int = 0
    mensaje: Optional[str] = None


class Progreso(BaseModel):
    paso: Optional[str]
    hecho: Optional[int]
    total: Optional[int]


class FotoResumen(BaseModel):
    fechaCorte: date
    moneda: str
    saldoPortal: float
    saldoSistema: Optional[float]
    diferencia: Optional[float]


class PortalSalida(BaseModel):
    idPortal: int
    nombre: str
    url: str
    tipo: str
    idContacto: Optional[int]
    contacto: Optional[str]
    notas: Optional[str]
    credencial: Optional[CredencialResumen]
    conector: ConectorInfo
    autorizacion: Autorizacion
    programacion: Optional[Programacion]
    ultimaCorrida: Optional[CorridaResumen]
    ultimaFoto: Optional[FotoResumen]
    enCurso: bool
    enCola: bool = False
    progreso: Optional[Progreso] = None
    # Por qué no se puede sincronizar ahora (None = se puede).
    motivoNoSincroniza: Optional[str] = None
    recordatorio: Optional[str] = None


class Lista(BaseModel):
    items: list


class AutorizacionEntrada(BaseModel):
    fecha: date
    autorizadoPor: str = Field(min_length=1, max_length=60)
    fuente: Optional[str] = Field(default=None, max_length=300)


class ProgramacionEntrada(BaseModel):
    frecuencia: Literal["desactivada", "diaria", "semanal", "mensual"]
    diaSemana: Optional[int] = Field(default=None, ge=1, le=7)
    diaMes: Optional[int] = Field(default=None, ge=1, le=28)
    hora: str = Field(default="07:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class FotoRevision(BaseModel):
    revisada: bool


class PedidoSincronizar(BaseModel):
    """Portales a sincronizar ahora; vacío o ausente = todos los que se pueden."""
    idsPortales: Optional[list[int]] = None
