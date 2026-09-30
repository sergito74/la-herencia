"""Tests de la cola de revisión de la migración de Cajas Giamigli (027) —
repository (fixtures) y endpoint (TestClient), mismo criterio que
`test_cuentas_socios_endpoints.py`: solo lectura, sin tocar `WC` real."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.migracion_cajas_giamigli import repository
from src.main import app

client = TestClient(app)
client.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))


def test_listar_casos_a_revisar_sin_filtro(monkeypatch):
    capturado = {}

    def fake_fetch_all(sql, params=()):
        capturado["sql"] = sql
        capturado["params"] = params
        return [
            {
                "idRevision": 1, "hoja": "Cuenta Sergio", "numeroFila": 5, "motivo": "Sin fecha",
                "datosCrudos": "{}", "fechaCarga": "2026-09-30T00:00:00", "resuelto": 0,
            }
        ]

    monkeypatch.setattr(repository, "fetch_all", fake_fetch_all)
    resultado = repository.listar_casos_a_revisar(None)
    assert "WHERE" not in capturado["sql"]
    assert resultado[0]["resuelto"] is False


def test_listar_casos_a_revisar_filtra_por_resuelto(monkeypatch):
    capturado = {}

    def fake_fetch_all(sql, params=()):
        capturado["sql"] = sql
        capturado["params"] = params
        return []

    monkeypatch.setattr(repository, "fetch_all", fake_fetch_all)
    repository.listar_casos_a_revisar(True)
    assert "WHERE Resuelto = ?" in capturado["sql"]
    assert capturado["params"] == (1,)

    repository.listar_casos_a_revisar(False)
    assert capturado["params"] == (0,)


def test_endpoint_listar_revision(monkeypatch):
    monkeypatch.setattr(
        repository,
        "listar_casos_a_revisar",
        lambda resuelto: [
            {
                "idRevision": 1, "hoja": "Cuenta Sergio", "numeroFila": 5, "motivo": "Sin fecha",
                "datosCrudos": None, "fechaCarga": "2026-09-30T00:00:00", "resuelto": False,
            }
        ],
    )
    response = client.get("/api/migracion-cajas-giamigli/revision")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["hoja"] == "Cuenta Sergio"
