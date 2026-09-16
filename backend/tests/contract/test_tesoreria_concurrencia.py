"""Concurrent reads across tesoreria medios never block one another (FR-014).

Same rationale as test_compras_concurrencia.py: fakes a blocking pyodbc
round-trip with `time.sleep` and asserts wall-clock time proves the thread
pool is actually parallelizing requests, not serializing them.
"""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from src.features.tesoreria import repository
from src.main import app

DELAY_SECONDS = 0.2
MEDIOS = ("bna", "galicia", "efectivo", "valores-propios", "valores-recibidos", "tarjetas")


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_concurrent_movimientos_across_medios_do_not_serialize(client, monkeypatch):
    def slow_get_movimientos(medio, fecha_desde, fecha_hasta, page, page_size):
        time.sleep(DELAY_SECONDS)
        return [], 0

    monkeypatch.setattr(repository, "get_movimientos", slow_get_movimientos)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        start = time.monotonic()
        responses = await asyncio.gather(
            *(ac.get(f"/api/tesoreria/{medio}/movimientos") for medio in MEDIOS)
        )
        elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    assert elapsed < DELAY_SECONDS * (len(MEDIOS) / 2)
