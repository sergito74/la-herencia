"""Contract tests de saldos externos de /api/revision-cuentas (036, T034).

El alta y la baja se sustituyen: ninguna prueba cambia saldos externos reales de WC.
"""

from __future__ import annotations

from datetime import date, timedelta

import httpx
import pytest

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.main import app

BASE = "/api/revision-cuentas"
CUENTA = 48


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _cliente(rol: str | None = None) -> httpx.AsyncClient:
    kwargs = {"cookies": {COOKIE_NAME: crear_token(id_usuario=0, rol=rol)}} if rol else {}
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", **kwargs)


@pytest.fixture
def saldos_en_memoria(monkeypatch):
    """Saldos externos guardados en memoria; la diferencia se calcula contra el saldo real de la cuenta a esa fecha."""
    from src.features.revision_cuentas import evidencia, router

    guardados: dict[int, dict] = {}

    def crear(id_contacto, fecha_saldo, saldo, moneda, fuente, referencia, nota, usuario):
        i = len(guardados) + 1
        guardados[i] = {"id": i, "idContacto": id_contacto, "fecha": fecha_saldo, "saldo": saldo, "moneda": moneda, "fuente": fuente,
                        "referencia": referencia, "nota": nota, "anulado": False}
        return i

    def anular(id_contacto, id_saldo, usuario):
        g = guardados.get(id_saldo)
        if g is None or g["idContacto"] != id_contacto or g["anulado"]:
            return False
        g["anulado"] = True
        return True

    def listar(id_contacto):
        salida = []
        for g in guardados.values():
            if g["idContacto"] != id_contacto or g["anulado"]:
                continue
            cuenta = -3.31                      # saldo de Jauregui al corte
            diferencia, clasificacion = evidencia.clasificar_saldo_externo(g["saldo"], cuenta, g["moneda"])
            salida.append({"idSaldoExterno": g["id"], "fechaSaldo": g["fecha"], "saldo": g["saldo"], "moneda": g["moneda"], "fuente": g["fuente"],
                           "referencia": g["referencia"], "nota": g["nota"], "saldoCuentaALaFecha": cuenta, "diferencia": diferencia, "clasificacion": clasificacion})
        return sorted(salida, key=lambda s: s["fechaSaldo"], reverse=True)

    monkeypatch.setattr(evidencia, "crear_saldo_externo", crear)
    monkeypatch.setattr(evidencia, "anular_saldo_externo", anular)
    monkeypatch.setattr(router, "_saldos_externos_de", listar)
    return guardados


@pytest.mark.anyio
async def test_los_saldos_externos_de_una_cuenta_sin_cargas_es_una_lista_vacia_con_la_forma_del_contrato():
    async with _cliente() as c:
        r = await c.get(f"{BASE}/cuentas/{CUENTA}/saldos-externos")
    assert r.status_code == 200 and isinstance(r.json(), list)


@pytest.mark.anyio
async def test_cargar_un_saldo_externo_lo_devuelve_con_la_diferencia_y_su_clasificacion(saldos_en_memoria):
    cuerpo = {"fechaSaldo": "2026-09-30", "saldo": 0.01, "moneda": "Pesos", "fuente": "portal", "referencia": "Estado de cuenta del proveedor, 09/10/2026"}
    async with _cliente() as c:
        r = await c.post(f"{BASE}/cuentas/{CUENTA}/saldos-externos", json=cuerpo)
        assert r.status_code == 201
        b = r.json()
        assert b["diferencia"] == -3.32 and b["clasificacion"] == "menor-al-umbral" and b["saldoCuentaALaFecha"] == -3.31
        lista = (await c.get(f"{BASE}/cuentas/{CUENTA}/saldos-externos")).json()
        assert [s["idSaldoExterno"] for s in lista] == [b["idSaldoExterno"]]


