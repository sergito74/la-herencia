"""Exclusive edit-lock for Ventas de Hacienda (FR-006), backed by
`dbo.VentaHaciendaEditLocks` en `WC`.

Copia exacta del patrón de `src/features/compras/repository_locks.py`
(006-carga-compras, TTL corto + "forzar" tras la lección real de un solo
usuario auto-bloqueándose con pestañas viejas) — ver research.md §5 de
007-ventas-hacienda-granos.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.db.connection import execute_write, fetch_one

LOCK_TTL_MINUTES = 5


def _validar_formato_lock_token(lock_token: str) -> None:
    try:
        uuid.UUID(lock_token)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"lockToken inválido: debe ser un UUID, se recibió {lock_token!r}") from exc


@dataclass
class LockInfo:
    id_venta: int
    lock_token: str
    expires_at: datetime


def _get_lock_row(id_venta: int) -> dict | None:
    return fetch_one(
        "SELECT IdVenta, LockToken, LockedAt, ExpiresAt "
        "FROM dbo.VentaHaciendaEditLocks WHERE IdVenta = ?",
        (id_venta,),
    )


def _is_vigente(row: dict) -> bool:
    return row["ExpiresAt"] > datetime.now()


def _mismo_token(row: dict, lock_token: str) -> bool:
    return str(row["LockToken"]).lower() == lock_token.lower()


def adquirir_lock(id_venta: int, lock_token: str, force: bool = False) -> LockInfo | None:
    """Adquiere o renueva el lock. Devuelve `None` si está tomado por otro token vigente
    y `force=False`. Lanza `ValueError` si `lock_token` no es un UUID válido."""
    _validar_formato_lock_token(lock_token)
    row = _get_lock_row(id_venta)
    now = datetime.now()
    expires_at = now + timedelta(minutes=LOCK_TTL_MINUTES)

    if not force and row is not None and _is_vigente(row) and not _mismo_token(row, lock_token):
        return None

    if row is None:
        execute_write(
            "INSERT INTO dbo.VentaHaciendaEditLocks (IdVenta, LockToken, LockedAt, ExpiresAt) "
            "VALUES (?, ?, ?, ?)",
            (id_venta, lock_token, now, expires_at),
        )
    else:
        execute_write(
            "UPDATE dbo.VentaHaciendaEditLocks SET LockToken = ?, LockedAt = ?, ExpiresAt = ? "
            "WHERE IdVenta = ?",
            (lock_token, now, expires_at, id_venta),
        )
    return LockInfo(id_venta=id_venta, lock_token=lock_token, expires_at=expires_at)


def liberar_lock(id_venta: int, lock_token: str) -> bool:
    """Libera el lock si el token coincide (o si ya no había ninguno vigente). False si es de otro token."""
    row = _get_lock_row(id_venta)
    if row is None:
        return True
    if _is_vigente(row) and not _mismo_token(row, lock_token):
        return False
    execute_write("DELETE FROM dbo.VentaHaciendaEditLocks WHERE IdVenta = ?", (id_venta,))
    return True


def verificar_lock(id_venta: int, lock_token: str) -> bool:
    """True si no hay lock vigente para esa venta, o si el vigente es de este mismo token."""
    row = _get_lock_row(id_venta)
    if row is None:
        return True
    if not _is_vigente(row):
        return True
    return _mismo_token(row, lock_token)
