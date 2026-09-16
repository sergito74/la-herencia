"""Contract tests for GET /api/remuneraciones and /api/remuneraciones/pagos.

`Pagos Remuneraciones` is queried independently (no employee filter, no
nested list under a liquidación) — confirmed against real data that
`IdEmpleado` is not a FK into `Contactos` (see research.md).
"""

from __future__ import annotations

import httpx
import pytest

from src.features.remuneraciones import repository
from src.main import app

FIXTURE_REMUNERACION = {
    "idSalario": 1829633151,
    "empleado": "Juan Pérez",
    "fechaPago": "2019-11-30",
    "periodoLiquidado": "2019-11",
    "importe": 85000.00,
}

FIXTURE_PAGO = {
    "idPago": 501,
    "fecha": "2019-12-02",
    "cuenta": "BNA",
    "caja": None,
    "importe": 85000.00,
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


async def _get(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(url)


@pytest.mark.anyio
async def test_list_remuneraciones_by_empleado(client, monkeypatch):
    def fake_search(empleado, periodo_liquidado, page, page_size):
        assert empleado == "Juan"
        return [FIXTURE_REMUNERACION], 1

    monkeypatch.setattr(repository, "search_remuneraciones", fake_search)

    response = await _get(client, "/api/remuneraciones?empleado=Juan")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["empleado"] == "Juan Pérez"
    assert "pagos" not in body["items"][0]


@pytest.mark.anyio
async def test_list_remuneraciones_sin_empleado_identificado(client, monkeypatch):
    fixture = dict(FIXTURE_REMUNERACION, empleado=None)

    def fake_search(empleado, periodo_liquidado, page, page_size):
        return [fixture], 1

    monkeypatch.setattr(repository, "search_remuneraciones", fake_search)

    response = await _get(client, "/api/remuneraciones")
    assert response.status_code == 200
    assert response.json()["items"][0]["empleado"] is None


@pytest.mark.anyio
async def test_list_remuneraciones_empty_result(client, monkeypatch):
    def fake_search(empleado, periodo_liquidado, page, page_size):
        return [], 0

    monkeypatch.setattr(repository, "search_remuneraciones", fake_search)

    response = await _get(client, "/api/remuneraciones")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.anyio
async def test_remuneraciones_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/remuneraciones")
            assert resp.status_code in (404, 405)


@pytest.mark.anyio
async def test_list_pagos_remuneracion_independent_listing(client, monkeypatch):
    def fake_search(page, page_size):
        return [FIXTURE_PAGO], 1

    monkeypatch.setattr(repository, "search_pagos_remuneracion", fake_search)

    response = await _get(client, "/api/remuneraciones/pagos")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["idPago"] == 501
    # No debe existir ningún campo de empleado/contacto: no hay FK confiable.
    assert "empleado" not in body["items"][0]
    assert "idEmpleado" not in body["items"][0]


@pytest.mark.anyio
async def test_pagos_remuneracion_empty_result(client, monkeypatch):
    def fake_search(page, page_size):
        return [], 0

    monkeypatch.setattr(repository, "search_pagos_remuneracion", fake_search)

    response = await _get(client, "/api/remuneraciones/pagos")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.anyio
async def test_pagos_remuneracion_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/remuneraciones/pagos")
            assert resp.status_code in (404, 405)


@pytest.fixture
def anyio_backend():
    return "asyncio"
