"""Contract tests for POST/PUT/DELETE /api/ventas-hacienda y sus endpoints
de bloqueo/documentos relacionados (007-ventas-hacienda-granos).

`repository.create_venta`/`update_venta`/`delete_venta` se mockean
directamente porque su lógica interna (transacción, validación) ya tiene
cobertura propia en `test_db_connection.py` (execute_write_transaction) —
mismo patrón que `test_compras_alta_api.py` (006).
"""

from __future__ import annotations

import httpx
import pytest

from src.features.ventas_hacienda import repository, repository_locks
from src.main import app

VALID_BODY = {
    "idConsignatario": 82,
    "idEstablecimiento": 3,
    "idTipoDocumento": 6,
    "numeroDocumento": "0001-00004567",
    "fecha": "2026-09-17",
    "lineas": [
        {
            "idComprador": 512,
            "idTipoProducto": 4,
            "cantidad": 25,
            "unidadMedida": "Cabezas",
            "pesoTotal": 6250,
            "precioUnitarioA": 1200,
            "precioUnitarioB": 0,
        }
    ],
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --- US1: alta ---


@pytest.mark.anyio
async def test_post_venta_hacienda_alta_exitosa_calcula_totales(client, monkeypatch):
    monkeypatch.setattr(repository, "create_venta", lambda cabecera, lineas, vencimientos: 999)
    monkeypatch.setattr(repository, "get_vencimientos_venta", lambda id_venta: [])
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-hacienda", json=VALID_BODY)

    assert response.status_code == 201
    body = response.json()
    assert body["idVenta"] == 999
    assert body["subTotal"] == 25 * 1200
    assert body["importeTotal"] == 25 * 1200  # sin comisión/IVA/deducciones cargados
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_post_venta_hacienda_dos_compradores_distintos(client, monkeypatch):
    monkeypatch.setattr(repository, "create_venta", lambda cabecera, lineas, vencimientos: 1000)
    monkeypatch.setattr(repository, "get_vencimientos_venta", lambda id_venta: [])
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: False)

    body = {
        **VALID_BODY,
        "lineas": [
            {**VALID_BODY["lineas"][0], "idComprador": 512},
            {**VALID_BODY["lineas"][0], "idComprador": 600},
        ],
    }
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-hacienda", json=body)

    assert response.status_code == 201
    compradores = [l["idComprador"] for l in response.json()["lineas"]]
    assert compradores == [512, 600]


@pytest.mark.anyio
async def test_post_venta_hacienda_sin_lineas_es_422(client):
    body = {**VALID_BODY, "lineas": []}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-hacienda", json=body)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_venta_hacienda_sin_id_consignatario_es_422(client):
    body = {k: v for k, v in VALID_BODY.items() if k != "idConsignatario"}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-hacienda", json=body)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_venta_hacienda_linea_sin_comprador_es_422(client):
    body = {**VALID_BODY, "lineas": [{k: v for k, v in VALID_BODY["lineas"][0].items() if k != "idComprador"}]}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-hacienda", json=body)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_venta_hacienda_consignatario_tipo_invalido_es_400(client, monkeypatch):
    def fake_create(cabecera, lineas, vencimientos):
        raise ValueError(["El consignatario seleccionado no existe o no es de un tipo válido."])

    monkeypatch.setattr(repository, "create_venta", fake_create)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-hacienda", json=VALID_BODY)

    assert response.status_code == 400


@pytest.mark.anyio
async def test_post_venta_hacienda_documento_duplicado_no_bloquea(client, monkeypatch):
    """Decisión Q3: advertencia no bloqueante, nunca 400 — a diferencia de Compras (006)."""
    monkeypatch.setattr(repository, "create_venta", lambda cabecera, lineas, vencimientos: 1001)
    monkeypatch.setattr(repository, "get_vencimientos_venta", lambda id_venta: [])
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: True)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-hacienda", json=VALID_BODY)

    assert response.status_code == 201
    assert len(response.json()["warnings"]) == 1


# --- US2: lock + edición ---


