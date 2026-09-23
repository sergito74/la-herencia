"""Cookie de sesión firmada sin estado (016-autenticacion, Clarifications Q3).

HMAC-SHA256 sobre un payload JSON (`idUsuario`, `rol`, `exp`) — sin JWT ni
tabla de sesiones (constitución VII). El secreto vive en
`src.auth.secret.get_secret()`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from src.auth.secret import get_secret


def crear_token(id_usuario: int, rol: str, horas: int = 12) -> str:
    payload = {
        "idUsuario": id_usuario,
        "rol": rol,
        "exp": time.time() + horas * 3600,
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode()
    firma = hmac.new(get_secret(), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{firma}"


def verificar_token(token: str) -> dict | None:
    try:
        payload_b64, firma = token.split(".", 1)
    except ValueError:
        return None

    firma_esperada = hmac.new(get_secret(), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(firma, firma_esperada):
        return None

    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    except (ValueError, UnicodeDecodeError):
        return None

    if payload.get("exp", 0) < time.time():
        return None

    return payload
