"""Contract tests for GET /api/compras/{idCompra}/trazabilidad — fixtures only.

Covers the case with movimientos and the explicit empty case (FR-008, FR-009).
"""

from __future__ import annotations

import httpx
import pytest

from src.features.compras import repository
from src.main import app

FIXTURE_MOVIMIENTOS = [
    {
        "origenTipo": "Compra",
        "idOrigen": 12345,
        "documento": "0001-00012345",
        "fecha": "2026-08-05",
        "importe": 60500.00,
        "tipoImporte": "Deuda",
    }
]


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_get_trazabilidad_con_movimientos(client, monkeypatch):
    monkeypatch.setattr(
        repository, "get_trazabilidad_compra", lambda id_compra: FIXTURE_MOVIMIENTOS
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/compras/12345/trazabilidad")

    assert response.status_code == 200
    body = response.json()
    assert body["idCompra"] == 12345
    assert len(body["movimientos"]) == 1
    assert body["movimientos"][0]["tipoImporte"] == "Deuda"


@pytest.mark.anyio
async def test_get_trazabilidad_sin_movimientos(client, monkeypatch):
    monkeypatch.setattr(repository, "get_trazabilidad_compra", lambda id_compra: [])

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/compras/12345/trazabilidad")

    assert response.status_code == 200
    body = response.json()
    # Explicit empty list, never an error — frontend renders "sin movimientos
    # asociados todavía" for this case (FR-009).
    assert body["movimientos"] == []


@pytest.mark.anyio
async def test_get_trazabilidad_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/compras/12345/trazabilidad")
            assert resp.status_code in (404, 405)
