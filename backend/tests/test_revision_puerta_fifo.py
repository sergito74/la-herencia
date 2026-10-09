"""Pruebas de la puerta del FIFO — 036 (T039). El motor FIFO y la base están sustituidos: ninguna prueba simula ni aplica nada real."""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.features.recalculo_fifo import ejecuciones
from src.features.revision_cuentas import fichas
from src.main import app

CORTE = date(2026, 9, 30)
AUDITORIA = "/api/auditoria-cuentas"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _criterios_ctx(**cambios) -> dict:
    base = {"pagos_pendientes": 0, "pagos_importe_pendiente": 0.0, "pagos_antiguos": 0, "detector_cierra": True, "hallazgos": set(),
            "retenciones_sin_certificado": 0, "imputaciones": {"sanas": True}, "tiene_inventario": False, "reabierta": False,
            "referencia_access": {"tiene": True, "explica": True, "diferencia": 0.0}, "saldo_externo": None, "sin_estado": False, "saldo": 0.0}
    base.update(cambios)
    return {"criterios_ctx": base}


# ---- La puerta (función)

def test_una_cuenta_con_pagos_sin_factura_sin_decision_no_pasa_y_la_etapa_pendiente_es_e1(monkeypatch):
    monkeypatch.setattr(fichas, "corte_vigente", lambda: {"corte": CORTE})
    monkeypatch.setattr(fichas, "cargar_contextos", lambda corte, ids: {48: _criterios_ctx(pagos_pendientes=2, pagos_importe_pendiente=900.0)})
    p = fichas.puerta_fifo(48)
    assert p["puede"] is False and p["etapaPendiente"] == "E1" and p["criterios"][0]["codigo"] == "C1"
    assert "etapa E1" in fichas.mensaje_de_puerta(p)


def test_una_cuenta_que_cumple_e1_a_e4_pasa_aunque_no_tenga_inventario_ni_fifo(monkeypatch):
    monkeypatch.setattr(fichas, "corte_vigente", lambda: {"corte": CORTE})
    monkeypatch.setattr(fichas, "cargar_contextos", lambda corte, ids: {48: _criterios_ctx(hallazgos={"aplicacion-fuera-de-plazo"})})
    assert fichas.puerta_fifo(48)["puede"] is True


def test_el_doble_conteo_con_tarjeta_bloquea_en_e3(monkeypatch):
    monkeypatch.setattr(fichas, "corte_vigente", lambda: {"corte": CORTE})
    monkeypatch.setattr(fichas, "cargar_contextos", lambda corte, ids: {61: _criterios_ctx(hallazgos={"doble-descuento-tarjeta"})})
    p = fichas.puerta_fifo(61)
    assert p["puede"] is False and p["etapaPendiente"] == "E3"


def test_una_cuenta_sin_movimientos_hasta_el_corte_no_se_bloquea(monkeypatch):
    monkeypatch.setattr(fichas, "corte_vigente", lambda: {"corte": CORTE})
    monkeypatch.setattr(fichas, "cargar_contextos", lambda corte, ids: {})
    assert fichas.puerta_fifo(999)["puede"] is True


def test_la_puerta_de_varias_cuentas_se_calcula_por_lotes(monkeypatch):
    monkeypatch.setattr(fichas, "corte_vigente", lambda: {"corte": CORTE})
    llamadas: list = []
    monkeypatch.setattr(fichas, "cargar_contextos", lambda corte, ids: llamadas.append(ids) or {1: _criterios_ctx(), 2: _criterios_ctx(pagos_pendientes=1, pagos_importe_pendiente=5.0)})
    r = fichas.puerta_fifo_varias([1, 2])
    assert r[1]["puede"] is True and r[2]["puede"] is False and llamadas == [[1, 2]]


# ---- Los endpoints de la 035

