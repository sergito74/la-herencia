"""Contract tests for /api/tarjetas-cuenta (034, Historia 1). Solo lectura sobre WC."""

from __future__ import annotations

import httpx
import pytest

from src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _get(url: str) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        return await c.get(url)


@pytest.mark.anyio
async def test_resumen_trae_todas_las_tarjetas_y_aviso():
    r = await _get("/api/tarjetas-cuenta/resumen")
    assert r.status_code == 200
    body = r.json()
    assert len(body["tarjetas"]) + len(body["tarjetasSinContacto"]) >= 5
    assert round(sum(t["saldo"] for t in body["tarjetas"]) - body["total"]["saldo"], 2) == 0
    assert "IVA" in body["avisoSaldo"]


@pytest.mark.anyio
async def test_cuenta_saldo_final_es_inicial_mas_movimientos():
    r = await _get("/api/tarjetas-cuenta/4?agrupar=movimientos")
    assert r.status_code == 200
    b = r.json()
    neto = sum(f["credito"] - f["deuda"] for f in b["filas"])
    assert round(b["saldoInicial"] + neto - b["saldoFinal"], 2) == 0
    d = b["detalleSaldo"]
    assert round(d["exigible"] + d["noResumido"] - b["saldoFinal"], 2) == 0


@pytest.mark.anyio
async def test_cuenta_por_resumen_conserva_el_saldo():
    a = (await _get("/api/tarjetas-cuenta/2?agrupar=movimientos")).json()
    b = (await _get("/api/tarjetas-cuenta/2?agrupar=resumenes")).json()
    assert a["saldoFinal"] == b["saldoFinal"]


@pytest.mark.anyio
async def test_filtro_desde_arma_saldo_inicial():
    todo = (await _get("/api/tarjetas-cuenta/4")).json()
    parcial = (await _get("/api/tarjetas-cuenta/4?desde=2025-01-01")).json()
    assert parcial["saldoFinal"] == todo["saldoFinal"]
    assert len(parcial["filas"]) < len(todo["filas"])


@pytest.mark.anyio
async def test_errores():
    assert (await _get("/api/tarjetas-cuenta/99999")).status_code == 404
    assert (await _get("/api/tarjetas-cuenta/1?agrupar=otra")).status_code == 422


@pytest.mark.anyio
async def test_exportar_devuelve_xlsx():
    r = await _get("/api/tarjetas-cuenta/2/exportar")
    assert r.status_code == 200
    assert r.content[:2] == b"PK"


@pytest.mark.anyio
async def test_control_casos_conocidos_y_filtros():
    b = (await _get("/api/tarjetas-cuenta/control")).json()
    assert sum(b["resumenPorCategoria"].values()) == len(b["hallazgos"])
    # la devolución BNA 9426 de AgroNacion se cruzó el 06/10/2026 (cruce #1): ya no se informa
    assert not any(h["categoria"] == "devolucion-sin-cruzar" and h["idMovimiento"] == 9426 for h in b["hallazgos"])
    uno = (await _get("/api/tarjetas-cuenta/control?categoria=pago-en-proveedor")).json()
    assert {h["categoria"] for h in uno["hallazgos"]} <= {"pago-en-proveedor"}
    assert uno["resumenPorCategoria"] == b["resumenPorCategoria"]
    visa = (await _get("/api/tarjetas-cuenta/control?idTarjeta=4")).json()
    assert all(h["idTarjeta"] == 4 for h in visa["hallazgos"])


@pytest.mark.anyio
async def test_control_errores_y_exportacion():
    assert (await _get("/api/tarjetas-cuenta/control?categoria=inexistente")).status_code == 422
    r = await _get("/api/tarjetas-cuenta/control/exportar")
    assert r.status_code == 200 and r.content[:2] == b"PK"


async def _post(url: str, body: dict) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        return await c.post(url, json=body)


@pytest.mark.anyio
async def test_sugerencias_de_cruce_traen_los_casos_conocidos():
    cruces = (await _get("/api/tarjetas-cuenta/cruces")).json()
    assert any(c["idMovimientoOrigen"] == 9426 and c["idMovimientoDestino"] == 18093 for c in cruces)
    d = (await _get("/api/tarjetas-cuenta/cruces/sugerencias?tipo=devolucion-debito")).json()["sugerencias"]
    assert not any(s["origen"]["idMovimiento"] == 9426 for s in d)
    assert (await _get("/api/tarjetas-cuenta/cruces/sugerencias?tipo=otro")).status_code == 422
    assert (await _get("/api/tarjetas-cuenta/cruces")).status_code == 200


@pytest.mark.anyio
async def test_alta_de_cruce_rechaza_sin_escribir():
    # importes distintos: la devolución 9426 no puede cruzarse con un débito menor
    r = await _post("/api/tarjetas-cuenta/cruces", {"tipo": "devolucion-debito", "idTarjeta": 4, "origen": {"medio": "bna", "idMovimiento": 9426},
                                                    "destino": {"medio": "bna", "idMovimiento": 18093}})
    assert r.status_code == 409  # 9426 ya está cruzado (cruce #1)
    r = await _post("/api/tarjetas-cuenta/cruces", {"tipo": "devolucion-debito", "idTarjeta": 1, "origen": {"medio": "bna", "idMovimiento": 99999999},
                                                    "destino": {"medio": "bna", "idMovimiento": 18093}})
    assert r.status_code == 404
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.delete("/api/tarjetas-cuenta/cruces/99999999")).status_code == 404


@pytest.mark.anyio
async def test_cada_fila_trae_referencia_para_navegar():
    tipos = set()
    for id_t in (1, 2, 4):
        for f in (await _get(f"/api/tarjetas-cuenta/{id_t}")).json()["filas"]:
            r = f["referencia"]
            if r:
                tipos.add(r["tipo"])
                if r["tipo"] == "movimiento-bancario":
                    assert r["medio"] in ("bna", "galicia", "efectivo") and r["idMovimiento"]
                if r["tipo"] == "linea-consumo":
                    assert r["idLineaConsumo"]
                if r["tipo"] == "cruce":
                    assert r["idCruce"]
    assert {"linea-consumo", "resumen", "movimiento-bancario", "cruce"} <= tipos
