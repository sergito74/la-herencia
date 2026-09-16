"""Contract test for GET /api/tesoreria/medios (FR-001)."""

from __future__ import annotations

import httpx
import pytest

from src.main import app


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_list_medios(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tesoreria/medios")

    assert response.status_code == 200
    body = response.json()
    assert set(body["medios"]) == {
        "bna",
        "galicia",
        "efectivo",
        "valores-propios",
        "valores-recibidos",
        "tarjetas",
    }


@pytest.mark.anyio
async def test_medios_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/tesoreria/medios")
            assert resp.status_code in (404, 405)
