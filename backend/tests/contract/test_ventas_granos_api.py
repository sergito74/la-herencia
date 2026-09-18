"""Contract tests for /api/ventas-granos (007-ventas-hacienda-granos) —
dominio 100% nuevo, lectura + alta/edición/eliminación desde el arranque.

`repository.*` se mockea directamente — mismo patrón que
`test_compras_alta_api.py`/`test_ventas_hacienda_alta_api.py`.
"""

from __future__ import annotations

import httpx
import pytest

from src.features.ventas_granos import repository, repository_locks
from src.main import app

VALID_BODY = {
    "idConsignatario": 219,
    "idTipoDocumento": 6,
    "idProducto": 1,
    "numeroDocumento": "0002-00001122",
    "fecha": "2026-09-17",
    "precioUnitario": 285000,
    "factor": 100,
    "flete": 0,
    "cantidadEntregada": 32000,
    "cantidadVendida": 32000,
    "alicuotaIVA": 10.5,
}


@pytest.fixture
def client():
    return httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --- US5: listado (lectura) ---


@pytest.mark.anyio
async def test_list_ventas_granos_sin_filtro_devuelve_vacio(client, monkeypatch):
    """FR-010: sin filtro, ni siquiera se ejecuta la query — `search_ventas`
    real ya maneja esto, pero acá confirmamos el contrato HTTP."""
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/ventas-granos")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


@pytest.mark.anyio
async def test_list_ventas_granos_con_filtro(client, monkeypatch):
    def fake_search(consignatario, numero_documento, fecha_desde, fecha_hasta, campania, page, page_size, sort_by, sort_dir):
        assert numero_documento == "0002"
        return (
            [
                {
                    "idVenta": 1,
                    "fecha": "2026-09-17",
                    "consignatario": {"idContacto": 219, "razonSocial": "Acopio Central"},
                    "tipoDocumento": "Liquidacion",
                    "numeroDocumento": "0002-00001122",
                    "grano": "Soja",
                    "campania": "2025/2026",
                }
            ],
            1,
        )

    monkeypatch.setattr(repository, "search_ventas", fake_search)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/ventas-granos?numeroDocumento=0002")

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.anyio
async def test_get_venta_granos_detalle_ajustes_deducciones_separados(client, monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_venta_cabecera",
        lambda id_venta: {
            **VALID_BODY,
            "retencionIVA": 0,
            "retIG": 0,
            "percepciones": 0,
            "otraRetenciones": 0,
            "sellado": 0,
            "derechoRegistro": 0,
            "honorariosCamara": 0,
            "aCuentaCalidad": 0,
            "iibb": 0,
        },
    )
    monkeypatch.setattr(
        repository, "get_ajustes", lambda id_venta: [{"idAjuste": 1, "concepto": "Bonif", "importe": 5000, "alicuotaIVA": 10.5}]
    )
    monkeypatch.setattr(
        repository,
        "get_deducciones",
        lambda id_venta: [{"idDeduccion": 1, "idConcepto": 3, "concepto": "Comision", "detalle": None, "porc": 2, "baseCalculo": 100000, "alicuota": 10.5}],
    )

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/ventas-granos/1")

    assert response.status_code == 200
    body = response.json()
    assert len(body["ajustes"]) == 1
    assert len(body["deducciones"]) == 1


@pytest.mark.anyio
async def test_get_venta_granos_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.get("/api/ventas-granos/999999")

    assert response.status_code == 404


# --- US6: alta ---


@pytest.mark.anyio
async def test_post_venta_granos_alta_exitosa(client, monkeypatch):
    monkeypatch.setattr(repository, "create_venta", lambda cabecera, ajustes, deducciones: 500)
    monkeypatch.setattr(repository, "get_ajustes", lambda id_venta: [])
    monkeypatch.setattr(repository, "get_deducciones", lambda id_venta: [])
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-granos", json=VALID_BODY)

    assert response.status_code == 201
    body = response.json()
    assert body["idVenta"] == 500
    # precioKg = (285000*100/100 - 0)/1000 = 285; subTotal = 32000*285 = 9120000
    assert body["subTotal"] == pytest.approx(9120000)
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_post_venta_granos_con_ajuste_y_deduccion(client, monkeypatch):
    monkeypatch.setattr(repository, "create_venta", lambda cabecera, ajustes, deducciones: 501)
    monkeypatch.setattr(repository, "get_ajustes", lambda id_venta: [{"idAjuste": 1, "concepto": "Bonif", "importe": 5000, "alicuotaIVA": 0}])
    monkeypatch.setattr(
        repository, "get_deducciones", lambda id_venta: [{"idDeduccion": 1, "idConcepto": 3, "concepto": "Comision", "detalle": None, "porc": 2, "baseCalculo": 100000, "alicuota": 0}]
    )
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: False)

    body = {
        **VALID_BODY,
        "ajustes": [{"concepto": "Bonif", "importe": 5000, "alicuotaIVA": 0}],
        "deducciones": [{"idConcepto": 3, "porc": 2, "baseCalculo": 100000, "alicuota": 0}],
    }
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-granos", json=body)

    assert response.status_code == 201
    result = response.json()
    # subTotal ahora incluye el ajuste de 5000; totalDeducciones = 100000*2/100 = 2000
    assert result["subTotal"] == pytest.approx(9120000 + 5000)
    assert result["totalDeducciones"] == pytest.approx(2000)
    assert result["importeNetoAPercibir"] < result["totalOperacion"]


