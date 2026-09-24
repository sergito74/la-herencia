"""Tests del middleware global de auth (016-autenticacion)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.main import app

client = TestClient(app)

# Un endpoint de escritura real por cada uno de 5 módulos distintos (SC-002).
WRITE_ENDPOINTS = [
    "/api/compras",
    "/api/contactos",
    "/api/tesoreria/excel/validar",
    "/api/remitos",
    "/api/tarjetas",
]


def test_sin_cookie_devuelve_401_en_endpoint_cualquiera():
    resp = client.get("/api/compras")
    assert resp.status_code == 401


def test_cookie_lectura_permite_get_pero_rechaza_escrituras():
    token = crear_token(id_usuario=1, rol="Lectura")
    client.cookies.set(COOKIE_NAME, token)
    try:
        resp = client.get("/api/compras")
        assert resp.status_code != 401

        for path in WRITE_ENDPOINTS:
            resp = client.post(path, json={})
            assert resp.status_code == 403, f"{path} debería rechazar escritura de Lectura"
    finally:
        client.cookies.clear()


def test_cookie_administrador_no_es_bloqueada_por_el_middleware():
    token = crear_token(id_usuario=1, rol="Administrador")
    client.cookies.set(COOKIE_NAME, token)
    try:
        for path in WRITE_ENDPOINTS:
            resp = client.post(path, json={})
            assert resp.status_code != 401
            assert resp.status_code != 403
    finally:
        client.cookies.clear()


def test_cookie_con_exp_vencido_devuelve_401():
    token = crear_token(id_usuario=1, rol="Administrador", horas=-1)
    client.cookies.set(COOKIE_NAME, token)
    try:
        resp = client.get("/api/compras")
        assert resp.status_code == 401
    finally:
        client.cookies.clear()


def test_login_y_health_no_requieren_cookie():
    resp = client.get("/health")
    assert resp.status_code == 200

    resp = client.post("/api/auth/login", json={"usuario": "no-existe", "password": "x"})
    assert resp.status_code != 401 or resp.json()["detail"] != "Sesión inválida o expirada"


def test_sesion_no_requiere_cookie():
    """El heartbeat del launcher (`launcher/LaHerencia.ps1`) y la pestaña del
    navegador llaman a /api/sesion/* sin login — nunca tuvo acceso a WC.
    Regresión real (2026-09-24): sin este exento, `POST /api/sesion/inicio`
    quedaba bloqueado con 401 y el launcher no arrancaba el sistema."""
    resp = client.post("/api/sesion/inicio")
    assert resp.status_code != 401

    resp = client.get("/api/sesion/estado")
    assert resp.status_code != 401
