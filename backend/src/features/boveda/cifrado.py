"""Cifrado de los secretos de la bóveda (042, research.md R1).

AES-256-GCM con una clave maestra de 32 bytes que vive en el Administrador
de credenciales de Windows (servicio `LaHerencia-Boveda`, cuenta
`clave-maestra`), nunca en `WC`: una copia de la base sola no descifra nada.
En la base se guarda `nonce (12 B) + cifrado + tag`. Los datos asociados
(AAD) atan cada valor a su fila y campo, así que un blob copiado a otra
credencial no descifra.
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SERVICIO = "LaHerencia-Boveda"
CUENTA = "clave-maestra"
_NONCE = 12


class ClaveMaestraNoDisponible(Exception):
    pass


class Secreto:
    """Envoltorio de un valor secreto: nunca se imprime ni se loguea por accidente."""

    __slots__ = ("_valor",)

    def __init__(self, valor: str):
        self._valor = valor

    def valor(self) -> str:
        return self._valor

    def __repr__(self) -> str:
        return "Secreto(***)"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return "***"


def _keyring():
    import keyring

    return keyring


def clave_maestra(crear: bool = False) -> bytes:
    """Lee la clave maestra. Solo la genera con `crear=True` (`boveda_clave generar`, o la primera
    credencial cuando la bóveda no tiene ningún secreto): nunca en silencio sobre secretos existentes."""
    try:
        guardada = _keyring().get_password(SERVICIO, CUENTA)
    except Exception as exc:  # backend de credenciales caído
        raise ClaveMaestraNoDisponible("No se pudo leer el Administrador de credenciales de Windows.") from exc
    if guardada:
        return base64.b64decode(guardada)
    if not crear:
        raise ClaveMaestraNoDisponible("La bóveda no tiene clave maestra en este equipo.")
    nueva = os.urandom(32)
    guardar_clave_maestra(nueva)
    return nueva


def guardar_clave_maestra(clave: bytes) -> None:
    if len(clave) != 32:
        raise ValueError("La clave maestra debe tener 32 bytes.")
    _keyring().set_password(SERVICIO, CUENTA, base64.b64encode(clave).decode("ascii"))


def aad_clave(id_credencial: int) -> str:
    return f"boveda:{id_credencial}:clave"


def aad_dato(id_credencial: int, nombre: str) -> str:
    return f"boveda:{id_credencial}:dato:{nombre}"


def cifrar(valor: str, aad: str, clave: bytes | None = None) -> bytes:
    nonce = os.urandom(_NONCE)
    cifrado = AESGCM(clave or clave_maestra()).encrypt(nonce, valor.encode("utf-8"), aad.encode("utf-8"))
    return nonce + cifrado


def descifrar(blob: bytes, aad: str, clave: bytes | None = None) -> Secreto:
    datos = bytes(blob)
    texto = AESGCM(clave or clave_maestra(crear=False)).decrypt(datos[:_NONCE], datos[_NONCE:], aad.encode("utf-8"))
    return Secreto(texto.decode("utf-8"))
