"""Contract tests for /api/tarjetas-cuotas (008-tarjetas, Historia 3).

Solo lectura desde 2026-09-19 (feedback del usuario, punto 5: la
estructura `[Tarjetas de Credito]`/`[Cuotas Tarjetas de Credito]` es
obsoleta, sin uso real desde diciembre de 2015 — ver repository.py).
"""

from __future__ import annotations

import httpx
import pytest

from src.features.tarjetas_cuotas import repository
from src.main import app


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_list_compras_sin_filtro_vacio(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-cuotas")

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "pageSize": 50, "total": 0}


@pytest.mark.anyio
async def test_list_compras_con_filtro_devuelve_resultados(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "search_compras",
        lambda *a, **kw: (
            [
                {
                    "idPagoTarjeta": 1,
                    "idContacto": 245,
                    "contacto": "Juan Perez",
                    "fecha": "2013-07-17",
                    "nroComprobante": 110,
                    "cantidadCuotas": 12,
                    "cuotasCobradas": 12,
                    "cuotasPendientes": 0,
                }
            ],
            1,
        ),
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-cuotas?idContacto=245")

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.anyio
async def test_get_detalle_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_detalle", lambda id_pago_tarjeta: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-cuotas/999999")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_detalle_con_cuotas(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_detalle",
        lambda id_pago_tarjeta: {
            "idPagoTarjeta": 1,
            "idContacto": 245,
            "contacto": "Juan Perez",
            "fecha": "2013-07-17",
            "nroComprobante": 110,
            "cantidadCuotas": 2,
        },
    )
    monkeypatch.setattr(
        repository,
        "get_cuotas",
        lambda id_pago_tarjeta: [
            {"idCuota": 1, "numeroCuota": 1, "fechaVencimiento": "2013-08-17", "importe": 100.0, "cobrado": True},
            {"idCuota": 2, "numeroCuota": 2, "fechaVencimiento": "2013-09-17", "importe": 100.0, "cobrado": True},
        ],
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-cuotas/1")

    assert response.status_code == 200
    body = response.json()
    assert len(body["cuotas"]) == 2
    assert body["importeTotal"] == 200.0


@pytest.mark.anyio
async def test_no_expone_endpoints_de_escritura(client):
    """FR del feedback 2026-09-19: la estructura es obsoleta, no se
    permite alta/edición/eliminación/lock/marcar-cobrada."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        post = await ac.post("/api/tarjetas-cuotas", json={"idContacto": 1, "fecha": "2026-01-01", "nroComprobante": 1, "importeTotal": 100, "cantidadCuotas": 1})
        put = await ac.put("/api/tarjetas-cuotas/1", json={})
        delete = await ac.delete("/api/tarjetas-cuotas/1")
        patch = await ac.patch("/api/tarjetas-cuotas/1/cuotas/1", json={"cobrado": True})

    assert post.status_code == 405
    assert put.status_code == 405
    assert delete.status_code == 405
    assert patch.status_code == 404
