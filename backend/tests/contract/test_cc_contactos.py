"""Contract tests for GET /api/cuentas-corrientes/contactos — fixtures only."""

from __future__ import annotations

import httpx
import pytest

from src.features.cuentas_corrientes import repository
from src.main import app

FIXTURE_CONTACTOS = [
    {"idContacto": 42, "razonSocial": "Rutas Sur Atlantico S.A.", "tipoContacto": "Proveedor"},
    {"idContacto": 43, "razonSocial": "Otro Proveedor S.R.L.", "tipoContacto": "Proveedor"},
]


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


async def _get(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(url)


@pytest.mark.anyio
async def test_search_contactos_by_razon_social(client, monkeypatch):
    def fake_search(q, tipo_contacto):
        assert q == "Rutas Sur"
        assert tipo_contacto is None
        return [FIXTURE_CONTACTOS[0]]

    monkeypatch.setattr(repository, "search_contactos", fake_search)

    response = await _get(client, "/api/cuentas-corrientes/contactos?q=Rutas Sur")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["razonSocial"] == "Rutas Sur Atlantico S.A."


@pytest.mark.anyio
async def test_search_contactos_by_tipo(client, monkeypatch):
    def fake_search(q, tipo_contacto):
        assert tipo_contacto == "Proveedor"
        return FIXTURE_CONTACTOS

    monkeypatch.setattr(repository, "search_contactos", fake_search)

    response = await _get(client, "/api/cuentas-corrientes/contactos?tipoContacto=Proveedor")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


@pytest.mark.anyio
async def test_search_contactos_tipo_multiple_sin_duplicados(client, monkeypatch):
    """FR-014: contactos tipo 'Multiple' no deben aparecer duplicados."""

    def fake_search(q, tipo_contacto):
        assert tipo_contacto == "Multiple"
        return [{"idContacto": 7, "razonSocial": "Contacto Multiple", "tipoContacto": "Multiple"}]

    monkeypatch.setattr(repository, "search_contactos", fake_search)

    response = await _get(client, "/api/cuentas-corrientes/contactos?tipoContacto=Multiple")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["idContacto"] == 7


@pytest.mark.anyio
async def test_search_contactos_empty_result(client, monkeypatch):
    def fake_search(q, tipo_contacto):
        return []

    monkeypatch.setattr(repository, "search_contactos", fake_search)

    response = await _get(client, "/api/cuentas-corrientes/contactos?q=NoExiste")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.anyio
async def test_contactos_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/cuentas-corrientes/contactos")
            assert resp.status_code in (404, 405)


@pytest.fixture
def anyio_backend():
    return "asyncio"
