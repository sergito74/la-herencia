"""Exclusive edit-lock for Resúmenes de Tarjeta (FR-013), backed by
`dbo.TarjetaResumenEditLocks` en `WC`.

Copia exacta del patrón de `ventas_hacienda/repository_locks.py`
(TTL corto + "forzar").
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
    id_resumen: int
    lock_token: str
    expires_at: datetime


def _get_lock_row(id_resumen: int) -> dict | None:
    return fetch_one(
        "SELECT IdResumen, LockToken, LockedAt, ExpiresAt "
        "FROM dbo.TarjetaResumenEditLocks WHERE IdResumen = ?",
        (id_resumen,),
    )


def _is_vigente(row: dict) -> bool:
    return row["ExpiresAt"] > datetime.now()


def _mismo_token(row: dict, lock_token: str) -> bool:
    return str(row["LockToken"]).lower() == lock_token.lower()


def adquirir_lock(id_resumen: int, lock_token: str, force: bool = False) -> LockInfo | None:
    _validar_formato_lock_token(lock_token)
    row = _get_lock_row(id_resumen)
    now = datetime.now()
    expires_at = now + timedelta(minutes=LOCK_TTL_MINUTES)

    if not force and row is not None and _is_vigente(row) and not _mismo_token(row, lock_token):
        return None

    if row is None:
        execute_write(
            "INSERT INTO dbo.TarjetaResumenEditLocks (IdResumen, LockToken, LockedAt, ExpiresAt) "
            "VALUES (?, ?, ?, ?)",
            (id_resumen, lock_token, now, expires_at),
        )
    else:
        execute_write(
            "UPDATE dbo.TarjetaResumenEditLocks SET LockToken = ?, LockedAt = ?, ExpiresAt = ? "
            "WHERE IdResumen = ?",
            (lock_token, now, expires_at, id_resumen),
        )
    return LockInfo(id_resumen=id_resumen, lock_token=lock_token, expires_at=expires_at)


def liberar_lock(id_resumen: int, lock_token: str) -> bool:
    row = _get_lock_row(id_resumen)
    if row is None:
        return True
    if _is_vigente(row) and not _mismo_token(row, lock_token):
        return False
    execute_write("DELETE FROM dbo.TarjetaResumenEditLocks WHERE IdResumen = ?", (id_resumen,))
    return True


def verificar_lock(id_resumen: int, lock_token: str) -> bool:
    row = _get_lock_row(id_resumen)
    if row is None:
        return True
    if not _is_vigente(row):
        return True
    return _mismo_token(row, lock_token)
