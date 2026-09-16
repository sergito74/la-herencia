"""Contract tests for GET /api/arrendamientos."""

from __future__ import annotations

import httpx
import pytest

from src.features.arrendamientos import repository
from src.main import app

FIXTURE_ARRENDAMIENTO = {
    "idAlquiler": 138210671,
    "fecha": "2011-08-09",
    "inicioPeriodo": "2011-09-01",
    "finPeriodo": "2012-08-31",
    "contacto": "Estancia El Rincón",
    "importeTotalContrato": 500000.00,
    "cantidadCuotas": 6,
    "cobros": [
        {
            "idCobroAlquiler": 3001,
            "numeroCuota": 1,
            "importeCuota": 83333.33,
            "estado": "Cobrado",
            "fechaVencimiento": "2011-10-01",
        }
    ],
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


async def _get(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(url)


@pytest.mark.anyio
async def test_list_arrendamientos_by_contacto(client, monkeypatch):
    def fake_search(contacto, page, page_size):
        assert contacto == "Estancia"
        return [FIXTURE_ARRENDAMIENTO], 1

    monkeypatch.setattr(repository, "search_arrendamientos", fake_search)

    response = await _get(client, "/api/arrendamientos?contacto=Estancia")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["cobros"][0]["estado"] == "Cobrado"


@pytest.mark.anyio
async def test_list_arrendamientos_sin_cobros(client, monkeypatch):
    fixture = dict(FIXTURE_ARRENDAMIENTO, cobros=[])

    def fake_search(contacto, page, page_size):
        return [fixture], 1

    monkeypatch.setattr(repository, "search_arrendamientos", fake_search)

    response = await _get(client, "/api/arrendamientos")
    assert response.status_code == 200
    assert response.json()["items"][0]["cobros"] == []


@pytest.mark.anyio
async def test_list_arrendamientos_empty_result(client, monkeypatch):
    def fake_search(contacto, page, page_size):
        return [], 0

    monkeypatch.setattr(repository, "search_arrendamientos", fake_search)

    response = await _get(client, "/api/arrendamientos")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.anyio
async def test_arrendamientos_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/arrendamientos")
            assert resp.status_code in (404, 405)


@pytest.mark.anyio
async def test_actualizar_estado_cuota_marca_cobrada(client, monkeypatch):
    captured = {}

    def fake_set_estado(id_cobro_alquiler, estado):
        captured["id"] = id_cobro_alquiler
        captured["estado"] = estado
        return True

    monkeypatch.setattr(repository, "set_estado_cuota", fake_set_estado)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.patch(
            "/api/arrendamientos/cuotas/3001/estado", json={"estado": "Cobrado"}
        )

    assert response.status_code == 200
    assert response.json() == {"idCobroAlquiler": 3001, "estado": "Cobrado"}
    assert captured == {"id": 3001, "estado": "Cobrado"}


@pytest.mark.anyio
async def test_actualizar_estado_cuota_no_encontrada(client, monkeypatch):
    monkeypatch.setattr(repository, "set_estado_cuota", lambda id_cobro_alquiler, estado: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.patch(
            "/api/arrendamientos/cuotas/999999/estado", json={"estado": "Cobrado"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_actualizar_estado_cuota_rechaza_valor_invalido(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.patch(
            "/api/arrendamientos/cuotas/3001/estado", json={"estado": "Vencido"}
        )

    assert response.status_code == 422


@pytest.fixture
def anyio_backend():
    return "asyncio"
