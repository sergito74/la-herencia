"""Contract tests for GET /api/compras — fixtures only, no real DB access."""

from __future__ import annotations

import httpx
import pytest

from src.features.compras import repository
from src.main import app

FIXTURE_COMPRAS = [
    {
        "idCompra": 12345,
        "fecha": "2026-08-01",
        "proveedor": {"idContacto": 42, "razonSocial": "Rutas Sur Atlantico S.A."},
        "tipoDocumento": "Factura A",
        "numeroDocumento": "0001-00012345",
    },
    {
        "idCompra": 12346,
        "fecha": "2026-07-15",
        "proveedor": {"idContacto": 43, "razonSocial": "Otro Proveedor S.R.L."},
        "tipoDocumento": "Factura B",
        "numeroDocumento": "0002-00000456",
    },
]


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


async def _get(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(url)


@pytest.mark.anyio
async def test_list_compras_by_proveedor(client, monkeypatch):
    def fake_search(proveedor, numero_documento, fecha_desde, fecha_hasta, id_centro_costo, id_rubro, page, page_size, id_contacto=None):
        assert proveedor == "Rutas Sur"
        return [FIXTURE_COMPRAS[0]], 1

    monkeypatch.setattr(repository, "search_compras", fake_search)

    response = await _get(client, "/api/compras?proveedor=Rutas Sur")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["proveedor"]["razonSocial"] == "Rutas Sur Atlantico S.A."
    assert body["page"] == 1
    assert body["pageSize"] == 50


@pytest.mark.anyio
async def test_list_compras_empty_result(client, monkeypatch):
    def fake_search(proveedor, numero_documento, fecha_desde, fecha_hasta, id_centro_costo, id_rubro, page, page_size, id_contacto=None):
        return [], 0

    monkeypatch.setattr(repository, "search_compras", fake_search)

    response = await _get(client, "/api/compras?proveedor=NoExiste")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.anyio
async def test_list_compras_pagination_defaults(client, monkeypatch):
    captured = {}

    def fake_search(proveedor, numero_documento, fecha_desde, fecha_hasta, id_centro_costo, id_rubro, page, page_size, id_contacto=None):
        captured["page"] = page
        captured["page_size"] = page_size
        return FIXTURE_COMPRAS, len(FIXTURE_COMPRAS)

    monkeypatch.setattr(repository, "search_compras", fake_search)

    response = await _get(client, "/api/compras")
    assert response.status_code == 200
    assert captured["page"] == 1
    assert captured["page_size"] == 50
    assert response.json()["total"] == 2


@pytest.mark.anyio
async def test_list_compras_page_size_rejected_over_max(client, monkeypatch):
    # FastAPI query validation (le=200) rejects out-of-range pageSize outright,
    # before it ever reaches normalize_pagination.
    def fake_search(proveedor, numero_documento, fecha_desde, fecha_hasta, id_centro_costo, id_rubro, page, page_size, id_contacto=None):
        return [], 0

    monkeypatch.setattr(repository, "search_compras", fake_search)

    response = await _get(client, "/api/compras?pageSize=9999")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_compras_page_size_at_max_allowed(client, monkeypatch):
    captured = {}

    def fake_search(proveedor, numero_documento, fecha_desde, fecha_hasta, id_centro_costo, id_rubro, page, page_size, id_contacto=None):
        captured["page_size"] = page_size
        return [], 0

    monkeypatch.setattr(repository, "search_compras", fake_search)

    response = await _get(client, "/api/compras?pageSize=200")
    assert response.status_code == 200
    assert captured["page_size"] == 200


@pytest.mark.anyio
async def test_list_compras_rejects_unsupported_write_methods(client):
    """006-carga-compras agregó POST /api/compras (alta) — solo DELETE/PATCH siguen sin soporte aquí."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("delete", "patch"):
            resp = await ac.request(method, "/api/compras")
            assert resp.status_code in (404, 405)


@pytest.mark.anyio
async def test_post_compras_without_body_is_rejected_not_ignored(client):
    """POST ahora es una ruta real (alta) — sin body válido, debe ser 422, no 404/405."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        resp = await ac.post("/api/compras")
        assert resp.status_code == 422


@pytest.mark.anyio
async def test_list_compras_filters_by_centro_costo_and_rubro(client, monkeypatch):
    captured = {}

    def fake_search(proveedor, numero_documento, fecha_desde, fecha_hasta, id_centro_costo, id_rubro, page, page_size, id_contacto=None):
        captured["id_centro_costo"] = id_centro_costo
        captured["id_rubro"] = id_rubro
        return [], 0

    monkeypatch.setattr(repository, "search_compras", fake_search)

    response = await _get(client, "/api/compras?idCentroCosto=5&idRubro=7")
    assert response.status_code == 200
    assert captured["id_centro_costo"] == 5
    assert captured["id_rubro"] == 7


@pytest.mark.anyio
async def test_get_filtros_compras(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_filtros",
        lambda: {
            "centrosCosto": [{"idCentroCosto": 1, "centroCosto": "Administración"}],
            "rubros": [{"idRubro": 1, "rubro": "Insumos"}],
        },
    )

    response = await _get(client, "/api/compras/filtros")
    assert response.status_code == 200
    body = response.json()
    assert body["centrosCosto"][0]["centroCosto"] == "Administración"
    assert body["rubros"][0]["rubro"] == "Insumos"


@pytest.fixture
def anyio_backend():
    return "asyncio"
