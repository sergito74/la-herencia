"""Contract tests de /api/descarga-peajes (037). Servicio, repositorio y
configuración simulados: no escribe en WC ni entra a portales."""

from __future__ import annotations

import httpx
import pytest

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.features.descarga_peajes import configuracion, repository, router, servicio
from src.main import app

EJECUCION = {"idEjecucion": 13, "origen": "manual", "usuario": "sergio", "inicio": "2026-10-16T10:00:00",
             "fin": None, "estado": "en_curso", "mensaje": None,
             "portales": [{"portal": "TelePASE", "estado": "ok", "nuevos": 1, "existentes": 23, "cargados": 1,
                           "pendientes": 0, "error": None}]}
DOCUMENTO = {"idDocumento": 101, "portal": "TelePASE", "proveedor": "AutopistasDelSol", "idContacto": 276,
             "fechaDocumento": "2026-10-16", "numeroDocumento": "0840-00811111", "totalImpreso": 4120.55,
             "ruta": r"C:\Users\x\Compras\04 2026 - 03 2027\20261016_AutopistasDelSol.pdf",
             "estadoCarga": "pendiente", "motivo": "No cierra", "idCompra": None, "idEjecucion": 13}


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.setattr(router, "get_usuario_por_id", lambda i: {"NombreUsuario": "sergio"})
    monkeypatch.setattr(repository, "revalidar_pendientes", lambda: 0)
    return httpx.ASGITransport(app=app)


async def _req(transport, method, url, cookies=None):
    kwargs = {"cookies": cookies} if cookies is not None else {}
    async with httpx.AsyncClient(transport=transport, base_url="http://test", **kwargs) as ac:
        return await ac.request(method, url)


# --- US1 ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_iniciar_devuelve_202(transport, monkeypatch):
    monkeypatch.setattr(servicio, "iniciar_en_segundo_plano", lambda u: (13, None))
    r = await _req(transport, "POST", "/api/descarga-peajes/ejecuciones")
    assert r.status_code == 202 and r.json() == {"idEjecucion": 13}


@pytest.mark.anyio
async def test_iniciar_con_otra_en_curso_devuelve_409(transport, monkeypatch):
    monkeypatch.setattr(servicio, "iniciar_en_segundo_plano", lambda u: (None, 12))
    r = await _req(transport, "POST", "/api/descarga-peajes/ejecuciones")
    assert r.status_code == 409 and r.json()["idEjecucion"] == 12


@pytest.mark.anyio
async def test_iniciar_con_rol_lectura_devuelve_403(transport, monkeypatch):
    llamado = []
    monkeypatch.setattr(servicio, "iniciar_en_segundo_plano", lambda u: llamado.append(u) or (1, None))
    cookies = {COOKIE_NAME: crear_token(id_usuario=5, rol="Lectura")}
    r = await _req(transport, "POST", "/api/descarga-peajes/ejecuciones", cookies=cookies)
    assert r.status_code == 403 and not llamado


@pytest.mark.anyio
async def test_detalle_ejecucion(transport, monkeypatch):
    monkeypatch.setattr(repository, "obtener_ejecucion", lambda i: {**EJECUCION, "documentos": [DOCUMENTO]})
    r = await _req(transport, "GET", "/api/descarga-peajes/ejecuciones/13")
    assert r.status_code == 200
    body = r.json()
    assert body["portales"][0]["existentes"] == 23
    assert body["documentos"][0]["nombreArchivo"] == "20261016_AutopistasDelSol.pdf"


@pytest.mark.anyio
async def test_detalle_inexistente_404(transport, monkeypatch):
    monkeypatch.setattr(repository, "obtener_ejecucion", lambda i: None)
    assert (await _req(transport, "GET", "/api/descarga-peajes/ejecuciones/999")).status_code == 404


# --- US2 ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_documentos_filtra_y_valida_estado(transport, monkeypatch):
    monkeypatch.setattr(repository, "listar_documentos", lambda e, l, d: ([DOCUMENTO], 1))
    r = await _req(transport, "GET", "/api/descarga-peajes/documentos?estado=pendiente")
    assert r.status_code == 200 and r.json()["total"] == 1
    assert (await _req(transport, "GET", "/api/descarga-peajes/documentos?estado=otro")).status_code == 400


# --- US3 ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_historial_paginado(transport, monkeypatch):
    recibido = {}

    def listar(limite, desde):
        recibido.update(limite=limite, desde=desde)
        return [EJECUCION], 40
    monkeypatch.setattr(repository, "listar_ejecuciones", listar)
    r = await _req(transport, "GET", "/api/descarga-peajes/ejecuciones?limite=20&desde=20")
    assert r.status_code == 200 and r.json()["total"] == 40 and recibido == {"limite": 20, "desde": 20}
    assert (await _req(transport, "GET", "/api/descarga-peajes/ejecuciones?limite=500")).status_code == 422


# --- US4 ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_estado_solo_expone_booleanos(transport, monkeypatch):
    monkeypatch.setattr(configuracion, "credencial", lambda p: ("usuario-secreto", "clave-secreta"))
    monkeypatch.setattr(configuracion, "estado_tarea",
                        lambda: {"instalada": True, "proximaCorrida": "2026-10-19T09:00:00", "ultimoResultado": "0"})
    monkeypatch.setattr(repository, "ejecucion_en_curso", lambda: None)
    r = await _req(transport, "GET", "/api/descarga-peajes/estado")
    assert r.status_code == 200
    assert "secreto" not in r.text and "secreta" not in r.text
    body = r.json()
    assert [p["credenciales"] for p in body["portales"]] == [True] * 4
    assert body["tarea"]["proximaCorrida"] == "2026-10-19T09:00:00" and body["enCurso"] is None


@pytest.mark.anyio
async def test_resumen_contador(transport, monkeypatch):
    monkeypatch.setattr(repository, "resumen", lambda: {"pendientes": 2, "portalesConError": 1})
    r = await _req(transport, "GET", "/api/descarga-peajes/resumen")
    assert r.json() == {"pendientes": 2, "portalesConError": 1}
