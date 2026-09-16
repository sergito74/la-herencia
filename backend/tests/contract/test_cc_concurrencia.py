"""Contract test: concurrent reads never block one another (FR-015).

Same approach as test_compras_concurrencia.py: fake a blocking pyodbc
round-trip with `time.sleep` and assert N concurrent requests complete in
close to a single delay, not N * delay.
"""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from src.features.cuentas_corrientes import repository
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
async def test_concurrent_movimientos_requests_do_not_serialize(client, monkeypatch):
    def slow_movimientos(id_contacto, fecha_desde, fecha_hasta, page, page_size):
        time.sleep(DELAY_SECONDS)
        return [], 0

    monkeypatch.setattr(repository, "get_movimientos", slow_movimientos)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        start = time.monotonic()
        responses = await asyncio.gather(
            *(
                ac.get(f"/api/cuentas-corrientes/contactos/{id_contacto}/movimientos")
                for id_contacto in range(1, N_REQUESTS + 1)
            )
        )
        elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    assert elapsed < DELAY_SECONDS * (N_REQUESTS / 2)
