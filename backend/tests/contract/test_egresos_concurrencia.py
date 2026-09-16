"""Contract test: concurrent reads never block one another (FR-011).

Same approach as test_cc_concurrencia.py / test_compras_concurrencia.py:
fake a blocking pyodbc round-trip with `time.sleep` and assert N
concurrent requests complete in close to a single delay, not N * delay,
for each of the 4 new endpoints from specs/005-egresos-y-ventas-menores.
"""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from src.features.arrendamientos import repository as arrendamientos_repository
from src.features.impuestos import repository as impuestos_repository
from src.features.remuneraciones import repository as remuneraciones_repository
from src.features.ventas_hacienda import repository as ventas_hacienda_repository
from src.main import app

DELAY_SECONDS = 0.2
N_REQUESTS = 5


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_concurrent_impuestos_requests_do_not_serialize(client, monkeypatch):
    def slow_search(organismo, fecha_desde, fecha_hasta, page, page_size):
        time.sleep(DELAY_SECONDS)
        return [], 0

    monkeypatch.setattr(impuestos_repository, "search_impuestos", slow_search)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        start = time.monotonic()
        responses = await asyncio.gather(*(ac.get("/api/impuestos") for _ in range(N_REQUESTS)))
        elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    assert elapsed < DELAY_SECONDS * (N_REQUESTS / 2)


@pytest.mark.anyio
async def test_concurrent_remuneraciones_requests_do_not_serialize(client, monkeypatch):
    def slow_search(empleado, periodo_liquidado, page, page_size):
        time.sleep(DELAY_SECONDS)
        return [], 0

    monkeypatch.setattr(remuneraciones_repository, "search_remuneraciones", slow_search)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        start = time.monotonic()
        responses = await asyncio.gather(
            *(ac.get("/api/remuneraciones") for _ in range(N_REQUESTS))
        )
        elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    assert elapsed < DELAY_SECONDS * (N_REQUESTS / 2)


@pytest.mark.anyio
async def test_concurrent_arrendamientos_requests_do_not_serialize(client, monkeypatch):
    def slow_search(contacto, page, page_size):
        time.sleep(DELAY_SECONDS)
        return [], 0

    monkeypatch.setattr(arrendamientos_repository, "search_arrendamientos", slow_search)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        start = time.monotonic()
        responses = await asyncio.gather(
            *(ac.get("/api/arrendamientos") for _ in range(N_REQUESTS))
        )
        elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    assert elapsed < DELAY_SECONDS * (N_REQUESTS / 2)


@pytest.mark.anyio
async def test_concurrent_ventas_hacienda_requests_do_not_serialize(client, monkeypatch):
    def slow_search(consignatario, fecha_desde, fecha_hasta, page, page_size):
        time.sleep(DELAY_SECONDS)
        return [], 0

    monkeypatch.setattr(ventas_hacienda_repository, "search_ventas_hacienda", slow_search)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        start = time.monotonic()
        responses = await asyncio.gather(
            *(ac.get("/api/ventas-hacienda") for _ in range(N_REQUESTS))
        )
        elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    assert elapsed < DELAY_SECONDS * (N_REQUESTS / 2)
