"""Contract test: concurrent reads never block one another (FR-014).

Each repository call is faked with a blocking `time.sleep`, simulating a
real pyodbc round-trip. If the endpoints awaited these calls directly
instead of offloading them to a thread pool, N concurrent requests would
take N * delay to complete instead of ~delay. This test asserts the
wall-clock time stays close to a single delay, proving requests are served
in parallel.
"""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from src.features.compras import repository
from src.main import app

DELAY_SECONDS = 0.2
N_REQUESTS = 5

FIXTURE_CABECERA = {
    "idCompra": 12345,
    "fecha": "2026-08-01",
    "proveedor": {"idContacto": 42, "razonSocial": "Rutas Sur Atlantico S.A."},
    "tipoDocumento": "Factura A",
    "numeroDocumento": "0001-00012345",
    "conceptosNoGravados": 0,
    "ingresosBrutos": 0,
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_concurrent_list_requests_do_not_serialize(client, monkeypatch):
    def slow_search(proveedor, numero_documento, fecha_desde, fecha_hasta, id_centro_costo, id_rubro, page, page_size, *args, **kwargs):
        time.sleep(DELAY_SECONDS)
        return [], 0

    monkeypatch.setattr(repository, "search_compras", slow_search)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        start = time.monotonic()
        responses = await asyncio.gather(
            *(ac.get("/api/compras") for _ in range(N_REQUESTS))
        )
        elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    # Serialized execution would take N_REQUESTS * DELAY_SECONDS; parallel
    # execution via the thread pool should stay well under that.
    assert elapsed < DELAY_SECONDS * (N_REQUESTS / 2)


@pytest.mark.anyio
async def test_concurrent_detail_requests_do_not_serialize(client, monkeypatch):
    def slow_cabecera(id_compra):
        time.sleep(DELAY_SECONDS)
        return FIXTURE_CABECERA

    def slow_lineas(id_compra):
        return []

    monkeypatch.setattr(repository, "get_compra_cabecera", slow_cabecera)
    monkeypatch.setattr(repository, "get_lineas_compra", slow_lineas)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        start = time.monotonic()
        responses = await asyncio.gather(
            *(ac.get("/api/compras/12345") for _ in range(N_REQUESTS))
        )
        elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    assert elapsed < DELAY_SECONDS * (N_REQUESTS / 2)
