"""Contract tests for GET /api/tesoreria/{medio}/movimientos (FR-002/003/012/013)."""

from __future__ import annotations

import httpx
import pytest

from src.features.tesoreria import repository
from src.main import app

FIXTURE_BNA = [
    {
        "idMovimientoBNA": 555,
        "fechaHora": "2026-08-05T10:15:00",
        "concepto": "Transferencia",
        "importe": -60500.00,
        "idContacto": 42,
        "contacto": "Rutas Sur Atlantico S.A.",
    }
]

FIXTURE_GALICIA = [
    {
        "idMovimiento": 900,
        "fecha": "2026-08-06",
        "descripcion": "Trf Inmed Proveed",
        "debitos": 46044.04,
        "creditos": 0,
        "saldo": 774943.40,
        "idContacto": 42,
        "contacto": "Rutas Sur Atlantico S.A.",
    }
]


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _get(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(url)


@pytest.mark.anyio
async def test_list_movimientos_bna(client, monkeypatch):
    monkeypatch.setattr(
        repository, "get_movimientos", lambda *a, **k: (FIXTURE_BNA, 1)
    )

    response = await _get(client, "/api/tesoreria/bna/movimientos")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["concepto"] == "Transferencia"


@pytest.mark.anyio
async def test_list_movimientos_galicia_has_saldo_field(client, monkeypatch):
    monkeypatch.setattr(
        repository, "get_movimientos", lambda *a, **k: (FIXTURE_GALICIA, 1)
    )

    response = await _get(client, "/api/tesoreria/galicia/movimientos")
    assert response.status_code == 200
    body = response.json()
    # Saldo is Galicia-specific, not forced onto BNA's shape (FR-002).
    assert body["items"][0]["saldo"] == 774943.40


@pytest.mark.anyio
async def test_list_movimientos_empty_result(client, monkeypatch):
    monkeypatch.setattr(repository, "get_movimientos", lambda *a, **k: ([], 0))

    response = await _get(client, "/api/tesoreria/bna/movimientos")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.anyio
async def test_list_movimientos_unknown_medio(client):
    response = await _get(client, "/api/tesoreria/inexistente/movimientos")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_movimientos_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/tesoreria/bna/movimientos")
            assert resp.status_code in (404, 405)
