"""Contract tests for /api/tarjetas (008-tarjetas, Historias 2 y 4)."""

from __future__ import annotations

import httpx
import pytest

from src.features.tarjetas import repository
from src.main import app


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --- US4: catálogo ---


@pytest.mark.anyio
async def test_list_tarjetas(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_tarjetas",
        lambda solo_activas=False: [
            {"idTarjeta": 1, "nombre": "AgroNacion", "banco": "Banco Nacion", "activa": True},
            {"idTarjeta": 2, "nombre": "Visa Galicia", "banco": "Banco Galicia", "activa": True},
        ],
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas")

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.anyio
async def test_list_tarjetas_solo_activas(client, monkeypatch):
    captured = {}

    def fake_get_tarjetas(solo_activas=False):
        captured["solo_activas"] = solo_activas
        return []

    monkeypatch.setattr(repository, "get_tarjetas", fake_get_tarjetas)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        await ac.get("/api/tarjetas?soloActivas=true")

    assert captured["solo_activas"] is True


# --- US2: cuenta corriente ---


@pytest.mark.anyio
async def test_movimientos_tarjeta_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_tarjeta", lambda id_tarjeta: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas/999999/movimientos")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_movimientos_tarjeta_un_movimiento_por_resumen_saldo_acumulado(client, monkeypatch):
    monkeypatch.setattr(repository, "get_tarjeta", lambda id_tarjeta: {"idTarjeta": 3, "nombre": "Visa Galicia"})
    monkeypatch.setattr(
        repository,
        "get_movimientos",
        lambda id_tarjeta: [
            {"idResumen": 1, "fecha": "2026-05-10", "codigo": "A", "deuda": 1000.0, "credito": 0.0, "saldoAcumulado": 1000.0},
            {"idResumen": 2, "fecha": "2026-06-10", "codigo": "B", "deuda": 500.0, "credito": 0.0, "saldoAcumulado": 1500.0},
        ],
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas/3/movimientos")

    assert response.status_code == 200
    body = response.json()
    assert body["tarjeta"] == "Visa Galicia"
    assert len(body["movimientos"]) == 2
    assert body["movimientos"][-1]["saldoAcumulado"] == 1500.0


@pytest.mark.anyio
async def test_movimientos_tarjeta_no_incluye_cuotas(client, monkeypatch):
    """Decisión de "solo resúmenes" (research.md §3) — el repository real
    (get_movimientos) no consulta tarjetas_cuotas en absoluto; este test
    documenta el contrato de respuesta, no reimplementa la lógica interna."""
    monkeypatch.setattr(repository, "get_tarjeta", lambda id_tarjeta: {"idTarjeta": 3, "nombre": "Visa Galicia"})
    monkeypatch.setattr(repository, "get_movimientos", lambda id_tarjeta: [])

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas/3/movimientos")

    assert response.status_code == 200
    assert response.json()["movimientos"] == []