@pytest.mark.anyio
async def test_la_diferencia_grande_se_clasifica_con_diferencia(saldos_en_memoria):
    async with _cliente() as c:
        r = await c.post(f"{BASE}/cuentas/{CUENTA}/saldos-externos", json={"fechaSaldo": "2026-09-30", "saldo": 5000.0, "moneda": "Pesos", "fuente": "pdf"})
    assert r.json()["clasificacion"] == "con-diferencia"


@pytest.mark.anyio
async def test_sin_estado_exige_nota(saldos_en_memoria):
    async with _cliente() as c:
        r = await c.post(f"{BASE}/cuentas/{CUENTA}/saldos-externos", json={"fechaSaldo": "2026-09-30", "saldo": 0.0, "moneda": "Pesos", "fuente": "sin-estado"})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_sin_estado_con_nota_se_acepta_como_decision_de_no_pedir_el_estado(saldos_en_memoria):
    cuerpo = {"fechaSaldo": "2026-09-30", "saldo": 0.0, "moneda": "Pesos", "fuente": "sin-estado", "nota": "Movimientos de 2015: no se pide estado de cuenta"}
    async with _cliente() as c:
        assert (await c.post(f"{BASE}/cuentas/{CUENTA}/saldos-externos", json=cuerpo)).status_code == 201


@pytest.mark.anyio
async def test_la_fecha_futura_devuelve_422(saldos_en_memoria):
    futura = (date.today() + timedelta(days=5)).isoformat()
    async with _cliente() as c:
        r = await c.post(f"{BASE}/cuentas/{CUENTA}/saldos-externos", json={"fechaSaldo": futura, "saldo": 0.0, "moneda": "Pesos", "fuente": "portal"})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_una_fuente_desconocida_devuelve_422(saldos_en_memoria):
    async with _cliente() as c:
        r = await c.post(f"{BASE}/cuentas/{CUENTA}/saldos-externos", json={"fechaSaldo": "2026-09-30", "saldo": 0.0, "moneda": "Pesos", "fuente": "telepatia"})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_anular_un_saldo_externo_es_una_baja_logica_y_devuelve_204(saldos_en_memoria):
    async with _cliente() as c:
        b = (await c.post(f"{BASE}/cuentas/{CUENTA}/saldos-externos", json={"fechaSaldo": "2026-09-30", "saldo": 0.01, "moneda": "Pesos", "fuente": "portal"})).json()
        assert (await c.delete(f"{BASE}/cuentas/{CUENTA}/saldos-externos/{b['idSaldoExterno']}")).status_code == 204
        assert (await c.get(f"{BASE}/cuentas/{CUENTA}/saldos-externos")).json() == []
        assert (await c.delete(f"{BASE}/cuentas/{CUENTA}/saldos-externos/{b['idSaldoExterno']}")).status_code == 404
    assert saldos_en_memoria[1]["anulado"] is True              # la fila sigue existiendo: nunca se borra


@pytest.mark.anyio
async def test_anular_un_saldo_de_otra_cuenta_devuelve_404(saldos_en_memoria):
    async with _cliente() as c:
        b = (await c.post(f"{BASE}/cuentas/{CUENTA}/saldos-externos", json={"fechaSaldo": "2026-09-30", "saldo": 0.01, "moneda": "Pesos", "fuente": "portal"})).json()
        assert (await c.delete(f"{BASE}/cuentas/999/saldos-externos/{b['idSaldoExterno']}")).status_code == 404


@pytest.mark.anyio
async def test_rol_lectura_no_puede_cargar_ni_anular_saldos_externos(saldos_en_memoria):
    async with _cliente("Lectura") as c:
        assert (await c.post(f"{BASE}/cuentas/{CUENTA}/saldos-externos", json={"fechaSaldo": "2026-09-30", "saldo": 0.0, "moneda": "Pesos", "fuente": "portal"})).status_code == 403
        assert (await c.delete(f"{BASE}/cuentas/{CUENTA}/saldos-externos/1")).status_code == 403
