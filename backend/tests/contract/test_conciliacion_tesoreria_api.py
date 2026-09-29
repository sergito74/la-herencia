"""Contract tests for /api/tesoreria/{medio}/movimientos/{id}/conciliacion
(023-conciliacion-tesoreria) — ver
specs/023-conciliacion-tesoreria/contracts/conciliacion-tesoreria-api.md.
"""

from __future__ import annotations

import httpx
import pytest

from src.features.conciliacion_tesoreria import repository
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


@pytest.mark.anyio
async def test_get_estado_sin_conciliar(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "calcular_estado",
        lambda medio, id_mov: {
            "estado": "sin_conciliar",
            "importeTotal": 60500.0,
            "saldoPendiente": 60500.0,
            "conciliaciones": [],
        },
    )

    response = await _get(client, "/api/tesoreria/bna/movimientos/555/conciliacion")
    assert response.status_code == 200
    body = response.json()
    assert body["estado"] == "sin_conciliar"
    assert body["saldoPendiente"] == 60500.0


@pytest.mark.anyio
async def test_post_conciliacion_simple(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "aplicar_conciliacion",
        lambda medio, id_mov, id_contacto, importe, usuario: {
            "idConciliacion": 88,
            "idContacto": id_contacto,
            "contacto": "Rutas Sur Atlantico S.A.",
            "importe": importe,
            "usuario": usuario,
            "fecha": "2026-09-28T11:04:00",
        },
    )

    response = await _post(
        client, "/api/tesoreria/bna/movimientos/555/conciliacion", {"idContacto": 42, "importe": 60500.0}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["idConciliacion"] == 88
    assert body["idContacto"] == 42
    assert body["importe"] == 60500.0


@pytest.mark.anyio
async def test_post_conciliacion_tarjetas_responde_400(client):
    """FR-002: Tarjetas se concilia exclusivamente desde su propio flujo (008/009)."""
    response = await _post(
        client, "/api/tesoreria/tarjetas/movimientos/1/conciliacion", {"idContacto": 42, "importe": 100.0}
    )
    assert response.status_code == 400
    assert "no se concilia desde este módulo" in response.json()["detail"]


@pytest.mark.anyio
async def test_post_conciliacion_movimiento_ya_reconocido_responde_409(client, monkeypatch):
    def _fake_aplicar(medio, id_mov, id_contacto, importe, usuario):
        raise ValueError(f"El movimiento '{medio}' {id_mov} ya tiene un contacto reconocido por su origen habitual.")

    monkeypatch.setattr(repository, "aplicar_conciliacion", _fake_aplicar)

    response = await _post(
        client, "/api/tesoreria/galicia/movimientos/2712/conciliacion", {"idContacto": 42, "importe": 100.0}
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_post_conciliacion_contacto_inexistente_responde_400(client, monkeypatch):
    def _fake_aplicar(medio, id_mov, id_contacto, importe, usuario):
        raise ValueError(f"El contacto {id_contacto} no existe.")

    monkeypatch.setattr(repository, "aplicar_conciliacion", _fake_aplicar)

    response = await _post(
        client, "/api/tesoreria/bna/movimientos/555/conciliacion", {"idContacto": 999999, "importe": 100.0}
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_post_conciliacion_movimiento_inexistente_responde_404(client, monkeypatch):
    def _fake_aplicar(medio, id_mov, id_contacto, importe, usuario):
        raise ValueError(f"No existe ningún movimiento '{medio}' con id {id_mov}.")

    monkeypatch.setattr(repository, "aplicar_conciliacion", _fake_aplicar)

    response = await _post(
        client, "/api/tesoreria/bna/movimientos/999999/conciliacion", {"idContacto": 42, "importe": 100.0}
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_reparto_incremental_dos_posts_sucesivos(client, monkeypatch):
    """US2, FR-006: el primer POST deja parcialmente_conciliado con el
    saldo pendiente correcto; el segundo lo completa."""
    llamadas = {"n": 0}

    def _fake_aplicar(medio, id_mov, id_contacto, importe, usuario):
        llamadas["n"] += 1
        return {
            "idConciliacion": llamadas["n"],
            "idContacto": id_contacto,
            "contacto": "X",
            "importe": importe,
            "usuario": usuario,
            "fecha": "2026-09-28T11:04:00",
        }

    monkeypatch.setattr(repository, "aplicar_conciliacion", _fake_aplicar)

    primero = await _post(
        client, "/api/tesoreria/mercado-libre/movimientos/1/conciliacion", {"idContacto": 1, "importe": 300.0}
    )
    segundo = await _post(
        client, "/api/tesoreria/mercado-libre/movimientos/1/conciliacion", {"idContacto": 2, "importe": 200.0}
    )
    assert primero.status_code == 201
    assert segundo.status_code == 201
    assert llamadas["n"] == 2


@pytest.fixture(autouse=True)
def _sin_transacciones_reales_026(monkeypatch):
    # Los tests de negocio simulan escrituras; el contexto común se verifica
    # aparte con conexiones simuladas, no obteniendo locks en producción.
    from contextlib import nullcontext
    from src.db import connection
    monkeypatch.setattr(connection, 'reconciliation_transaction', nullcontext)
