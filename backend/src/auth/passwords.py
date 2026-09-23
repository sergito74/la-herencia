"""Hash y verificación de contraseñas (016-autenticacion, FR-008).

`pbkdf2_hmac` (stdlib, sin dependencias nuevas — constitución VIII), sal
aleatoria por contraseña. Formato de almacenamiento: `salt$hash`, ambos
en base64.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_b64, digest_b64 = password_hash.split("$", 1)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except (ValueError, UnicodeDecodeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return hmac.compare_digest(actual, expected)
