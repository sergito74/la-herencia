"""Contract tests for /api/tarjetas-cuotas (008-tarjetas, Historia 3)."""

from __future__ import annotations

from datetime import date, datetime

import httpx
import pytest

from src.features.tarjetas_cuotas import repository, repository_locks
from src.features.tarjetas_cuotas.calculo_cuotas import generar_cronograma
from src.main import app

VALID_BODY = {
    "idContacto": 245,
    "fecha": "2026-09-18",
    "nroComprobante": 8834,
    "importeTotal": 10000,
    "cantidadCuotas": 3,
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --- calculo_cuotas puro ---


def test_generar_cronograma_ajusta_redondeo_en_ultima():
    cuotas = generar_cronograma(date(2026, 9, 18), 10000, 3)
    assert [c["importe"] for c in cuotas] == [3333.33, 3333.33, 3333.34]
    assert round(sum(c["importe"] for c in cuotas), 2) == 10000.0
    assert cuotas[0]["fechaVencimiento"] == date(2026, 10, 18)
    assert cuotas[1]["fechaVencimiento"] == date(2026, 11, 18)
    assert cuotas[2]["fechaVencimiento"] == date(2026, 12, 18)


def test_generar_cronograma_una_sola_cuota():
    cuotas = generar_cronograma(date(2026, 9, 18), 5000, 1)
    assert len(cuotas) == 1
    assert cuotas[0]["importe"] == 5000


# --- FR-006: listado vacío por defecto ---


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
                    "fecha": "2026-09-18",
                    "nroComprobante": 8834,
                    "cantidadCuotas": 3,
                    "cuotasCobradas": 0,
                    "cuotasPendientes": 3,
                }
            ],
            1,
        ),
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/tarjetas-cuotas?idContacto=245")

    assert response.status_code == 200
    assert response.json()["total"] == 1


# --- US3: alta ---


