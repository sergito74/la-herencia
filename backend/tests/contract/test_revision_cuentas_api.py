"""Contract tests for /api/revision-cuentas (036). Lecturas de solo lectura sobre WC; las escrituras se sustituyen
(nunca cambian el corte, las fichas ni las marcas reales de WC)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

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


# ---- Corte (T008)

@pytest.mark.anyio
async def test_corte_vigente_es_el_inicial_del_primer_cierre():
    r = await _get(f"{BASE}/corte")
    assert r.status_code == 200
    b = r.json()
    assert b["corte"] == "2026-09-30"
    assert b["usuario"] and b["fecha"]


@pytest.mark.anyio
async def test_cambiar_corte_crea_fila_nueva_y_no_sobrescribe(monkeypatch):
    from src.features.revision_cuentas import fichas

    llamadas = []

    def falso(corte, motivo, usuario):
        llamadas.append((corte, motivo, usuario))
        return {"corte": corte, "motivo": motivo, "usuario": usuario, "fecha": datetime(2026, 10, 9, 12, 0)}

    monkeypatch.setattr(fichas, "fijar_corte", falso)
    r = await _put(f"{BASE}/corte", {"corte": "2026-10-31", "motivo": "Cierre del mes 10"})
    assert r.status_code == 200
    assert r.json()["corte"] == "2026-10-31"
    assert llamadas and llamadas[0][0] == date(2026, 10, 31)


@pytest.mark.anyio
async def test_cambiar_corte_a_fecha_futura_devuelve_422(monkeypatch):
    from src.features.revision_cuentas import fichas

    monkeypatch.setattr(fichas, "_insertar_corte", lambda *a, **k: pytest.fail("no debe escribir con una fecha futura"))
    futura = (date.today() + timedelta(days=3)).isoformat()
    r = await _put(f"{BASE}/corte", {"corte": futura})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_rol_lectura_no_puede_cambiar_el_corte():
    r = await _put(f"{BASE}/corte", {"corte": "2026-10-31"}, rol="Lectura")
    assert r.status_code == 403


# ---- Pagos sin factura (T011)

CUENTA_JAUREGUI = 48


@pytest.fixture
def marcas_en_memoria(monkeypatch):
    """Sustituye la lectura y la escritura de marcas: ninguna prueba cambia las marcas reales de WC."""
    from src.features.revision_cuentas import evidencia

    guardadas: dict = {}
    llamadas: list = []

    def leer(id_contacto):
        return {k[1:]: v for k, v in guardadas.items() if k[0] == id_contacto}

    def guardar(id_contacto, medio, id_movimiento, estado, id_compra, fuente_respaldo, nota, usuario, tipo_venta=None, id_venta=None):
        marca = {"estado": estado, "nota": nota, "idCompra": id_compra, "fuenteRespaldo": fuente_respaldo, "tipoVenta": tipo_venta, "idVenta": id_venta,
                 "respaldo": f"venta de hacienda #{id_venta}" if tipo_venta else None}
        guardadas[(id_contacto, medio, id_movimiento)] = marca
        llamadas.append((id_contacto, medio, id_movimiento, estado, usuario))
        return marca

    monkeypatch.setattr(evidencia, "leer_marcas", leer)
    monkeypatch.setattr(evidencia, "guardar_marca", guardar)
    return guardadas


@pytest.mark.anyio
async def test_pagos_sin_factura_de_jauregui_tienen_la_forma_del_contrato(marcas_en_memoria):
    r = await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura")
    assert r.status_code == 200
    b = r.json()
    assert b["idContacto"] == CUENTA_JAUREGUI and b["corte"] == "2026-09-30"
    assert set(b["consistencia"]) >= {"pagosSinFactura", "facturasSinPago", "saldo", "cierra"}
    # con las 10 facturas ya cargadas no quedan pagos sin factura desde 2021; lo anterior se informa aparte
    assert [p for p in b["pagos"] if not p["anteriorA2021"]] == []
    assert b["consistencia"]["cierra"] is True
    for p in b["pagos"]:
        assert set(p) >= {"medio", "idMovimiento", "fecha", "importe", "importeEsperadoFactura", "fechaEsperadaDesde",
                          "fechaEsperadaHasta", "confianza", "anteriorA2021", "marca"}


@pytest.mark.anyio
async def test_pagos_sin_factura_de_una_cuenta_inexistente_devuelve_404(marcas_en_memoria):
    assert (await _get(f"{BASE}/cuentas/987654321/pagos-sin-factura")).status_code == 404


@pytest.mark.anyio
async def test_sin_documento_exige_nota(marcas_en_memoria):
    pago = (await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura")).json()["pagos"][0]
    r = await _put(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura/{pago['medio']}/{pago['idMovimiento']}", {"estado": "sin-documento"})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_factura_cargada_sin_archivo_exige_fuente_de_respaldo(marcas_en_memoria):
    pago = (await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura")).json()["pagos"][0]
    url = f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura/{pago['medio']}/{pago['idMovimiento']}"
    assert (await _put(url, {"estado": "factura-cargada"})).status_code == 422
    assert (await _put(url, {"estado": "factura-cargada", "fuenteRespaldo": "portal"})).status_code == 200


@pytest.mark.anyio
async def test_la_marca_se_conserva_en_el_siguiente_get(marcas_en_memoria):
    pago = (await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura")).json()["pagos"][0]
    url = f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura/{pago['medio']}/{pago['idMovimiento']}"
    r = await _put(url, {"estado": "sin-documento", "nota": "Cheque de 2015: no hay comprobante"})
    assert r.status_code == 200 and r.json()["marca"]["estado"] == "sin-documento"
    despues = (await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura")).json()["pagos"]
    marcado = next(p for p in despues if p["idMovimiento"] == pago["idMovimiento"] and p["medio"] == pago["medio"])
    assert marcado["marca"]["estado"] == "sin-documento"
    sin_marcados = (await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura", incluirMarcados="false")).json()["pagos"]
    assert not any(p["idMovimiento"] == pago["idMovimiento"] and p["medio"] == pago["medio"] for p in sin_marcados)


@pytest.mark.anyio
async def test_marcar_un_movimiento_inexistente_devuelve_404(marcas_en_memoria):
    r = await _put(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura/galicia/987654321", {"estado": "anticipo"})
    assert r.status_code == 404


@pytest.mark.anyio
async def test_rol_lectura_no_puede_marcar_pagos(marcas_en_memoria):
    r = await _put(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura/galicia/2794", {"estado": "anticipo"}, rol="Lectura")
    assert r.status_code == 403


# ---- Ficha, inventario y decisiones (T020, T023a)

@pytest.mark.anyio
async def test_ficha_de_jauregui_tiene_los_siete_criterios_y_no_escribe():
    r = await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/ficha")
    assert r.status_code == 200
    b = r.json()
    assert b["idContacto"] == CUENTA_JAUREGUI and b["corte"] == "2026-09-30" and b["razonSocial"]
    assert [c["codigo"] for c in b["criterios"]] == ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    assert b["etapa"] in {"E0", "E1", "E2", "E3", "E4", "E5", "E6"} and b["cola"] in set("ABCDEFGHI")
    assert b["estadoEfectivo"] in {"pendiente", "en-proceso", "esperando-evidencia", "esperando-sergio", "cerrada", "cerrada-con-excepcion", "reabierta"}
    assert b["saldoAlCorte"] == pytest.approx(-3.31, abs=0.01)
    c1 = next(c for c in b["criterios"] if c["codigo"] == "C1")
    assert c1["cumple"] is True       # con las 10 facturas cargadas ya no hay pagos sin factura desde 2021
    assert set(b) >= {"otrosProblemas", "antecedente035", "fifoAplicadoAntes", "pregunta", "cierre", "historial", "saldosExternos", "pagosSinFactura"}


@pytest.mark.anyio
async def test_ficha_de_una_cuenta_inexistente_devuelve_404():
    assert (await _get(f"{BASE}/cuentas/987654321/ficha")).status_code == 404


@pytest.mark.anyio
async def test_cerrar_una_cuenta_con_criterios_sin_cumplir_devuelve_409_con_la_lista():
    """Una cuenta de la cola D tiene pagos sin factura sin decisión: C1 no cumple y no se puede cerrar (devuelve 409 sin escribir nada).

    Jauregui ya está cerrada (09/10/2026): cerrarla otra vez SÍ escribiría, por eso se usa una cuenta que todavía tiene pendientes.
    """
    cuenta = (await _get(f"{BASE}/colas/D", tamano=1)).json()["cuentas"][0]["idContacto"]
    r = await _put(f"{BASE}/cuentas/{cuenta}/ficha", {"estado": "cerrada"})
    assert r.status_code == 409
    assert r.json()["criterios"] and all(c["cumple"] is False for c in r.json()["criterios"])
    assert "C1" in [c["codigo"] for c in r.json()["criterios"]]


@pytest.mark.anyio
async def test_cerrar_con_excepcion_sin_motivo_devuelve_422():
    r = await _put(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/ficha", {"estado": "cerrada-con-excepcion"})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_esperando_sergio_sin_pregunta_devuelve_422():
    assert (await _put(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/ficha", {"estado": "esperando-sergio"})).status_code == 422


@pytest.mark.anyio
async def test_cambiar_la_ficha_devuelve_la_ficha_actualizada(monkeypatch):
    from src.features.revision_cuentas import fichas

    base = (await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/ficha")).json()
    monkeypatch.setattr(fichas, "cambiar_estado", lambda id_contacto, cambio, usuario: {**base, "estado": cambio["estado"], "estadoEfectivo": cambio["estado"]})
    r = await _put(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/ficha", {"estado": "en-proceso", "nota": "Empece la revision"})
    assert r.status_code == 200 and r.json()["estado"] == "en-proceso"


@pytest.mark.anyio
async def test_rol_lectura_no_puede_cambiar_la_ficha():
    assert (await _put(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/ficha", {"estado": "en-proceso"}, rol="Lectura")).status_code == 403


@pytest.mark.anyio
async def test_inventario_vacio_devuelve_422():
    assert (await _put(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/ficha/inventario", {"fuentes": []})).status_code == 422


@pytest.mark.anyio
async def test_decisiones_exigen_texto_y_evidencia_para_descartar_el_access():
    assert (await _post(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/decisiones", {"tipo": "otro", "texto": ""})).status_code == 422
    r = await _post(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/decisiones", {"tipo": "descartar-access", "texto": "El Access esta mal"})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_registrar_y_listar_decisiones(monkeypatch):
    from src.features.revision_cuentas import fichas

    guardadas: list = []

    def registrar(id_contacto, tipo, texto, evid, usuario):
        d = {"idDecision": len(guardadas) + 1, "tipo": tipo, "texto": texto, "evidencia": evid, "usuario": usuario, "fecha": datetime(2026, 10, 9, 12, 0)}
        guardadas.append(d)
        return d

    monkeypatch.setattr(fichas, "registrar_decision", registrar)
    monkeypatch.setattr(fichas, "listar_decisiones", lambda id_contacto: list(reversed(guardadas)))
    r = await _post(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/decisiones",
                    {"tipo": "descartar-access", "texto": "El Access esta mal", "evidencia": "Estado de cuenta del proveedor al 09/10/2026"})
    assert r.status_code == 201 and r.json()["tipo"] == "descartar-access"
    lista = (await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/decisiones")).json()
    assert [d["texto"] for d in lista] == ["El Access esta mal"]


@pytest.mark.anyio
async def test_rol_lectura_no_puede_registrar_decisiones():
    r = await _post(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/decisiones", {"tipo": "otro", "texto": "x"}, rol="Lectura")
    assert r.status_code == 403


@pytest.mark.anyio
async def test_un_pago_se_respalda_con_una_venta_de_hacienda_y_la_ficha_lo_muestra(marcas_en_memoria, monkeypatch):
    from src.features.revision_cuentas import evidencia

    monkeypatch.setattr(evidencia, "fetch_one", lambda sql, params=(): {"x": 1})  # la venta existe y es de la cuenta
    pago = (await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura")).json()["pagos"][0]
    url = f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura/{pago['medio']}/{pago['idMovimiento']}"
    r = await _put(url, {"estado": "venta-cargada", "tipoVenta": "venta-hacienda", "idVenta": 67})
    assert r.status_code == 200
    marca = r.json()["marca"]
    assert marca["estado"] == "venta-cargada" and marca["tipoVenta"] == "venta-hacienda" and marca["idVenta"] == 67
    assert marca["respaldo"] == "venta de hacienda #67"


@pytest.mark.anyio
async def test_venta_cargada_sin_la_venta_devuelve_422(marcas_en_memoria):
    pago = (await _get(f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura")).json()["pagos"][0]
    url = f"{BASE}/cuentas/{CUENTA_JAUREGUI}/pagos-sin-factura/{pago['medio']}/{pago['idMovimiento']}"
    assert (await _put(url, {"estado": "venta-cargada"})).status_code == 422
    assert (await _put(url, {"estado": "venta-cargada", "tipoVenta": "venta-hacienda", "idVenta": 987654321})).status_code == 422  # no es de esta cuenta


@pytest.mark.anyio
async def test_las_ventas_de_la_cuenta_se_listan_para_elegir_el_respaldo(monkeypatch):
    from src.features.revision_cuentas import evidencia

    monkeypatch.setattr(evidencia, "ventas_de_cuenta", lambda i: [{"tipo": "venta-hacienda", "idVenta": 67, "fecha": date(2024, 5, 28), "numero": "00003-00000014",
                                                                    "rotulo": "venta de hacienda 00003-00000014"}])
    r = await _get(f"{BASE}/cuentas/551/ventas")
    assert r.status_code == 200
    assert r.json() == [{"tipo": "venta-hacienda", "idVenta": 67, "fecha": "2024-05-28", "numero": "00003-00000014", "rotulo": "venta de hacienda 00003-00000014"}]
