"""Contract tests de /api/recalculo-fifo (032, contracts/api.md).

Solo lectura sobre WC: usan la última ejecución guardada y comprueban que
un usuario sin rol Administrador no pueda simular. Si todavía no hay
ninguna ejecución, los tests de lectura se saltean.
"""

from __future__ import annotations

import httpx
import pytest

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.main import app

BASE = "/api/recalculo-fifo"


def _cliente(**kwargs) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", **kwargs)


@pytest.mark.anyio
async def test_lectura_de_la_ultima_ejecucion():
    async with _cliente() as c:
        r = await c.get(f"{BASE}/ejecuciones")
        assert r.status_code == 200
        ejecuciones = r.json()
        if not ejecuciones:
            pytest.skip("No hay ejecuciones guardadas")
        id_ej = ejecuciones[0]["idEjecucion"]
        r = await c.get(f"{BASE}/ejecuciones/{id_ej}/contactos", params={"filtro": "todos", "tamanio": 5})
        assert r.status_code == 200
        cuerpo = r.json()
        assert {"items", "total", "pagina", "tamanio"} <= cuerpo.keys()
        if cuerpo["items"]:
            item = cuerpo["items"][0]
            assert {"idContacto", "cerrabaAntes", "cierraDespues", "tendencia", "controles", "marcas"} <= item.keys()
            r = await c.get(f"{BASE}/ejecuciones/{id_ej}/contactos/{item['idContacto']}")
            assert r.status_code == 200
            assert {"contacto", "renglones", "aplicaciones"} <= r.json().keys()


@pytest.mark.anyio
async def test_filtro_invalido_responde_422():
    async with _cliente() as c:
        r = await c.get(f"{BASE}/ejecuciones/1/contactos", params={"filtro": "cualquiera"})
        assert r.status_code == 422


@pytest.mark.anyio
async def test_ejecucion_inexistente_responde_404():
    async with _cliente() as c:
        r = await c.get(f"{BASE}/ejecuciones/999999999")
        assert r.status_code == 404


@pytest.mark.anyio
async def test_simular_exige_administrador():
    cookies = {COOKIE_NAME: crear_token(id_usuario=0, rol="Consulta")}
    async with _cliente(cookies=cookies) as c:
        r = await c.post(f"{BASE}/ejecuciones", json={"alcance": [340]})
        assert r.status_code == 403


@pytest.mark.anyio
async def test_aplicar_y_revertir_exigen_administrador():
    cookies = {COOKIE_NAME: crear_token(id_usuario=0, rol="Consulta")}
    async with _cliente(cookies=cookies) as c:
        assert (await c.post(f"{BASE}/ejecuciones/1/aplicar", json={})).status_code == 403
        assert (await c.post(f"{BASE}/ejecuciones/1/revertir")).status_code == 403


@pytest.mark.anyio
async def test_aplicar_una_ejecucion_descartada_responde_409():
    async with _cliente() as c:
        ejecuciones = (await c.get(f"{BASE}/ejecuciones")).json()
        descartadas = [e for e in ejecuciones if e["estado"] in ("descartada", "revertida")]
        if not descartadas:
            pytest.skip("No hay ejecuciones descartadas")
        r = await c.post(f"{BASE}/ejecuciones/{descartadas[0]['idEjecucion']}/aplicar", json={})
        assert r.status_code == 409


@pytest.fixture
def anyio_backend():
    return "asyncio"
