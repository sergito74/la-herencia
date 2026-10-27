"""Conectores de portales (042, research.md R4).

Cada conector sabe entrar a un portal, listar sus documentos y, si el
portal lo ofrece, leer el estado de cuenta. Solo navega, lee y descarga:
nunca hace clic en pagar, presentar, confirmar, aceptar, firmar ni enviar.
Ante captcha o segundo factor se detiene con `RequiereIntervencion`.

Un portal cuyo `CodigoConector` no está en `CONECTORES` es "solo bóveda".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Callable, Protocol

from src.features.boveda.cifrado import Secreto


class RequiereIntervencion(Exception):
    """El portal pidió captcha, segundo factor u otra verificación humana."""


class CredencialesRechazadas(Exception):
    """El portal rechazó usuario o contraseña."""


class PortalCambio(Exception):
    """La página no tiene lo que el conector espera (el portal cambió)."""


@dataclass
class Credencial:
    usuario: str | None
    clave: Secreto | None
    datos: dict[str, str | Secreto] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Credencial(usuario={self.usuario!r}, clave=***, datos={sorted(self.datos)})"


@dataclass
class DocumentoPortal:
    clave: str
    fecha: date | None
    tipo: str  # factura | nota_credito | nota_debito | resumen | certificado | boleta | poliza | liquidacion | otro
    proveedor: str  # parte del nombre AAAAMMDD_Proveedor.pdf
    bajar: Callable[[], bytes]
    numero: str | None = None
    total: Decimal | None = None
    moneda: str | None = None
    detalle: str | None = None
    id_contacto: int | None = None
    # Patrones LIKE de claves con que otro portal ofrece el mismo comprobante (ej. AUBASA en TelePASE).
    equivalentes: list[str] = field(default_factory=list)


@dataclass
class MovimientoCuenta:
    fecha: date | None
    comprobante: str | None
    detalle: str | None
    debe: Decimal | None
    haber: Decimal | None
    saldo: Decimal | None


@dataclass
class EstadoCuentaPortal:
    fecha_corte: date
    moneda: str  # ARS | USD
    saldo: Decimal  # positivo = deuda nuestra con el tercero
    completa: bool
    movimientos: list[MovimientoCuenta] = field(default_factory=list)


@dataclass
class DatosCompra:
    """Lo leído de un comprobante, armado como alta de Compras (`cabecera`, `lineas` de compras.repository).
    La carga calcula el total con las reglas de Compras y lo compara al centavo con `total_impreso`."""

    cabecera: dict
    lineas: list[dict]
    numero: str
    total_impreso: Decimal


@dataclass
class MapeoProveedor:
    id_contacto: int
    rubro: str | None = None
    centro_costo: str | None = None


class Conector(Protocol):
    codigo: str
    nombre: str
    tiene_estado_cuenta: bool
    tiene_carga_compras: bool
    mapeo_proveedores: dict[str, MapeoProveedor]

    def ingresar(self, pw, credencial: Credencial): ...

    def listar_documentos(self, sesion) -> list[DocumentoPortal]: ...

    def estado_cuenta(self, sesion) -> list[EstadoCuentaPortal]: ...

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes) -> DatosCompra | None: ...

    def cerrar(self, sesion) -> None: ...


CONECTORES: dict[str, Conector] = {}


def registrar(conector: Conector) -> Conector:
    CONECTORES[conector.codigo] = conector
    return conector


# Módulos con conectores; cada uno se registra con `registrar` al importarse.
MODULOS: tuple[str, ...] = ("peajes", "cargill", "baya_casal", "arba", "arca", "sancor", "jauregui_morales",
                             "chrome_comun", "decampoacampo", "cebol")


def cargar_conectores() -> dict[str, Conector]:
    import importlib

    for modulo in MODULOS:
        importlib.import_module(f"src.features.boveda.conectores.{modulo}")
    return CONECTORES
