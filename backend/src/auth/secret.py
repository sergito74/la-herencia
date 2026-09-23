"""Secreto de firma de sesión (016-autenticacion).

Vive en `backend/.auth_secret`, fuera de Git (Clarifications Q3): un
archivo de 32 bytes aleatorios, generado la primera vez que se necesita.
No requiere ningún paso manual (Edge Cases de spec.md).
"""

from __future__ import annotations

import secrets
from pathlib import Path

_SECRET_PATH = Path(__file__).resolve().parent.parent.parent / ".auth_secret"


def get_secret() -> bytes:
    if _SECRET_PATH.exists():
        return _SECRET_PATH.read_bytes()
    secret = secrets.token_bytes(32)
    _SECRET_PATH.write_bytes(secret)
    return secret
