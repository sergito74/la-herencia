"""Unit tests for the lock-token format guard in repository_locks.py.

`adquirir_lock` validates the token's UUID format before touching the
database — a malformed token bound to a `uniqueidentifier` column fails
with an opaque SQL conversion error (500) instead of a clean 400.
"""

from __future__ import annotations

import pytest

from src.features.compras import repository_locks


def test_adquirir_lock_rejects_non_uuid_token_before_hitting_db():
    with pytest.raises(ValueError, match="lockToken inválido"):
        repository_locks.adquirir_lock(1, "no-es-un-uuid")


def test_adquirir_lock_accepts_valid_uuid_format(monkeypatch):
    monkeypatch.setattr(repository_locks, "_get_lock_row", lambda id_compra: None)
    captured = {}
    monkeypatch.setattr(
        "src.features.compras.repository_locks.execute_write",
        lambda sql, params: captured.setdefault("params", params),
    )

    lock = repository_locks.adquirir_lock(1, "3fa85f64-5717-4562-b3fc-2c963f66afa6")

    assert lock is not None
    assert lock.lock_token == "3fa85f64-5717-4562-b3fc-2c963f66afa6"


def test_adquirir_lock_force_ignora_lock_vigente_de_otro_token(monkeypatch):
    """"Forzar edición" (2026-09-17) — con `force=True`, un lock vigente de
    OTRO token no bloquea la adquisición (caso real: pestaña vieja del
    mismo usuario que quedó colgada, no una edición concurrente genuina)."""
    from datetime import datetime, timedelta

    otro_token = "11111111-1111-1111-1111-111111111111"
    nuevo_token = "22222222-2222-2222-2222-222222222222"
    monkeypatch.setattr(
        repository_locks,
        "_get_lock_row",
        lambda id_compra: {
            "IdCompra": id_compra,
            "LockToken": otro_token,
            "LockedAt": datetime.now(),
            "ExpiresAt": datetime.now() + timedelta(minutes=5),
        },
    )
    captured = {}
    monkeypatch.setattr(
        "src.features.compras.repository_locks.execute_write",
        lambda sql, params: captured.setdefault("params", params),
    )

    sin_force = repository_locks.adquirir_lock(1, nuevo_token, force=False)
    assert sin_force is None

    con_force = repository_locks.adquirir_lock(1, nuevo_token, force=True)
    assert con_force is not None
    assert con_force.lock_token == nuevo_token
