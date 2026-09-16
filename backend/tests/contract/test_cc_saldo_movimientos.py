"""Contract tests for GET .../saldo and .../movimientos — fixtures only."""

from __future__ import annotations

import httpx
import pytest

from src.features.cuentas_corrientes import repository
from src.main import app

FIXTURE_MOVIMIENTO = {
    "fecha": "2026-08-05",
    "documento": "Factura A",
    "numeroDocumento": "0001-00012345",
    "deuda": 60500.00,
    "credito": 0,
    "origenTipo": "Compras",
    "idOrigen": 12345,
    "saldoParcial": -60500.00,
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


async def _get(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(url)


@pytest.mark.anyio
async def test_get_saldo(client, monkeypatch):
    def fake_saldo(id_contacto):
        assert id_contacto == 42
        return {"idContacto": 42, "saldoParcial": -60500.00}

    monkeypatch.setattr(repository, "get_saldo", fake_saldo)

    response = await _get(client, "/api/cuentas-corrientes/contactos/42/saldo")
    assert response.status_code == 200
    assert response.json() == {"idContacto": 42, "saldoParcial": -60500.00}


@pytest.mark.anyio
async def test_get_saldo_not_found(client, monkeypatch):
    def fake_saldo(id_contacto):
        return None

    monkeypatch.setattr(repository, "get_saldo", fake_saldo)

    response = await _get(client, "/api/cuentas-corrientes/contactos/999/saldo")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_movimientos(client, monkeypatch):
    def fake_movimientos(id_contacto, fecha_desde, fecha_hasta, page, page_size):
        assert id_contacto == 42
        return [FIXTURE_MOVIMIENTO], 1

    monkeypatch.setattr(repository, "get_movimientos", fake_movimientos)

    response = await _get(client, "/api/cuentas-corrientes/contactos/42/movimientos")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["deuda"] == 60500.00
    # FR-008: origen nunca omitido, siempre uno de los 4 tipos definidos.
    assert body["items"][0]["origen"]["tipo"] in (
        "compra",
        "tesoreria",
        "fuera_de_alcance",
        "no_disponible",
    )


@pytest.mark.anyio
async def test_list_movimientos_empty_result(client, monkeypatch):
    def fake_movimientos(id_contacto, fecha_desde, fecha_hasta, page, page_size):
        return [], 0

    monkeypatch.setattr(repository, "get_movimientos", fake_movimientos)

    response = await _get(client, "/api/cuentas-corrientes/contactos/42/movimientos")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.anyio
async def test_list_movimientos_date_filters_forwarded(client, monkeypatch):
    captured = {}

    def fake_movimientos(id_contacto, fecha_desde, fecha_hasta, page, page_size):
        captured["fecha_desde"] = fecha_desde
        captured["fecha_hasta"] = fecha_hasta
        return [], 0

    monkeypatch.setattr(repository, "get_movimientos", fake_movimientos)

    response = await _get(
        client,
        "/api/cuentas-corrientes/contactos/42/movimientos"
        "?fechaDesde=2026-08-01&fechaHasta=2026-08-31",
    )
    assert response.status_code == 200
    assert str(captured["fecha_desde"]) == "2026-08-01"
    assert str(captured["fecha_hasta"]) == "2026-08-31"


@pytest.mark.anyio
async def test_movimientos_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(
                method, "/api/cuentas-corrientes/contactos/42/movimientos"
            )
            assert resp.status_code in (404, 405)


@pytest.fixture
def anyio_backend():
    return "asyncio"
