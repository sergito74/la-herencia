"""Contract tests de /api/descarga-peajes (037, desde 042 sobre la Bóveda de portales).

Todo simulado: la bóveda (portales, corridas, documentos) y el servicio que dispara las corridas. Nunca entra a un
portal ni escribe en WC (18/11/2026: la versión anterior no simulaba el servicio y disparaba una corrida real)."""

from __future__ import annotations

import httpx
import pytest

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.features.descarga_peajes import router
from src.main import app

PORTALES = [
    {"idPortal": 1, "nombre": "TelePASE", "codigoConector": "telepase", "claveConfigurada": True, "credencialRechazada": False,
     "autFecha": "2026-10-16", "suspendida": False, "proximaCorrida": None, "ucId": 7, "ucEstado": "ok", "ucInicio": None},
    {"idPortal": 2, "nombre": "AUBASA", "codigoConector": "aubasa", "claveConfigurada": True, "credencialRechazada": True,
     "autFecha": None, "suspendida": True, "proximaCorrida": None, "ucId": None, "ucEstado": None, "ucInicio": None},
    {"idPortal": 9, "nombre": "Bayá Casal", "codigoConector": "baya", "claveConfigurada": True, "credencialRechazada": False,
     "autFecha": "2026-10-20", "suspendida": False, "proximaCorrida": None, "ucId": None, "ucEstado": None, "ucInicio": None},
]


@pytest.fixture
def transport(monkeypatch):
    llamadas = []
    monkeypatch.setattr(router.boveda, "listar_portales", lambda: [dict(p) for p in PORTALES])
    monkeypatch.setattr(router.boveda, "revalidar_pendientes", lambda: 0)
    monkeypatch.setattr(router.servicio, "en_cola", lambda: set())
    monkeypatch.setattr(router.servicio, "correr_varios_en_segundo_plano", lambda ids, u: llamadas.append((ids, u)))
    monkeypatch.setattr(router, "usuario_actual", lambda request: "sergio")
    t = httpx.ASGITransport(app=app)
    t.llamadas = llamadas
    return t


async def _req(transport, method, url, cookies=None):
    kwargs = {"cookies": cookies} if cookies is not None else {}
    async with httpx.AsyncClient(transport=transport, base_url="http://test", **kwargs) as ac:
        return await ac.request(method, url)


@pytest.mark.anyio
async def test_estado_solo_portales_de_peaje_y_sin_credenciales(transport):
    r = await _req(transport, "GET", "/api/descarga-peajes/estado")
    assert r.status_code == 200
    body = r.json()
    assert [p["portal"] for p in body["portales"]] == ["TelePASE", "AUBASA"]
    assert body["portales"][1]["credenciales"] is False and body["enCurso"] is False
    assert "clave" not in r.text.lower()


@pytest.mark.anyio
async def test_iniciar_corre_solo_los_autorizados(transport):
    r = await _req(transport, "POST", "/api/descarga-peajes/ejecuciones")
    assert r.status_code == 202 and r.json() == {"portales": [1]}
    assert transport.llamadas == [([1], "sergio")]


@pytest.mark.anyio
async def test_iniciar_con_otra_en_curso_devuelve_409(transport, monkeypatch):
    monkeypatch.setattr(router.boveda, "listar_portales", lambda: [{**PORTALES[0], "ucEstado": "en_curso"}])
    r = await _req(transport, "POST", "/api/descarga-peajes/ejecuciones")
    assert r.status_code == 409 and not transport.llamadas


@pytest.mark.anyio
async def test_iniciar_con_rol_lectura_devuelve_403(transport):
    cookies = {COOKIE_NAME: crear_token(id_usuario=5, rol="Lectura")}
    r = await _req(transport, "POST", "/api/descarga-peajes/ejecuciones", cookies=cookies)
    assert r.status_code == 403 and not transport.llamadas


@pytest.mark.anyio
async def test_documentos_valida_estado(transport, monkeypatch):
    monkeypatch.setattr(router.boveda, "listar_documentos", lambda *a, **k: ([], 0))
    assert (await _req(transport, "GET", "/api/descarga-peajes/documentos?estado=otro")).status_code == 400
    r = await _req(transport, "GET", "/api/descarga-peajes/documentos?estado=pendiente")
    assert r.status_code == 200 and r.json() == {"items": [], "total": 0}


@pytest.mark.anyio
async def test_resumen_contador(transport, monkeypatch):
    monkeypatch.setattr(router.boveda, "resumen", lambda ids: {"pendientesCarga": 3, "conError": 1, "requiereIntervencion": 1})
    r = await _req(transport, "GET", "/api/descarga-peajes/resumen")
    assert r.status_code == 200 and r.json() == {"pendientes": 3, "portalesConError": 2}
