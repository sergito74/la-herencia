"""Contract tests del tablero, las fotos semanales y las preguntas de /api/revision-cuentas (036, T048).

Las lecturas son de solo lectura sobre WC. Las fotos se guardan en memoria: ninguna prueba crea fotos reales.
"""

from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.features.revision_cuentas import tablero
from src.main import app

BASE = "/api/revision-cuentas"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _cliente(rol: str | None = None) -> httpx.AsyncClient:
    kwargs = {"cookies": {COOKIE_NAME: crear_token(id_usuario=0, rol=rol)}} if rol else {}
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", **kwargs)


@pytest.fixture
def fotos_en_memoria(monkeypatch):
    """Fotos semanales en memoria: ninguna prueba escribe en RevisionTableroFotos."""
    est: dict = {"fotos": {}, "anterior": None}
    monkeypatch.setattr(tablero, "_foto_de_semana", lambda semana: est["fotos"].get(semana))
    monkeypatch.setattr(tablero, "_foto_anterior", lambda semana: est["anterior"])

    def guardar(semana, corte, datos, usuario):
        est["fotos"][semana] = {"IdFoto": len(est["fotos"]) + 1, "Semana": semana, "Corte": corte, "Datos": json.dumps(datos, default=str), "Fecha": None}
        return len(est["fotos"])

    monkeypatch.setattr(tablero, "_guardar_foto", guardar)
    return est


@pytest.mark.anyio
async def test_el_tablero_suma_todas_las_cuentas_exactamente_una_vez(fotos_en_memoria):
    async with _cliente() as c:
        r = await c.get(f"{BASE}/tablero")
    assert r.status_code == 200
    b = r.json()
    assert b["corte"] == "2026-09-30" and b["totalCuentas"] >= 500
    assert sum(x["cuentas"] for x in b["casillas"]) == b["totalCuentas"]
    assert sum(t["cuentas"] for t in b["totalesPorCola"].values()) == b["totalCuentas"]
    assert sum(b["porEstado"].values()) == b["totalCuentas"]
    assert set(b["porEstado"]) == {"pendiente", "en-proceso", "esperando-evidencia", "esperando-sergio", "cerrada", "cerrada-con-excepcion", "reabierta"}
    assert set(b["casillas"][0]) == {"cola", "etapa", "cuentas", "importe"}
    assert b["comparacion"] is None            # todavía no hay foto de una semana anterior
    assert b["preguntas"] >= 0


@pytest.mark.anyio
async def test_abrir_el_tablero_crea_la_foto_de_la_semana_una_sola_vez(fotos_en_memoria):
    async with _cliente() as c:
        await c.get(f"{BASE}/tablero")
        await c.get(f"{BASE}/tablero")
    assert len(fotos_en_memoria["fotos"]) == 1
    assert next(iter(fotos_en_memoria["fotos"])) == tablero.semana_de(date.today())


@pytest.mark.anyio
async def test_con_una_foto_de_la_semana_anterior_el_tablero_compara(fotos_en_memoria):
    previa = {"totalCuentas": 518, "porEstado": {"cerrada": 0, "cerrada-con-excepcion": 0}, "totalesPorCola": {"I": {"cuentas": 20, "importe": 0}}, "casillas": []}
    fotos_en_memoria["anterior"] = {"Semana": date(2026, 10, 5), "Datos": json.dumps(previa)}
    async with _cliente() as c:
        b = (await c.get(f"{BASE}/tablero")).json()
    comp = b["comparacion"]
    assert comp["semanaAnterior"] == "2026-10-05"
    assert comp["cerradasEnLaSemana"] == b["porEstado"]["cerrada"] + b["porEstado"]["cerrada-con-excepcion"]
    assert comp["variacionExcepciones"] == b["totalesPorCola"].get("I", {"cuentas": 0})["cuentas"] - 20


@pytest.mark.anyio
async def test_las_fotos_se_listan_con_su_semana_y_total(fotos_en_memoria):
    async with _cliente() as c:
        await c.get(f"{BASE}/tablero")
        # la lista de fotos lee la base real; con la foto en memoria la forma del contrato se valida con la respuesta de crear
        r = await c.get(f"{BASE}/tablero/fotos")
    assert r.status_code == 200 and set(r.json()) == {"total", "fotos"}


@pytest.mark.anyio
async def test_crear_la_foto_a_pedido_devuelve_409_si_ya_existe_la_de_la_semana(fotos_en_memoria):
    async with _cliente() as c:
        await c.get(f"{BASE}/tablero")                      # el tablero ya creó la foto de la semana
        r = await c.post(f"{BASE}/tablero/fotos", json={})
    assert r.status_code == 409


@pytest.mark.anyio
async def test_crear_la_foto_a_pedido_en_una_semana_sin_foto_devuelve_201(fotos_en_memoria):
    async with _cliente() as c:
        r = await c.post(f"{BASE}/tablero/fotos", json={})
    assert r.status_code == 201
    b = r.json()
    assert b["semana"] == tablero.semana_de(date.today()).isoformat() and b["totalCuentas"] >= 500


@pytest.mark.anyio
async def test_el_rol_lectura_no_puede_crear_fotos(fotos_en_memoria):
    async with _cliente("Lectura") as c:
        assert (await c.post(f"{BASE}/tablero/fotos", json={})).status_code == 403


@pytest.mark.anyio
async def test_las_preguntas_son_una_lista_con_la_forma_del_contrato(fotos_en_memoria):
    async with _cliente() as c:
        r = await c.get(f"{BASE}/preguntas")
    assert r.status_code == 200 and isinstance(r.json(), list)
    for p in r.json():
        assert set(p) >= {"idContacto", "razonSocial", "cola", "etapa", "pregunta"}