@pytest.mark.anyio
async def test_post_venta_granos_campos_requeridos_faltantes_es_422(client):
    body = {k: v for k, v in VALID_BODY.items() if k not in ("idConsignatario", "idProducto")}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-granos", json=body)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_venta_granos_documento_duplicado_no_bloquea(client, monkeypatch):
    monkeypatch.setattr(repository, "create_venta", lambda cabecera, ajustes, deducciones: 502)
    monkeypatch.setattr(repository, "get_ajustes", lambda id_venta: [])
    monkeypatch.setattr(repository, "get_deducciones", lambda id_venta: [])
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: True)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.post("/api/ventas-granos", json=VALID_BODY)

    assert response.status_code == 201
    assert len(response.json()["warnings"]) == 1


# --- US7: lock + edición + eliminación ---


@pytest.mark.anyio
async def test_lock_venta_granos_conflicto_y_force(client, monkeypatch):
    from datetime import datetime

    calls = {"tokens": []}

    def fake_adquirir(id_venta, lock_token, force=False):
        calls["tokens"].append((lock_token, force))
        if force or len(calls["tokens"]) == 1:
            return repository_locks.LockInfo(id_venta, lock_token, datetime(2026, 9, 17, 12, 0))
        return None

    monkeypatch.setattr(repository_locks, "adquirir_lock", fake_adquirir)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        r1 = await ac.post("/api/ventas-granos/1/lock", json={"lockToken": "A"})
        r2 = await ac.post("/api/ventas-granos/1/lock", json={"lockToken": "B"})
        r3 = await ac.post("/api/ventas-granos/1/lock", json={"lockToken": "B", "force": True})

    assert r1.status_code == 200
    assert r2.status_code == 409
    assert r3.status_code == 200


@pytest.mark.anyio
async def test_put_venta_granos_recalcula_con_nueva_deduccion(client, monkeypatch):
    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: {**VALID_BODY, "idVenta": id_venta})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_venta, token: True)
    monkeypatch.setattr(repository, "update_venta", lambda *a, **kw: None)
    monkeypatch.setattr(repository, "get_ajustes", lambda id_venta: [])
    monkeypatch.setattr(
        repository, "get_deducciones", lambda id_venta: [{"idDeduccion": 1, "idConcepto": 3, "concepto": "Comision", "detalle": None, "porc": 2, "baseCalculo": 100000, "alicuota": 0}]
    )
    monkeypatch.setattr(repository, "hay_documento_duplicado", lambda *a, **kw: False)

    body = {**VALID_BODY, "deducciones": [{"idConcepto": 3, "porc": 2, "baseCalculo": 100000, "alicuota": 0}]}
    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/ventas-granos/1", json=body, headers={"X-Lock-Token": "A"})

    assert response.status_code == 200
    assert response.json()["totalDeducciones"] == pytest.approx(2000)


@pytest.mark.anyio
async def test_put_venta_granos_inexistente_es_404(client, monkeypatch):
    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: None)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.put("/api/ventas-granos/999999", json=VALID_BODY, headers={"X-Lock-Token": "A"})

    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_venta_granos_sin_lock_es_409(client, monkeypatch):
    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: {"idVenta": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_venta, token: False)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/ventas-granos/1", headers={"X-Lock-Token": "B"})

    assert response.status_code == 409


@pytest.mark.anyio
async def test_delete_venta_granos_con_lock_elimina(client, monkeypatch):
    borrado = {"id": None}

    def fake_delete(id_venta):
        borrado["id"] = id_venta

    monkeypatch.setattr(repository, "get_venta_cabecera", lambda id_venta: {"idVenta": 1})
    monkeypatch.setattr(repository_locks, "verificar_lock", lambda id_venta, token: True)
    monkeypatch.setattr(repository, "delete_venta", fake_delete)

    async with httpx.AsyncClient(transport=client, base_url="http://test") as ac:
        response = await ac.delete("/api/ventas-granos/1", headers={"X-Lock-Token": "A"})

    assert response.status_code == 204
    assert borrado["id"] == 1


def test_calcular_totales_formula_real():
    """Unit test puro de la fórmula (sin acceso a base) — T087/SC-003 la
    completa contra datos históricos reales, esto valida la aritmética."""
    cabecera = {
        "precioUnitario": 285000,
        "factor": 100,
        "flete": 0,
        "cantidadVendida": 32000,
        "alicuotaIVA": 10.5,
        "retIG": 1000,
        "retencionIVA": 500,
        "percepciones": 0,
        "otraRetenciones": 0,
    }
    ajustes = [{"importe": 5000}]
    deducciones = [{"baseCalculo": 100000, "porc": 2, "alicuota": 10.5}]

    totales = repository.calcular_totales(cabecera, ajustes, deducciones)

    assert totales["precioKg"] == pytest.approx(285.0)
    assert totales["subTotal"] == pytest.approx(32000 * 285 + 5000)
    assert totales["iva"] == pytest.approx(totales["subTotal"] * 0.105)
    assert totales["totalRetenciones"] == pytest.approx(1500)
    # deduccion: (100000*2/100) + (100000*2/100 * 10.5/100) = 2000 + 210 = 2210
    assert totales["totalDeducciones"] == pytest.approx(2210)
    assert totales["importeNetoAPercibir"] == pytest.approx(
        totales["totalOperacion"] - (1500 + 0 + 0 + 2210)
    )
