"""Contract tests for GET /api/compras/{idCompra} — fixtures only, no real DB access.

Covers the explicit `imputacion: null` case (FR-006) and the 404 case.
"""

from __future__ import annotations

import httpx
import pytest

from src.features.compras import repository
from src.main import app

FIXTURE_CABECERA = {
    "idCompra": 12345,
    "fecha": "2026-08-01",
    "proveedor": {"idContacto": 42, "razonSocial": "Rutas Sur Atlantico S.A."},
    "tipoDocumento": "Factura A",
    "numeroDocumento": "0001-00012345",
    "conceptosNoGravados": 0,
    "ingresosBrutos": 150.50,
}

FIXTURE_LINEAS = [
    {
        "idDetalleCompra": 98765,
        "productoServicio": "Flete",
        "cantidad": 1,
        "precioUnitario": 50000,
        "iva": 10500,
        "imputacion": {
            "idRubro": 7,
            "rubro": "Transporte",
            "idCentroCosto": 3,
            "centroCosto": "Campo Norte",
            "idDestino": 12,
            "destino": "Cosecha Norte",
            "idCampania": 4,
            "campania": "Cosecha 2026",
        },
    },
    {
        "idDetalleCompra": 98766,
        "productoServicio": "Servicio sin imputar",
        "cantidad": 1,
        "precioUnitario": 1000,
        "iva": 210,
        "imputacion": None,
    },
]


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_get_compra_detalle_with_null_imputacion(client, monkeypatch):
    monkeypatch.setattr(repository, "get_compra_cabecera", lambda id_compra: FIXTURE_CABECERA)
    monkeypatch.setattr(repository, "get_lineas_compra", lambda id_compra: FIXTURE_LINEAS)
    monkeypatch.setattr(repository, "get_vencimientos_compra", lambda id_compra: [])

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/compras/12345")

    assert response.status_code == 200
    body = response.json()
    assert body["idCompra"] == 12345
    assert len(body["lineas"]) == 2
    assert body["lineas"][0]["imputacion"]["rubro"] == "Transporte"
    # Explicit null, field present, never omitted (FR-006).
    assert "imputacion" in body["lineas"][1]
    assert body["lineas"][1]["imputacion"] is None


@pytest.mark.anyio
async def test_get_compra_detalle_not_found(client, monkeypatch):
    monkeypatch.setattr(repository, "get_compra_cabecera", lambda id_compra: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/compras/999999")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_compra_detalle_conceptos_diferenciados(client, monkeypatch):
    monkeypatch.setattr(repository, "get_compra_cabecera", lambda id_compra: FIXTURE_CABECERA)
    monkeypatch.setattr(repository, "get_lineas_compra", lambda id_compra: FIXTURE_LINEAS)
    monkeypatch.setattr(repository, "get_vencimientos_compra", lambda id_compra: [])

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/compras/12345")

    body = response.json()
    assert body["conceptosNoGravados"] == 0
    assert body["ingresosBrutos"] == 150.50


@pytest.mark.anyio
async def test_get_compra_detalle_rejects_unsupported_write_methods(client):
    """006-carga-compras agregó PUT/DELETE /api/compras/{id} (edición/eliminación) — solo PATCH sigue sin soporte."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        resp = await ac.request("patch", "/api/compras/12345")
        assert resp.status_code in (404, 405)


@pytest.mark.anyio
async def test_put_compra_without_lock_header_is_rejected_not_ignored(client):
    """PUT ahora es una ruta real (edición) — sin X-Lock-Token, debe ser 422, no 404/405."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        resp = await ac.put("/api/compras/12345", json={})
        assert resp.status_code == 422


@pytest.mark.anyio
async def test_delete_compra_without_lock_header_is_rejected_not_ignored(client):
    """DELETE (eliminación, 006) también requiere X-Lock-Token — sin él, 422, no 404/405."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        resp = await ac.delete("/api/compras/12345")
        assert resp.status_code == 422