def _cliente() -> httpx.AsyncClient:
    """Sesión de Administrador: el recálculo FIFO exige ese rol (el conftest de contrato no aplica fuera de tests/contract)."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t",
                             cookies={COOKIE_NAME: crear_token(id_usuario=0, rol="Administrador")})


@pytest.fixture
def motor(monkeypatch):
    """Motor FIFO sustituido: registra lo que se llamó. La puerta se controla desde cada prueba."""
    estado = {"simular": [], "aplicar": [], "revertir": []}

    def simular(alcance, usuario, hoy=None):
        estado["simular"].append(list(alcance))
        return {"idEjecucion": 900, "resumen": {"contactos": len(alcance)}}

    monkeypatch.setattr(ejecuciones, "simular", simular)
    monkeypatch.setattr(ejecuciones, "detalle", lambda i, c: {"contacto": {"idContacto": c}, "aplicaciones": []})
    monkeypatch.setattr(ejecuciones, "aplicar", lambda i, contactos, confirmar, usuario, hoy=None: estado["aplicar"].append(list(contactos)) or {"aplicados": contactos})
    monkeypatch.setattr(ejecuciones, "revertir", lambda i, usuario: estado["revertir"].append(i) or {"revertida": i})
    # los endpoints de la 035 dejan una entrada en el historial de la cuenta: con el motor sustituido tampoco se escribe ese historial
    from src.features.auditoria_cuentas import revision
    monkeypatch.setattr(revision, "registrar", lambda *a, **k: None)
    return estado


ABIERTA = {"puede": True, "etapaPendiente": None, "criterios": []}
CERRADA = {"puede": False, "etapaPendiente": "E1", "criterios": [{"codigo": "C1", "etapa": "E1", "cumple": False, "medido": "2 pagos sin factura por $ 900,00",
                                                                  "texto": "Hay pagos sin factura que los respalde", "evidencia": None}]}


@pytest.mark.anyio
async def test_simular_el_fifo_de_una_cuenta_bloqueada_devuelve_409_con_la_etapa_y_los_criterios(monkeypatch, motor):
    monkeypatch.setattr(fichas, "puerta_fifo", lambda id_contacto, corte=None: CERRADA)
    async with _cliente() as c:
        r = await c.post(f"{AUDITORIA}/cuentas/48/fifo/simular")
    assert r.status_code == 409
    b = r.json()
    assert b["etapaPendiente"] == "E1" and b["criterios"][0]["codigo"] == "C1" and "FIFO" in b["detail"]
    assert motor["simular"] == []                       # nunca llegó al motor


@pytest.mark.anyio
async def test_simular_el_fifo_de_una_cuenta_que_cumple_e1_a_e4_funciona_normalmente(monkeypatch, motor):
    monkeypatch.setattr(fichas, "puerta_fifo", lambda id_contacto, corte=None: ABIERTA)
    async with _cliente() as c:
        r = await c.post(f"{AUDITORIA}/cuentas/48/fifo/simular")
    assert r.status_code == 201 and motor["simular"] == [[48]]


@pytest.mark.anyio
async def test_aplicar_el_fifo_de_una_cuenta_bloqueada_devuelve_409(monkeypatch, motor):
    monkeypatch.setattr(fichas, "puerta_fifo", lambda id_contacto, corte=None: CERRADA)
    async with _cliente() as c:
        r = await c.post(f"{AUDITORIA}/cuentas/48/fifo/900/aplicar")
    assert r.status_code == 409 and motor["aplicar"] == []


@pytest.mark.anyio
async def test_revertir_no_tiene_puerta(monkeypatch, motor):
    monkeypatch.setattr(fichas, "puerta_fifo", lambda *a, **k: pytest.fail("revertir no consulta la puerta"))
    async with _cliente() as c:
        r = await c.post(f"{AUDITORIA}/cuentas/48/fifo/900/revertir")
    assert r.status_code == 200 and motor["revertir"] == [900]


@pytest.mark.anyio
async def test_la_tanda_omite_e_informa_las_cuentas_que_no_cumplen(monkeypatch, motor):
    monkeypatch.setattr(fichas, "puerta_fifo_varias", lambda ids, corte=None: {i: (ABIERTA if i != 2 else CERRADA) for i in ids})
    async with _cliente() as c:
        r = await c.post(f"{AUDITORIA}/fifo/tandas/simular", json={"contactos": [1, 2, 3]})
    assert r.status_code == 201
    b = r.json()
    assert motor["simular"] == [[1, 3]]
    assert [o["idContacto"] for o in b["omitidas"]] == [2] and b["omitidas"][0]["etapaPendiente"] == "E1"


@pytest.mark.anyio
async def test_una_tanda_donde_ninguna_cuenta_cumple_devuelve_409(monkeypatch, motor):
    monkeypatch.setattr(fichas, "puerta_fifo_varias", lambda ids, corte=None: {i: CERRADA for i in ids})
    async with _cliente() as c:
        r = await c.post(f"{AUDITORIA}/fifo/tandas/simular", json={"contactos": [1, 2]})
    assert r.status_code == 409 and motor["simular"] == []


@pytest.mark.anyio
async def test_aplicar_una_tanda_con_una_cuenta_que_ya_no_cumple_devuelve_409(monkeypatch, motor):
    monkeypatch.setattr(fichas, "puerta_fifo_varias", lambda ids, corte=None: {i: (CERRADA if i == 2 else ABIERTA) for i in ids})
    async with _cliente() as c:
        r = await c.post(f"{AUDITORIA}/fifo/tandas/900/aplicar", json={"contactos": [1, 2]})
    assert r.status_code == 409 and motor["aplicar"] == []