@pytest.mark.anyio
async def test_post_compra_genera_cronograma_correcto(client, monkeypatch):
    monkeypatch.setattr(repository, "create_compra", lambda cabecera: 1)
    monkeypatch.setattr(
        repository,
        "get_detalle",
        lambda id_pago_tarjeta: {"idPagoTarjeta": 1, "idContacto": 245, "contacto": "Juan Perez", "fecha": "2026-09-18", "nroComprobante": 8834, "cantidadCuotas": 3},
    )
    monkeypatch.setattr(
        repository,
        "get_cuotas",
        lambda id_pago_tarjeta: [
            {"idCuota": 1, "numeroCuota": 1, "fechaVencimiento": "2026-10-18", "importe": 3333.33, "cobrado": False},
            {"idCuota": 2, "numeroCuota": 2, "fechaVencimiento": "2026-11-18", "importe": 3333.33, "cobrado": False},
            {"idCuota": 3, "numeroCuota": 3, "fechaVencimiento": "2026-12-18", "importe": 3333.34, "cobrado": False},
        ],
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/tarjetas-cuotas", json=VALID_BODY)

    assert response.status_code == 201
    body = response.json()
    assert len(body["cuotas"]) == 3
    assert round(body["importeTotal"], 2) == 10000.0


@pytest.mark.anyio
async def test_post_compra_una_sola_cuota(client, monkeypatch):
    body = {**VALID_BODY, "cantidadCuotas": 1}
    monkeypatch.setattr(repository, "create_compra", lambda cabecera: 2)
    monkeypatch.setattr(
        repository,
        "get_detalle",
        lambda id_pago_tarjeta: {"idPagoTarjeta": 2, "idContacto": 245, "contacto": "Juan Perez", "fecha": "2026-09-18", "nroComprobante": 8834, "cantidadCuotas": 1},
    )
    monkeypatch.setattr(
        repository,
        "get_cuotas",
        lambda id_pago_tarjeta: [
            {"idCuota": 1, "numeroCuota": 1, "fechaVencimiento": "2026-10-18", "importe": 10000, "cobrado": False},
        ],
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/tarjetas-cuotas", json=body)

    assert response.status_code == 201
    assert len(response.json()["cuotas"]) == 1


@pytest.mark.anyio
async def test_post_compra_sin_campos_requeridos_es_422(client):
    body = {k: v for k, v in VALID_BODY.items() if k != "idContacto"}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/tarjetas-cuotas", json=body)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_compra_cantidad_cuotas_invalida_es_422(client):
    body = {**VALID_BODY, "cantidadCuotas": 0}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/tarjetas-cuotas", json=body)

    assert response.status_code == 422


# --- US3: marcar cobrada ---


@pytest.mark.anyio
async def test_patch_marcar_cobrada(client, monkeypatch):
    monkeypatch.setattr(repository, "marcar_cobrada", lambda id_cuota, cobrado: None)
    monkeypatch.setattr(
        repository,
        "get_cuotas",
        lambda id_pago_tarjeta: [
            {"idCuota": 1, "numeroCuota": 1, "fechaVencimiento": "2026-10-18", "importe": 3333.33, "cobrado": True},
        ],
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.patch("/api/tarjetas-cuotas/1/cuotas/1", json={"cobrado": True})

    assert response.status_code == 200
    assert response.json()["cobrado"] is True


# --- FR-013: lock / edición / eliminación ---


@pytest.mark.anyio
async def test_lock_compra_primer_token_adquiere_segundo_es_409(client, monkeypatch):
    calls = {"n": 0}

    def fake_adquirir(id_pago_tarjeta, lock_token, force=False):
        calls["n"] += 1
        if calls["n"] == 1:
            return repository_locks.LockInfo(id_pago_tarjeta, lock_token, datetime(2026, 9, 18, 12, 0))
        return None

    monkeypatch.setattr(repository_locks, "adquirir_lock", fake_adquirir)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        r1 = await ac.post("/api/tarjetas-cuotas/1/lock", json={"lockToken": "A"})
        r2 = await ac.post("/api/tarjetas-cuotas/1/lock", json={"lockToken": "B"})

    assert r1.status_code == 200
    assert r2.status_code == 409


@pytest.mark.anyio
async def test_put_compra_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_detalle", lambda id_pago_tarjeta: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/tarjetas-cuotas/999999", json=VALID_BODY, headers={"X-Lock-Token": "A"})

    assert response.status_code == 404


@pytest.mark.anyio
async def test_put_compra_sin_lock_es_409(client, monkeypatch):
    monkeypatch.setattr(repository, "get_detalle", lambda id_pago_tarjeta: {"idPagoTarjeta": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_pago_tarjeta, token: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/tarjetas-cuotas/1", json=VALID_BODY, headers={"X-Lock-Token": "B"})

    assert response.status_code == 409


@pytest.mark.anyio
async def test_put_compra_con_lock_regenera_cronograma_pierde_cobrado(client, monkeypatch):
    """FR-007a (Clarifications 2026-09-18): el PUT regenera el cronograma
    completo siempre; una cuota antes cobrada vuelve a `cobrado=False`
    porque el repository real la recrea desde cero (contrato de la
    respuesta, no la implementación interna de `update_compra`)."""
    monkeypatch.setattr(repository, "get_detalle", lambda id_pago_tarjeta: {"idPagoTarjeta": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_pago_tarjeta, token: True)
    monkeypatch.setattr(repository, "update_compra", lambda *a, **kw: None)
    monkeypatch.setattr(
        repository,
        "get_detalle",
        lambda id_pago_tarjeta: {"idPagoTarjeta": 1, "idContacto": 245, "contacto": "Juan Perez", "fecha": "2026-09-18", "nroComprobante": 8834, "cantidadCuotas": 2},
    )
    monkeypatch.setattr(
        repository,
        "get_cuotas",
        lambda id_pago_tarjeta: [
            {"idCuota": 10, "numeroCuota": 1, "fechaVencimiento": "2026-10-18", "importe": 5000, "cobrado": False},
            {"idCuota": 11, "numeroCuota": 2, "fechaVencimiento": "2026-11-18", "importe": 5000, "cobrado": False},
        ],
    )

    body = {**VALID_BODY, "cantidadCuotas": 2}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/tarjetas-cuotas/1", json=body, headers={"X-Lock-Token": "A"})

    assert response.status_code == 200
    assert all(c["cobrado"] is False for c in response.json()["cuotas"])


@pytest.mark.anyio
async def test_delete_compra_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_detalle", lambda id_pago_tarjeta: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/tarjetas-cuotas/999999", headers={"X-Lock-Token": "A"})

    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_compra_sin_lock_es_409(client, monkeypatch):
    monkeypatch.setattr(repository, "get_detalle", lambda id_pago_tarjeta: {"idPagoTarjeta": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_pago_tarjeta, token: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/tarjetas-cuotas/1", headers={"X-Lock-Token": "B"})

    assert response.status_code == 409


@pytest.mark.anyio
async def test_delete_compra_con_lock_elimina(client, monkeypatch):
    borrado = {"id": None}

    def fake_delete(id_pago_tarjeta):
        borrado["id"] = id_pago_tarjeta

    monkeypatch.setattr(repository, "get_detalle", lambda id_pago_tarjeta: {"idPagoTarjeta": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_pago_tarjeta, token: True)
    monkeypatch.setattr(repository, "delete_compra", fake_delete)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/tarjetas-cuotas/1", headers={"X-Lock-Token": "A"})

    assert response.status_code == 204
    assert borrado["id"] == 1
