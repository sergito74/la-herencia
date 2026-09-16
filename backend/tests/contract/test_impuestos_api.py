"""Contract tests for GET /api/impuestos and /api/impuestos/retenciones."""

from __future__ import annotations

import httpx
import pytest

from src.features.impuestos import repository
from src.main import app

FIXTURE_IMPUESTO = {
    "idImpuesto": 14,
    "fecha": "2011-05-16",
    "tipoImpuesto": "Ingresos Brutos",
    "periodoLiquidado": "2011-04",
    "numeroDocumento": "0001-00000123",
    "importe": 1500.00,
    "organismo": "ARBA",
}

FIXTURE_RETENCION = {
    "idRetencion": 1,
    "numeroCertificado": "0000-2017-000001",
    "fecha": "2017-09-19",
    "contacto": "Proveedor X",
    "importe": 435.94,
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


async def _get(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(url)


@pytest.mark.anyio
async def test_list_impuestos_by_organismo(client, monkeypatch):
    def fake_search(organismo, fecha_desde, fecha_hasta, page, page_size):
        assert organismo == "ARBA"
        return [FIXTURE_IMPUESTO], 1

    monkeypatch.setattr(repository, "search_impuestos", fake_search)

    response = await _get(client, "/api/impuestos?organismo=ARBA")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["organismo"] == "ARBA"


@pytest.mark.anyio
async def test_list_impuestos_empty_result(client, monkeypatch):
    def fake_search(organismo, fecha_desde, fecha_hasta, page, page_size):
        return [], 0

    monkeypatch.setattr(repository, "search_impuestos", fake_search)

    response = await _get(client, "/api/impuestos?organismo=NoExiste")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.anyio
async def test_list_impuestos_date_filters_forwarded(client, monkeypatch):
    captured = {}

    def fake_search(organismo, fecha_desde, fecha_hasta, page, page_size):
        captured["fecha_desde"] = fecha_desde
        captured["fecha_hasta"] = fecha_hasta
        return [], 0

    monkeypatch.setattr(repository, "search_impuestos", fake_search)

    response = await _get(client, "/api/impuestos?fechaDesde=2011-01-01&fechaHasta=2011-12-31")
    assert response.status_code == 200
    assert str(captured["fecha_desde"]) == "2011-01-01"
    assert str(captured["fecha_hasta"]) == "2011-12-31"


@pytest.mark.anyio
async def test_impuestos_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/impuestos")
            assert resp.status_code in (404, 405)


@pytest.mark.anyio
async def test_list_retenciones_by_contacto(client, monkeypatch):
    def fake_search(contacto, fecha_desde, fecha_hasta, page, page_size):
        assert contacto == "Proveedor X"
        return [FIXTURE_RETENCION], 1

    monkeypatch.setattr(repository, "search_retenciones", fake_search)

    response = await _get(client, "/api/impuestos/retenciones?contacto=Proveedor X")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["numeroCertificado"] == "0000-2017-000001"


@pytest.mark.anyio
async def test_list_retenciones_empty_result(client, monkeypatch):
    def fake_search(contacto, fecha_desde, fecha_hasta, page, page_size):
        return [], 0

    monkeypatch.setattr(repository, "search_retenciones", fake_search)

    response = await _get(client, "/api/impuestos/retenciones")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.anyio
async def test_retenciones_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/impuestos/retenciones")
            assert resp.status_code in (404, 405)


@pytest.fixture
def anyio_backend():
    return "asyncio"
