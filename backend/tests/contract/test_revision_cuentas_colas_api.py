"""Contract tests de colas y lotes de /api/revision-cuentas (036, T028).

Las colas leen WC sin escribir. Los lotes se guardan en memoria: ninguna prueba crea ni cambia correcciones, fichas o imputaciones reales.
"""

from __future__ import annotations

import httpx
import pytest

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.main import app

BASE = "/api/revision-cuentas"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _cliente(rol: str | None = None) -> httpx.AsyncClient:
    kwargs = {"cookies": {COOKIE_NAME: crear_token(id_usuario=0, rol=rol)}} if rol else {}
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", **kwargs)


async def _get(url: str, **params) -> httpx.Response:
    async with _cliente() as c:
        return await c.get(url, params=params or None)


async def _put(url: str, body: dict, rol: str | None = None) -> httpx.Response:
    async with _cliente(rol) as c:
        return await c.put(url, json=body)


async def _post(url: str, body: dict, rol: str | None = None) -> httpx.Response:
    async with _cliente(rol) as c:
        return await c.post(url, json=body)


# ---- Colas

@pytest.mark.anyio
async def test_cada_cuenta_esta_en_una_sola_cola_y_la_suma_es_el_total():
    totales = {}
    for cola in "ABCDEFGHI":
        r = await _get(f"{BASE}/colas/{cola}", tamano=100)
        assert r.status_code == 200
        totales[cola] = r.json()["total"]
    assert sum(totales.values()) >= 500           # las cuentas con movimientos, cada una en una sola cola
    a = (await _get(f"{BASE}/colas/A", tamano=100)).json()
    assert a["cola"] == "A" and a["total"] == totales["A"] and len(a["cuentas"]) == min(100, totales["A"])


@pytest.mark.anyio
async def test_la_cola_ordena_de_la_mas_facil_a_la_mas_compleja():
    cuentas = (await _get(f"{BASE}/colas/A", tamano=100)).json()["cuentas"]
    claves = [(c["movimientos"], abs(c["importe"])) for c in cuentas]
    assert claves == sorted(claves)
    for c in cuentas[:3]:
        assert set(c) >= {"idContacto", "razonSocial", "movimientos", "importe", "saldo", "moneda", "etapa", "estado", "otrosProblemas"}


@pytest.mark.anyio
async def test_la_cola_pagina_de_a_cien_como_maximo():
    p1 = (await _get(f"{BASE}/colas/A", tamano=5, pagina=1)).json()
    p2 = (await _get(f"{BASE}/colas/A", tamano=5, pagina=2)).json()
    assert len(p1["cuentas"]) == 5 and p2["pagina"] == 2
    assert not {c["idContacto"] for c in p1["cuentas"]} & {c["idContacto"] for c in p2["cuentas"]}
    assert (await _get(f"{BASE}/colas/A", tamano=101)).status_code == 422


@pytest.mark.anyio
async def test_una_cola_inexistente_devuelve_404():
    assert (await _get(f"{BASE}/colas/Z")).status_code == 404


@pytest.mark.anyio
async def test_las_reglas_de_lote_son_las_tres_del_primer_corte():
    reglas = {r["regla"]: r["cola"] for r in (await _get(f"{BASE}/reglas")).json()}
    assert reglas == {"aprobar-cierre": "A", "fifo-tandas": "B", "anular-doble-descuento": "C"}


# ---- Lotes

@pytest.fixture
def lotes_en_memoria(monkeypatch):
    from src.features.revision_cuentas import fichas, lotes

    est = {"corrs": {}, "n": 500, "cierres": []}

    def crear(cola, regla, parametros, cuentas, usuario):
        i = est["n"]
        est["n"] += 1
        est["corrs"][i] = {"idCorreccion": i, "regla": regla, "cola": cola, "estado": "simulada", "respaldo": None, "parametros": parametros,
                           "cuentas": [{"idContacto": c["idContacto"], "razonSocial": c["razonSocial"], "tildada": False, "cumple": c["cumple"],
                                        "saldoAntes": c["saldo"], "saldoDespues": c["saldo"], "detalle": "", "extra": c["extra"], "idsAplicacion": None}
                                       for c in cuentas]}
        return i

    def leer(i):
        if i not in est["corrs"]:
            raise lotes.LoteError(404, "El lote no existe")
        return est["corrs"][i]

    cuentas_falsas = [
        {"idContacto": 1, "razonSocial": "Uno", "saldo": 10.0, "cumple": True, "movimientos": 3, "importe": 5.0,
         "extra": {"cumple": True, "motivos": [], "evidencia": "access"}},
        {"idContacto": 2, "razonSocial": "Dos", "saldo": 0.0, "cumple": False, "movimientos": 9, "importe": 50.0,
         "extra": {"cumple": False, "motivos": ["C3: sin evidencia"], "evidencia": None}},
    ]
    monkeypatch.setattr(lotes, "_crear", crear)
    monkeypatch.setattr(lotes, "_leer", leer)
    monkeypatch.setattr(lotes, "_marcar_tildadas", lambda i, ids: [c.update(tildada=c["idContacto"] in ids) for c in est["corrs"][i]["cuentas"]])
    monkeypatch.setattr(lotes, "_poner_estado", lambda i, e, usuario=None, respaldo=None, aplicacion=False, reversion=False:
                        est["corrs"][i].update(estado=e, respaldo=respaldo or est["corrs"][i]["respaldo"]))
    monkeypatch.setattr(lotes, "_candidatas", lambda cola, regla, corte, usuario: (cuentas_falsas, {}))
    monkeypatch.setattr(lotes.datos, "saldos_al_corte", lambda corte: {1: 10.0, 2: 0.0})
    monkeypatch.setattr(lotes, "_aplicar_cierre", lambda lote, tildadas, corte, usuario: est["cierres"].append([c["idContacto"] for c in tildadas]))
    monkeypatch.setattr(fichas, "revertir_cierre_en_bloque", lambda i, tildadas, usuario: None)
    monkeypatch.setattr("src.features.vinculos.backup.backup_verificado", lambda etiqueta: f"respaldo-{etiqueta}.bak")
    return est


