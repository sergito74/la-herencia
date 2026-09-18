"""Exclusive edit-lock for Compras en Cuotas (FR-013), backed by
`dbo.TarjetaCuotasEditLocks` en `WC`. Mismo patrón que
`tarjetas_resumenes/repository_locks.py`."""

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
    id_pago_tarjeta: int
    lock_token: str
    expires_at: datetime


def _get_lock_row(id_pago_tarjeta: int) -> dict | None:
    return fetch_one(
        "SELECT IdPagoTarjeta, LockToken, LockedAt, ExpiresAt "
        "FROM dbo.TarjetaCuotasEditLocks WHERE IdPagoTarjeta = ?",
        (id_pago_tarjeta,),
    )


def _is_vigente(row: dict) -> bool:
    return row["ExpiresAt"] > datetime.now()


def _mismo_token(row: dict, lock_token: str) -> bool:
    return str(row["LockToken"]).lower() == lock_token.lower()


def adquirir_lock(id_pago_tarjeta: int, lock_token: str, force: bool = False) -> LockInfo | None:
    _validar_formato_lock_token(lock_token)
    row = _get_lock_row(id_pago_tarjeta)
    now = datetime.now()
    expires_at = now + timedelta(minutes=LOCK_TTL_MINUTES)

    if not force and row is not None and _is_vigente(row) and not _mismo_token(row, lock_token):
        return None

    if row is None:
        execute_write(
            "INSERT INTO dbo.TarjetaCuotasEditLocks (IdPagoTarjeta, LockToken, LockedAt, ExpiresAt) "
            "VALUES (?, ?, ?, ?)",
            (id_pago_tarjeta, lock_token, now, expires_at),
        )
    else:
        execute_write(
            "UPDATE dbo.TarjetaCuotasEditLocks SET LockToken = ?, LockedAt = ?, ExpiresAt = ? "
            "WHERE IdPagoTarjeta = ?",
            (lock_token, now, expires_at, id_pago_tarjeta),
        )
    return LockInfo(id_pago_tarjeta=id_pago_tarjeta, lock_token=lock_token, expires_at=expires_at)


def liberar_lock(id_pago_tarjeta: int, lock_token: str) -> bool:
    row = _get_lock_row(id_pago_tarjeta)
    if row is None:
        return True
    if _is_vigente(row) and not _mismo_token(row, lock_token):
        return False
    execute_write("DELETE FROM dbo.TarjetaCuotasEditLocks WHERE IdPagoTarjeta = ?", (id_pago_tarjeta,))
    return True


def verificar_lock(id_pago_tarjeta: int, lock_token: str) -> bool:
    row = _get_lock_row(id_pago_tarjeta)
    if row is None:
        return True
    if not _is_vigente(row):
        return True
    return _mismo_token(row, lock_token)
