"""Contract tests for GET /api/ventas-hacienda and /api/ventas-hacienda/retenciones.

Retenciones are queried independently — no reliable key back to a venta
(confirmed against real data, see research.md).
"""

from __future__ import annotations

import httpx
import pytest

from src.features.ventas_hacienda import repository
from src.main import app

FIXTURE_VENTA = {
    "idVenta": 1,
    "fecha": "2024-06-01",
    "consignatario": "Consignataria del Sur S.A.",
    "numeroDocumento": "2024-0042",
    "lineas": [
        {
            "idDetalleVenta": 10,
            "comprador": "Frigorífico Norte S.A.",
            "tipoHacienda": "Novillo",
            "cantidad": 45,
            "unidadMedida": "cabezas",
            "pesoTotal": 13620.0,
            "precioUnitarioA": 7.45,
            "precioUnitarioB": 1.5930,
        },
        {
            "idDetalleVenta": 11,
            "comprador": "Otro Frigorífico S.A.",
            "tipoHacienda": "Vaquillona",
            "cantidad": 10,
            "unidadMedida": "cabezas",
            "pesoTotal": 3200.0,
            "precioUnitarioA": 7.30,
            "precioUnitarioB": 1.71,
        },
    ],
}

FIXTURE_RETENCION = {
    "idRetencion": 1,
    "fecha": "2024-06-11",
    "contacto": "Frigorífico Norte S.A.",
    "documento": "Cert. Retencion Ganancias",
    "numeroDocumento": "2023-OP-1760",
    "importe": 555520.0,
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


async def _get(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(url)


@pytest.mark.anyio
async def test_list_ventas_hacienda_lineas_por_comprador(client, monkeypatch):
    def fake_search(consignatario, fecha_desde, fecha_hasta, page, page_size):
        return [FIXTURE_VENTA], 1

    monkeypatch.setattr(repository, "search_ventas_hacienda", fake_search)

    response = await _get(client, "/api/ventas-hacienda")
    assert response.status_code == 200
    body = response.json()
    lineas = body["items"][0]["lineas"]
    assert len(lineas) == 2
    assert lineas[0]["comprador"] != lineas[1]["comprador"]
    assert lineas[0]["precioUnitarioA"] == 7.45
    assert lineas[0]["precioUnitarioB"] == 1.593


@pytest.mark.anyio
async def test_list_ventas_hacienda_empty_result(client, monkeypatch):
    def fake_search(consignatario, fecha_desde, fecha_hasta, page, page_size):
        return [], 0

    monkeypatch.setattr(repository, "search_ventas_hacienda", fake_search)

    response = await _get(client, "/api/ventas-hacienda")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.anyio
async def test_ventas_hacienda_rejects_unsupported_write_methods(client):
    """007-ventas-hacienda-granos agregó POST /api/ventas-hacienda (alta real) —
    solo PUT/DELETE/PATCH sin un `id_venta` en la ruta siguen sin soporte."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("put", "delete", "patch"):
            resp = await ac.request(method, "/api/ventas-hacienda")
            assert resp.status_code in (404, 405)


@pytest.mark.anyio
async def test_post_ventas_hacienda_without_body_is_422(client):
    """POST ahora es una ruta real (alta, 007) — sin body, 422, no 404/405."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        resp = await ac.post("/api/ventas-hacienda", json={})
        assert resp.status_code == 422


@pytest.mark.anyio
async def test_list_retenciones_venta_hacienda_independent(client, monkeypatch):
    def fake_search(contacto, fecha_desde, fecha_hasta, page, page_size):
        assert contacto == "Frigorífico Norte"
        return [FIXTURE_RETENCION], 1

    monkeypatch.setattr(repository, "search_retenciones_venta_hacienda", fake_search)

    response = await _get(client, "/api/ventas-hacienda/retenciones?contacto=Frigorífico Norte")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["idRetencion"] == 1
    # No debe existir ningún campo que sugiera vínculo con una venta específica.
    assert "idVenta" not in body["items"][0]


@pytest.mark.anyio
async def test_retenciones_venta_hacienda_empty_result(client, monkeypatch):
    def fake_search(contacto, fecha_desde, fecha_hasta, page, page_size):
        return [], 0

    monkeypatch.setattr(repository, "search_retenciones_venta_hacienda", fake_search)

    response = await _get(client, "/api/ventas-hacienda/retenciones")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.anyio
async def test_retenciones_venta_hacienda_rejects_write_methods(client):
    """`/retenciones` sigue siendo de solo lectura. PUT/DELETE ahora existen
    como `/api/ventas-hacienda/{id_venta}` (007) — como "retenciones" no es
    un id numérico válido, la ruta responde 422 (path param inválido), no
    404/405; PATCH y POST siguen sin ruta que matchee este path, 404/405."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "patch"):
            resp = await ac.request(method, "/api/ventas-hacienda/retenciones")
            assert resp.status_code in (404, 405)
        for method in ("put", "delete"):
            resp = await ac.request(method, "/api/ventas-hacienda/retenciones")
            assert resp.status_code == 422


@pytest.fixture
def anyio_backend():
    return "asyncio"
