"""Contract tests for GET /api/tesoreria/{medio}/movimientos (FR-002/003/012/013)."""

from __future__ import annotations

import httpx
import pyodbc
import pytest

from src.features.tesoreria import estado_resolucion, repository
from src.main import app

FIXTURE_BNA = [
    {
        "idMovimientoBNA": 555,
        "fechaHora": "2026-08-05T10:15:00",
        "concepto": "Transferencia",
        "importe": -60500.00,
        "idContacto": 42,
        "contacto": "Rutas Sur Atlantico S.A.",
    }
]

FIXTURE_GALICIA = [
    {
        "idMovimiento": 900,
        "fecha": "2026-08-06",
        "descripcion": "Trf Inmed Proveed",
        "debitos": 46044.04,
        "creditos": 0,
        "saldo": 774943.40,
        "idContacto": 42,
        "contacto": "Rutas Sur Atlantico S.A.",
    }
]


@pytest.fixture
def intentos_sql(monkeypatch):
    """TEC-002: bloquea pyodbc.connect y cuenta los intentos; ninguna prueba debe tocar SQL."""
    intentos: list[tuple] = []

    def _bloqueado(*a, **k):
        intentos.append(a)
        raise RuntimeError("conexión SQL bloqueada en pruebas")

    monkeypatch.setattr(pyodbc, "connect", _bloqueado)
    return intentos


@pytest.fixture
def client(intentos_sql):
    return httpx.ASGITransport(app=app)


@pytest.fixture
def estados(monkeypatch):
    """Estado de conciliación simulado y controlado por la prueba."""
    llamadas: list[tuple[str, int]] = []

    def _estado(medio, id_movimiento):
        llamadas.append((medio, id_movimiento))
        return "conciliado"

    monkeypatch.setattr(estado_resolucion, "esta_resuelto", _estado)
    return llamadas


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _get(transport, url):
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(url)


@pytest.mark.anyio
async def test_list_movimientos_bna(client, estados, intentos_sql, monkeypatch):
    monkeypatch.setattr(
        repository, "get_movimientos", lambda *a, **k: (FIXTURE_BNA, 1)
    )

    response = await _get(client, "/api/tesoreria/bna/movimientos")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["concepto"] == "Transferencia"
    assert body["items"][0]["estadoConciliacion"] == "conciliado"
    assert estados == [("bna", 555)]
    assert intentos_sql == []


@pytest.mark.anyio
async def test_list_movimientos_galicia_has_saldo_field(client, estados, intentos_sql, monkeypatch):
    monkeypatch.setattr(
        repository, "get_movimientos", lambda *a, **k: (FIXTURE_GALICIA, 1)
    )

    response = await _get(client, "/api/tesoreria/galicia/movimientos")
    assert response.status_code == 200
    body = response.json()
    # Saldo is Galicia-specific, not forced onto BNA's shape (FR-002).
    assert body["items"][0]["saldo"] == 774943.40
    assert body["items"][0]["estadoConciliacion"] == "conciliado"
    assert estados == [("galicia", 900)]
    assert intentos_sql == []


@pytest.mark.anyio
async def test_list_movimientos_empty_result(client, monkeypatch):
    monkeypatch.setattr(repository, "get_movimientos", lambda *a, **k: ([], 0))

    response = await _get(client, "/api/tesoreria/bna/movimientos")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.anyio
async def test_list_movimientos_unknown_medio(client):
    response = await _get(client, "/api/tesoreria/inexistente/movimientos")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_movimientos_rejects_write_methods(client):
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        for method in ("post", "put", "delete", "patch"):
            resp = await ac.request(method, "/api/tesoreria/bna/movimientos")
            assert resp.status_code in (404, 405)


@pytest.mark.anyio
@pytest.mark.parametrize("extra", ["", "&estado=pendientes"])
async def test_fecha_hasta_maxima_sin_limite_superior(client, estados, intentos_sql, monkeypatch, extra):
    """TEC-003: fechaHasta=9999-12-31 se procesa como «sin límite superior», en ambos recorridos."""
    consultas: list[tuple[str, tuple]] = []

    def fake_one(sql, params):
        consultas.append((sql, params))
        return {"total": 1}

    def fake_all(sql, params):
        consultas.append((sql, params))
        return [{"id": 555}] if "AS id FROM" in sql else FIXTURE_BNA

    monkeypatch.setattr(repository, "fetch_one", fake_one)
    monkeypatch.setattr(repository, "fetch_all", fake_all)
    if extra:  # «Solo pendientes» conserva solo lo que sigue sin conciliar
        monkeypatch.setattr(estado_resolucion, "esta_resuelto", lambda m, i: estados.append((m, i)) or "sin_conciliar")

    response = await _get(client, f"/api/tesoreria/bna/movimientos?fechaDesde=2026-08-05&fechaHasta=9999-12-31{extra}")

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert consultas and all("FechaHora <" not in sql for sql, _ in consultas)
    assert intentos_sql == []
