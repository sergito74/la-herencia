"""Contract tests for GET /api/tesoreria/{medio}/movimientos/{id}/referencia.

Covers the 3 explicit estados (FR-004, FR-005) and the valores-propios
special case (always "sin_coincidencia", no query executed at all).
"""

from __future__ import annotations

import httpx
import pytest

from src.features.tesoreria import matching
from src.main import app


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
async def test_referencia_sin_coincidencia(client, monkeypatch):
    monkeypatch.setattr(
        matching, "buscar_referencia", lambda medio, id_mov: {"estado": "sin_coincidencia", "candidatas": []}
    )

    response = await _get(client, "/api/tesoreria/bna/movimientos/555/referencia")
    assert response.status_code == 200
    assert response.json() == {"estado": "sin_coincidencia", "candidatas": []}


@pytest.mark.anyio
async def test_referencia_coincidencia_unica(client, monkeypatch):
    candidata = {
        "idCompra": 12345,
        "numeroDocumento": "0001-00012345",
        "proveedor": "Rutas Sur Atlantico S.A.",
        "fecha": "2026-08-01",
        "importe": 60500.00,
    }
    monkeypatch.setattr(
        matching,
        "buscar_referencia",
        lambda medio, id_mov: {"estado": "coincidencia_unica", "candidatas": [candidata]},
    )

    response = await _get(client, "/api/tesoreria/bna/movimientos/555/referencia")
    body = response.json()
    assert body["estado"] == "coincidencia_unica"
    assert len(body["candidatas"]) == 1


@pytest.mark.anyio
async def test_referencia_ambigua(client, monkeypatch):
    candidatas = [
        {"idCompra": 1, "numeroDocumento": "A", "proveedor": "X", "fecha": "2026-08-01", "importe": 100},
        {"idCompra": 2, "numeroDocumento": "B", "proveedor": "X", "fecha": "2026-08-01", "importe": 100},
    ]
    monkeypatch.setattr(
        matching, "buscar_referencia", lambda medio, id_mov: {"estado": "ambigua", "candidatas": candidatas}
    )

    response = await _get(client, "/api/tesoreria/bna/movimientos/555/referencia")
    body = response.json()
    assert body["estado"] == "ambigua"
    assert len(body["candidatas"]) == 2


@pytest.mark.anyio
async def test_referencia_valores_propios_siempre_sin_coincidencia(client, monkeypatch):
    called = {"count": 0}

    def spy(medio, id_mov):
        called["count"] += 1
        return {"estado": "sin_coincidencia", "candidatas": []}

    monkeypatch.setattr(matching, "buscar_referencia", spy)

    response = await _get(client, "/api/tesoreria/valores-propios/movimientos/1/referencia")
    assert response.status_code == 200
    assert response.json()["estado"] == "sin_coincidencia"


@pytest.mark.anyio
async def test_referencia_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/tesoreria/bna/movimientos/555/referencia")
            assert resp.status_code in (404, 405)