@pytest.mark.anyio
async def test_lock_venta_hacienda_primer_token_adquiere_segundo_es_409(client, monkeypatch):
    calls = {"tokens": []}

    def fake_adquirir(id_venta, lock_token, force=False):
        calls["tokens"].append(lock_token)
        from datetime import datetime

        if len(calls["tokens"]) == 1:
            return repository_locks.LockInfo(id_venta, lock_token, datetime(2026, 9, 17, 12, 0))
        return None

    monkeypatch.setattr(repository_locks, "adquirir_lock", fake_adquirir)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        r1 = await ac.post("/api/ventas-hacienda/1/lock", json={"lockToken": "A"})
        r2 = await ac.post("/api/ventas-hacienda/1/lock", json={"lockToken": "B"})

    assert r1.status_code == 200
    assert r2.status_code == 409


@pytest.mark.anyio
async def test_lock_venta_hacienda_force_toma_igual(client, monkeypatch):
    from datetime import datetime

    monkeypatch.setattr(
        repository_locks,
        "adquirir_lock",
        lambda id_venta, lock_token, force=False: repository_locks.LockInfo(
            id_venta, lock_token, datetime(2026, 9, 17, 12, 5)
        ),
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-hacienda/1/lock", json={"lockToken": "B", "force": True})

    assert response.status_code == 200


@pytest.mark.anyio
async def test_delete_lock_venta_hacienda(client, monkeypatch):
    monkeypatch.setattr(repository_locks, "liberar_lock", lambda id_venta, token: token == "A")

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        ok = await ac.delete("/api/ventas-hacienda/1/lock", headers={"X-Lock-Token": "A"})
        conflict = await ac.delete("/api/ventas-hacienda/1/lock", headers={"X-Lock-Token": "B"})

    assert ok.status_code == 204
    assert conflict.status_code == 409


@pytest.mark.anyio
async def test_put_venta_hacienda_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put(
            "/api/ventas-hacienda/999999", json=VALID_BODY, headers={"X-Lock-Token": "A"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_put_venta_hacienda_sin_lock_es_409(client, monkeypatch):
    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: {"idVenta": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_venta, token: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/ventas-hacienda/1", json=VALID_BODY, headers={"X-Lock-Token": "B"})

    assert response.status_code == 409


@pytest.mark.anyio
async def test_put_venta_hacienda_con_lock_recalcula_totales(client, monkeypatch):
    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: {"idVenta": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_venta, token: True)
    monkeypatch.setattr(repository, "update_venta", lambda *a, **kw: None)
    monkeypatch.setattr(repository, "get_vencimientos_venta", lambda id_venta: [])
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: False)

    body = {**VALID_BODY, "lineas": [{**VALID_BODY["lineas"][0], "precioUnitarioA": 1500}]}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/ventas-hacienda/1", json=body, headers={"X-Lock-Token": "A"})

    assert response.status_code == 200
    assert response.json()["subTotal"] == 25 * 1500


# --- US3: eliminación ---


@pytest.mark.anyio
async def test_delete_venta_hacienda_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/ventas-hacienda/999999", headers={"X-Lock-Token": "A"})

    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_venta_hacienda_sin_lock_es_409(client, monkeypatch):
    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: {"idVenta": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_venta, token: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/ventas-hacienda/1", headers={"X-Lock-Token": "B"})

    assert response.status_code == 409


@pytest.mark.anyio
async def test_delete_venta_hacienda_con_lock_elimina(client, monkeypatch):
    borrado = {"id": None}

    def fake_delete(id_venta):
        borrado["id"] = id_venta

    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: {"idVenta": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_venta, token: True)
    monkeypatch.setattr(repository, "delete_venta", fake_delete)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/ventas-hacienda/1", headers={"X-Lock-Token": "A"})

    assert response.status_code == 204
    assert borrado["id"] == 1


# --- US4: documentos relacionados ---


@pytest.mark.anyio
async def test_get_documentos_relacionados_vacio(client, monkeypatch):
    monkeypatch.setattr(repository, "get_documentos_relacionados", lambda id_venta: [])

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/ventas-hacienda/1/relacionados")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_vincular_y_desvincular_documento_relacionado(client, monkeypatch):
    monkeypatch.setattr(repository, "agregar_documento_relacionado", lambda *a: None)
    monkeypatch.setattr(repository, "quitar_documento_relacionado", lambda *a: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        vincular = await ac.post("/api/ventas-hacienda/1/relacionados", json={"idVentaRelacionada": 2})
        desvincular = await ac.delete("/api/ventas-hacienda/1/relacionados/2")

    assert vincular.status_code == 204
    assert desvincular.status_code == 204
