"""Contract tests for /api/tesoreria/{medio}/movimientos/{id}/traspaso-interno
(024-traspasos-internos-tesoreria) — ver
specs/024-traspasos-internos-tesoreria/contracts/traspasos-internos-api.md.
"""

from __future__ import annotations

import httpx
import pytest

from src.features.traspasos_internos_tesoreria import repository
from src.main import app


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _get(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(url)


async def _post(transport, url, json):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.post(url, json=json)


async def _delete(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.delete(url)


@pytest.mark.anyio
async def test_get_estado_con_candidatas_sugeridas(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "estado_vinculo",
        lambda medio, id_mov: {
            "vinculado": False,
            "contraparte": None,
            "candidatas": [
                {"medio": "galicia", "idMovimiento": 2151, "fecha": "2024-10-10", "descripcion": "Debito Debin", "importe": 17595.82}
            ],
        },
    )

    response = await _get(client, "/api/tesoreria/mercado-libre/movimientos/25/traspaso-interno")
    assert response.status_code == 200
    body = response.json()
    assert not body["vinculado"]
    assert body["candidatas"][0]["idMovimiento"] == 2151


@pytest.mark.anyio
async def test_post_traspaso_interno_aplica_vinculo(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "vincular",
        lambda medioA, idA, medioB, idB, usuario: {
            "vinculado": True,
            "contraparte": {"medio": medioB, "idMovimiento": idB, "fecha": "2024-10-10", "descripcion": "Debito Debin", "importe": 17595.82},
            "candidatas": [],
            "idEvento": 42,
            "usuario": usuario,
            "fecha": "2026-09-29T12:00:00",
        },
    )

    response = await _post(
        client, "/api/tesoreria/mercado-libre/movimientos/25/traspaso-interno", {"medioB": "galicia", "idMovimientoB": 2151}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["vinculado"] and body["idEvento"] == 42


@pytest.mark.anyio
async def test_post_traspaso_interno_tarjetas_responde_400(client):
    """FR-002: Tarjetas no está soportado por este módulo."""
    response = await _post(
        client, "/api/tesoreria/tarjetas/movimientos/1/traspaso-interno", {"medioB": "galicia", "idMovimientoB": 1}
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_post_traspaso_interno_movimiento_ya_resuelto_responde_409(client, monkeypatch):
    def _fake_vincular(medioA, idA, medioB, idB, usuario):
        raise ValueError(f"El movimiento '{medioA}' {idA} ya está resuelto (conciliado) — no se puede vincular de nuevo.")

    monkeypatch.setattr(repository, "vincular", _fake_vincular)

    response = await _post(
        client, "/api/tesoreria/bna/movimientos/1/traspaso-interno", {"medioB": "galicia", "idMovimientoB": 2}
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_delete_traspaso_interno_deshace_vinculo(client, monkeypatch):
    monkeypatch.setattr(repository, "deshacer", lambda medio, id_mov, usuario: {"vinculado": False, "contraparte": None, "candidatas": []})

    response = await _delete(client, "/api/tesoreria/mercado-libre/movimientos/25/traspaso-interno")
    assert response.status_code == 200
    assert not response.json()["vinculado"]


@pytest.mark.anyio
async def test_delete_traspaso_interno_sin_vinculo_responde_404(client, monkeypatch):
    def _fake_deshacer(medio, id_mov, usuario):
        raise ValueError(f"El movimiento '{medio}' {id_mov} no tiene ningún vínculo de traspaso interno activo para deshacer.")

    monkeypatch.setattr(repository, "deshacer", _fake_deshacer)

    response = await _delete(client, "/api/tesoreria/bna/movimientos/1/traspaso-interno")
    assert response.status_code == 404


@pytest.fixture(autouse=True)
def _sin_transacciones_reales_026(monkeypatch):
    # Los tests de negocio simulan escrituras; el contexto común se verifica
    # aparte con conexiones simuladas, no obteniendo locks en producción.
    from contextlib import nullcontext
    from src.db import connection
    monkeypatch.setattr(connection, 'reconciliation_transaction', nullcontext)