@pytest.mark.anyio
async def test_simular_un_lote_devuelve_201_con_ninguna_cuenta_tildada(lotes_en_memoria):
    r = await _post(f"{BASE}/lotes/simular", {"cola": "A", "regla": "aprobar-cierre"})
    assert r.status_code == 201
    b = r.json()
    assert b["estado"] == "simulada" and b["cola"] == "A" and all(c["tildada"] is False for c in b["cuentas"])


@pytest.mark.anyio
async def test_simular_con_una_regla_que_no_es_de_la_cola_devuelve_422(lotes_en_memoria):
    assert (await _post(f"{BASE}/lotes/simular", {"cola": "B", "regla": "aprobar-cierre"})).status_code == 422


@pytest.mark.anyio
async def test_tildar_todas_marca_solo_las_que_cumplen_y_se_puede_desmarcar(lotes_en_memoria):
    i = (await _post(f"{BASE}/lotes/simular", {"cola": "A", "regla": "aprobar-cierre"})).json()["idCorreccion"]
    t = (await _put(f"{BASE}/lotes/{i}/cuentas", {"tildarTodas": True})).json()
    assert [c["idContacto"] for c in t["cuentas"] if c["tildada"]] == [1]
    d = (await _put(f"{BASE}/lotes/{i}/cuentas", {"idsContacto": []})).json()
    assert not any(c["tildada"] for c in d["cuentas"])
    assert (await _put(f"{BASE}/lotes/{i}/cuentas", {"idsContacto": [2]})).status_code == 422    # la 2 no cumple la regla


@pytest.mark.anyio
async def test_aplicar_sin_cuentas_tildadas_devuelve_409(lotes_en_memoria):
    i = (await _post(f"{BASE}/lotes/simular", {"cola": "A", "regla": "aprobar-cierre"})).json()["idCorreccion"]
    assert (await _post(f"{BASE}/lotes/{i}/aplicar", {})).status_code == 409


@pytest.mark.anyio
async def test_aplicar_y_revertir_un_lote(lotes_en_memoria):
    i = (await _post(f"{BASE}/lotes/simular", {"cola": "A", "regla": "aprobar-cierre"})).json()["idCorreccion"]
    await _put(f"{BASE}/lotes/{i}/cuentas", {"tildarTodas": True})
    a = await _post(f"{BASE}/lotes/{i}/aplicar", {})
    assert a.status_code == 200 and a.json()["estado"] == "aplicada" and a.json()["respaldo"]
    assert lotes_en_memoria["cierres"] == [[1]]
    assert (await _post(f"{BASE}/lotes/{i}/aplicar", {})).status_code == 409           # ya aplicado
    assert (await _post(f"{BASE}/lotes/{i}/revertir", {})).json()["estado"] == "revertida"
    assert (await _post(f"{BASE}/lotes/{i}/revertir", {})).status_code == 409          # ya no está aplicado


@pytest.mark.anyio
async def test_descartar_un_lote_simulado_devuelve_204_y_uno_aplicado_409(lotes_en_memoria):
    i = (await _post(f"{BASE}/lotes/simular", {"cola": "A", "regla": "aprobar-cierre"})).json()["idCorreccion"]
    async with _cliente() as c:
        assert (await c.delete(f"{BASE}/lotes/{i}")).status_code == 204
        j = (await _post(f"{BASE}/lotes/simular", {"cola": "A", "regla": "aprobar-cierre"})).json()["idCorreccion"]
        await _put(f"{BASE}/lotes/{j}/cuentas", {"tildarTodas": True})
        await _post(f"{BASE}/lotes/{j}/aplicar", {})
        assert (await c.delete(f"{BASE}/lotes/{j}")).status_code == 409


@pytest.mark.anyio
async def test_rol_lectura_no_puede_aplicar_ni_simular_lotes(lotes_en_memoria):
    assert (await _post(f"{BASE}/lotes/simular", {"cola": "A", "regla": "aprobar-cierre"}, rol="Lectura")).status_code == 403
    assert (await _post(f"{BASE}/lotes/1/aplicar", {}, rol="Lectura")).status_code == 403


@pytest.mark.anyio
async def test_un_lote_inexistente_devuelve_404(lotes_en_memoria):
    assert (await _get(f"{BASE}/lotes/999999")).status_code == 404
