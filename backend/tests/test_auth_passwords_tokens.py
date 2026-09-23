"""Tests de las primitivas puras de auth (016-autenticacion, sin HTTP)."""

from __future__ import annotations

import time

from src.auth import passwords, tokens


def test_hash_and_verify_correct_password():
    hashed = passwords.hash_password("Secreto123")
    assert passwords.verify_password("Secreto123", hashed)


def test_verify_rejects_incorrect_password():
    hashed = passwords.hash_password("Secreto123")
    assert not passwords.verify_password("otraCosa", hashed)


def test_crear_y_verificar_token_valido():
    token = tokens.crear_token(id_usuario=1, rol="Administrador")
    payload = tokens.verificar_token(token)
    assert payload is not None
    assert payload["idUsuario"] == 1
    assert payload["rol"] == "Administrador"


def test_verificar_token_expirado(monkeypatch):
    monkeypatch.setattr(tokens.time, "time", lambda: 1_000_000_000)
    token = tokens.crear_token(id_usuario=1, rol="Administrador", horas=1)
    monkeypatch.setattr(tokens.time, "time", lambda: 1_000_000_000 + 2 * 3600)
    assert tokens.verificar_token(token) is None


def test_verificar_token_con_firma_alterada():
    token = tokens.crear_token(id_usuario=1, rol="Administrador")
    payload_b64, _firma = token.split(".", 1)
    token_alterado = f"{payload_b64}.firmafalsa"
    assert tokens.verificar_token(token_alterado) is None
