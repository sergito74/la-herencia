"""Fixtures de la bóveda (042): keyring y repositorio simulados, sin conexión a `WC`."""

from __future__ import annotations

import os

os.environ.setdefault("LA_HERENCIA_SIN_PLANIFICADOR", "1")

import pytest
from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.main import app


class KeyringFalso:
    def __init__(self):
        self.valores: dict[tuple[str, str], str] = {}

    def get_password(self, servicio, cuenta):
        return self.valores.get((servicio, cuenta))

    def set_password(self, servicio, cuenta, valor):
        self.valores[(servicio, cuenta)] = valor


@pytest.fixture
def keyring_falso(monkeypatch):
    from src.features.boveda import cifrado

    falso = KeyringFalso()
    monkeypatch.setattr(cifrado, "_keyring", lambda: falso)
    cifrado.clave_maestra(crear=True)
    return falso


@pytest.fixture
def client():
    c = TestClient(app)
    yield c
    c.cookies.clear()


def iniciar_sesion(client: TestClient, rol: str) -> None:
    client.cookies.set(COOKIE_NAME, crear_token(id_usuario=1, rol=rol))
