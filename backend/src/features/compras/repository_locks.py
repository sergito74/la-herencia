"""Exclusive edit-lock for Compras (FR-009a), backed by `dbo.CompraEditLocks` in `WC`.

No real authentication exists yet (ver `NavHeader.tsx`, botón de usuario
deshabilitado) — el "propietario" del lock es un token de sesión de
navegador (UUID) generado por el frontend por sesión de edición, no un
usuario real. Ver research.md §2 para el detalle de esta decisión.

`CompraEditLocks` es infraestructura de esta app, no dato de negocio
migrado: no existe en `LaHerencia`, solo en `WC`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.db.connection import execute_write, fetch_one

LOCK_TTL_MINUTES = 5
# Sistema de un solo usuario real (ver nota de arriba) — cuando se cierra
# una pestaña de edición sin que el `beforeunload`/cleanup llegue a
# liberar el lock (cierre abrupto, PC en suspensión, red caída), quedaba
# "vivo" hasta 15 minutos y el mismo usuario, al reabrir esa compra con un
# token nuevo, chocaba contra su propio lock abandonado — parecía "otra
# sesión" sin serlo. Se acorta la ventana y se agrega `force` (abajo) para
# que el usuario pueda liberarlo al toque si igual llega a pasar.


def _validar_formato_lock_token(lock_token: str) -> None:
    """`LockToken` es `uniqueidentifier` en SQL Server — un valor no-GUID
    hace fallar la conversión en el motor con un error 500 genérico en vez
    de un 400 claro. Se valida el formato en Python antes de tocar la base."""
    try:
        uuid.UUID(lock_token)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"lockToken inválido: debe ser un UUID, se recibió {lock_token!r}") from exc


@dataclass
class LockInfo:
    id_compra: int
    lock_token: str
    expires_at: datetime


def _get_lock_row(id_compra: int) -> dict | None:
    return fetch_one(
        "SELECT IdCompra, LockToken, LockedAt, ExpiresAt "
        "FROM dbo.CompraEditLocks WHERE IdCompra = ?",
        (id_compra,),
    )


def _is_vigente(row: dict) -> bool:
    return row["ExpiresAt"] > datetime.now()


def _mismo_token(row: dict, lock_token: str) -> bool:
    """SQL Server normaliza `uniqueidentifier` a mayúsculas al leerlo — comparar case-insensitive."""
    return str(row["LockToken"]).lower() == lock_token.lower()


def adquirir_lock(id_compra: int, lock_token: str, force: bool = False) -> LockInfo | None:
    """Adquiere o renueva el lock. Devuelve `None` si está tomado por otro token vigente.

    `force=True` (botón "Forzar edición" del frontend cuando aparece el
    error de bloqueo) ignora ese chequeo y toma el lock igual — pensado
    para el caso real de un solo usuario con una pestaña vieja colgada,
    no para resolver una edición concurrente genuina de dos personas.

    Lanza `ValueError` si `lock_token` no es un UUID válido (el router lo
    traduce a 400)."""
    _validar_formato_lock_token(lock_token)
    row = _get_lock_row(id_compra)
    now = datetime.now()
    expires_at = now + timedelta(minutes=LOCK_TTL_MINUTES)

    if not force and row is not None and _is_vigente(row) and not _mismo_token(row, lock_token):
        return None

    if row is None:
        execute_write(
            "INSERT INTO dbo.CompraEditLocks (IdCompra, LockToken, LockedAt, ExpiresAt) "
            "VALUES (?, ?, ?, ?)",
            (id_compra, lock_token, now, expires_at),
        )
    else:
        execute_write(
            "UPDATE dbo.CompraEditLocks SET LockToken = ?, LockedAt = ?, ExpiresAt = ? "
            "WHERE IdCompra = ?",
            (lock_token, now, expires_at, id_compra),
        )
    return LockInfo(id_compra=id_compra, lock_token=lock_token, expires_at=expires_at)


def liberar_lock(id_compra: int, lock_token: str) -> bool:
    """Libera el lock si el token coincide (o si ya no había ninguno vigente). False si es de otro token."""
    row = _get_lock_row(id_compra)
    if row is None:
        return True
    if _is_vigente(row) and not _mismo_token(row, lock_token):
        return False
    execute_write("DELETE FROM dbo.CompraEditLocks WHERE IdCompra = ?", (id_compra,))
    return True


def verificar_lock(id_compra: int, lock_token: str) -> bool:
    """True si no hay lock vigente para esa compra, o si el vigente es de este mismo token."""
    row = _get_lock_row(id_compra)
    if row is None:
        return True
    if not _is_vigente(row):
        return True
    return _mismo_token(row, lock_token)
