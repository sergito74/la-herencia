"""Tests de /api/cajas-efectivo (027) — ver contracts/api.md. Monkeypatch
sobre repository, sin tocar WC real (mismo criterio que 021/023)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.cajas_efectivo import repository
from src.main import app

client = TestClient(app)
client.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))


def test_saldo_giamigli_sa(monkeypatch):
    monkeypatch.setattr(repository, "calcular_saldo", lambda caja: 152340.18)
    response = client.get("/api/cajas-efectivo/giamigli-sa/saldo")
    assert response.status_code == 200
    body = response.json()
    assert body["caja"] == "giamigli-sa"
    assert body["saldo"] == 152340.18


def test_saldo_campo_chica(monkeypatch):
    capturado = {}

    def fake_calcular_saldo(caja):
        capturado["caja"] = caja
        return 500.0

    monkeypatch.setattr(repository, "calcular_saldo", fake_calcular_saldo)
    response = client.get("/api/cajas-efectivo/campo-chica/saldo")
    assert response.status_code == 200
    assert capturado["caja"] == "CampoChica"


def test_caja_invalida_404():
    response = client.get("/api/cajas-efectivo/otra-cosa/saldo")
    assert response.status_code == 404


def test_movimientos_paginado(monkeypatch):
    monkeypatch.setattr(repository, "listar_movimientos", lambda caja, page, pageSize: ([], 0))
    response = client.get("/api/cajas-efectivo/giamigli-sa/movimientos?page=1&pageSize=20")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["pageSize"] == 20
    assert body["total"] == 0
