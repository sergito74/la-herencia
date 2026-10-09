"""Contract tests for /api/auditoria-cuentas (035, Historia 1). Solo lectura sobre WC."""

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
async def test_resumen_suma_todas_las_cuentas_en_sus_grupos():
    r = await _get("/api/auditoria-cuentas/resumen")
    assert r.status_code == 200
    b = r.json()
    assert sum(g["cuentas"] for g in b["causas"] if not g["adicional"]) == b["totalCuentas"]
    assert b["coinciden"] + b["conDiferencia"] == b["totalCuentas"]
    assert b["fechaCorte"] == "2026-09-25" and "25/09/2026" in b["avisoCorte"]
    por_causa = {g["causa"]: g for g in b["causas"]}
    for causa in ("coincide", "coincide-causa-conocida", "diferencia-menor-umbral"):
        if causa in por_causa:
            assert por_causa[causa]["excepcion"] is False
    assert b["parametros"] == {"plazoMaximoMeses": 24, "umbralPesos": 300, "anticipoDias": 60}


@pytest.mark.anyio
async def test_grupo_trae_las_cuentas_de_su_causa():
    b = (await _get("/api/auditoria-cuentas/resumen")).json()
    base = next(x for x in b["causas"] if not x["adicional"])
    g = (await _get(f"/api/auditoria-cuentas/grupos/{base['causa']}")).json()
    assert g["total"] == base["cuentas"]
    assert all(i["causa"] == base["causa"] for i in g["items"])


@pytest.mark.anyio
async def test_grupo_con_causa_desconocida_da_422():
    assert (await _get("/api/auditoria-cuentas/grupos/inventada")).status_code == 422


@pytest.mark.anyio
async def test_hallazgos_de_una_cuenta_y_cuenta_inexistente():
    otros = (await _get("/api/auditoria-cuentas/grupos/otros")).json()["items"]
    if otros:
        h = (await _get(f"/api/auditoria-cuentas/cuentas/{otros[0]['idContacto']}/hallazgos")).json()
        assert h["idContacto"] == otros[0]["idContacto"]
    assert (await _get("/api/auditoria-cuentas/cuentas/99999999/hallazgos")).status_code == 404


@pytest.mark.anyio
async def test_parametros_iniciales():
    p = (await _get("/api/auditoria-cuentas/parametros")).json()
    assert p["umbralPesos"] == 300 and p["anticipoDias"] == 60


@pytest.mark.anyio
async def test_casos_conocidos_aparecen_solos():
    b = (await _get("/api/auditoria-cuentas/resumen")).json()
    extras = {x["causa"]: x for x in b["causas"] if x["adicional"]}
    assert "aplicacion-fuera-de-plazo" in extras and "doble-descuento-tarjeta" in extras and extras["aplicacion-fuera-de-plazo"]["excepcion"]
    # Cargill (258): el movimiento 3240 de Galicia, aplicado a facturas desde 2019
    h = (await _get("/api/auditoria-cuentas/cuentas/258/hallazgos")).json()["hallazgos"]
    cargill = [x for x in h if x["causa"] == "aplicacion-fuera-de-plazo" and x.get("idMovimiento") == 3240 and x.get("medio") == "galicia"]
    assert cargill and cargill[0]["cantidadFacturas"] > 50 and cargill[0]["facturaMasVieja"] == "2019-05-07"
    # Doble descuento con tarjeta. Cooperativa (22) y Lartirigoyen (61) ya se corrigieron el 09/10/2026 (FIFO y anulación de imputaciones,
    # corrección 41): ya no figuran. Coto (465) sigue con el caso y lo encuentra solo.
    for contacto in (22, 61):
        hs = (await _get(f"/api/auditoria-cuentas/cuentas/{contacto}/hallazgos")).json()["hallazgos"]
        assert not any(x["causa"] == "doble-descuento-tarjeta" for x in hs)
    coto = (await _get("/api/auditoria-cuentas/cuentas/465/hallazgos")).json()["hallazgos"]
    assert any(x["causa"] == "doble-descuento-tarjeta" for x in coto)


@pytest.mark.anyio
async def test_el_grupo_adicional_trae_cuentas_aunque_el_saldo_coincida():
    g = (await _get("/api/auditoria-cuentas/grupos/aplicacion-fuera-de-plazo")).json()
    assert g["total"] > 0 and all("aplicacion-fuera-de-plazo" in i["causasExtra"] for i in g["items"])


async def _enviar(metodo: str, url: str, **kw) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        return await c.request(metodo, url, **kw)


@pytest.mark.anyio
async def test_reglas_conocidas_iniciales_y_validaciones_sin_escribir():
    lista = (await _get("/api/auditoria-cuentas/conocidos")).json()
    assert any(k["tipo"] == "concepto-movimiento" and k["clave"] == "LEY 25413" for k in lista)
    base = {"tipo": "concepto-movimiento", "clave": "LEY 25413", "motivo": "x"}
    assert (await _enviar("POST", "/api/auditoria-cuentas/conocidos", json=base)).status_code == 409           # ya existe
    assert (await _enviar("POST", "/api/auditoria-cuentas/conocidos", json={**base, "clave": "AB"})).status_code == 422  # muy corta
    assert (await _enviar("POST", "/api/auditoria-cuentas/conocidos", json={**base, "motivo": " "})).status_code == 422
    assert (await _enviar("POST", "/api/auditoria-cuentas/conocidos", json={"tipo": "cuenta", "clave": "315", "motivo": "x"})).status_code == 422  # falta la diferencia
    assert (await _enviar("POST", "/api/auditoria-cuentas/conocidos", json={**base, "tipo": "otro"})).status_code == 422
    assert (await _enviar("DELETE", "/api/auditoria-cuentas/conocidos/99999999")).status_code == 404


@pytest.mark.anyio
async def test_movimientos_sin_contacto_de_cualquier_monto_agrupados_por_concepto():
    b = (await _get("/api/auditoria-cuentas/resumen")).json()
    grupo = next((x for x in b["causas"] if x["causa"] == "movimiento-sin-contacto"), None)
    assert grupo is not None and grupo["movimientos"] > 0 and grupo["cuentas"] == 0
    g = (await _get("/api/auditoria-cuentas/grupos/movimiento-sin-contacto")).json()
    assert g["conceptos"] and sum(x["movimientos"] for x in g["conceptos"]) <= grupo["movimientos"]
    assert any(e["clave"] == "LEY 25413" and e["movimientos"] > 1000 for e in g["explicados"])


@pytest.mark.anyio
async def test_revision_de_una_cuenta_y_navegacion():
    sig = (await _get("/api/auditoria-cuentas/revision/siguiente")).json()
    assert sig and sig["idContacto"]
    r = (await _get(f"/api/auditoria-cuentas/cuentas/{sig['idContacto']}/revision")).json()
    assert r["estado"] in ("pendiente", "revisada", "revision-vieja") and r["dificultad"] in (0, 1, 2)
    assert r["totalCuentas"] > 100 and r["siguiente"] is None or r["siguiente"]["idContacto"] != sig["idContacto"]
    # la primera en el orden de trabajo es de las fáciles
    assert r["dificultad"] == 0
    assert (await _get("/api/auditoria-cuentas/cuentas/99999999/revision")).status_code == 404


@pytest.mark.anyio
async def test_revision_validaciones_sin_escribir():
    sig = (await _get("/api/auditoria-cuentas/revision/siguiente")).json()
    url = f"/api/auditoria-cuentas/cuentas/{sig['idContacto']}/revision"
    assert (await _enviar("PUT", url, json={"estado": "inventado"})).status_code == 422
    assert (await _enviar("PUT", url, json={"saldoEsperado": "mucho"})).status_code == 422
    assert (await _enviar("PUT", "/api/auditoria-cuentas/cuentas/99999999/revision", json={"estado": "revisada"})).status_code == 404


@pytest.mark.anyio
async def test_hallazgos_de_plazo_traen_los_ids_para_anular():
    h = (await _get("/api/auditoria-cuentas/cuentas/258/hallazgos")).json()["hallazgos"]
    plazo = [x for x in h if x["causa"] == "aplicacion-fuera-de-plazo"]
    assert plazo and all(x["idsAplicacion"] for x in plazo)


@pytest.mark.anyio
async def test_correcciones_validaciones_sin_escribir():
    base = "/api/auditoria-cuentas/cuentas/258"
    assert (await _enviar("POST", f"{base}/anular-aplicaciones", json={"idsAplicacion": [], "motivo": "x"})).status_code == 422
    assert (await _enviar("POST", f"{base}/anular-aplicaciones", json={"idsAplicacion": [1], "motivo": " "})).status_code == 422
    assert (await _enviar("POST", f"{base}/anular-aplicaciones", json={"idsAplicacion": [999999999], "motivo": "x"})).status_code == 409
    assert (await _enviar("POST", "/api/auditoria-cuentas/cuentas/99999999/anular-aplicaciones", json={"idsAplicacion": [1], "motivo": "x"})).status_code == 404
    assert (await _enviar("POST", "/api/auditoria-cuentas/correcciones/99999999/revertir")).status_code == 404
    assert (await _enviar("POST", f"{base}/nota-ajuste", json={"tipo": "otro", "fecha": "2026-01-01", "importe": 10, "motivo": "x"})).status_code == 422
    assert (await _enviar("POST", f"{base}/nota-ajuste", json={"tipo": "debito", "fecha": "2026-01-01", "importe": 0, "motivo": "x"})).status_code == 422
    assert (await _get(f"{base}/correcciones")).status_code == 200


@pytest.mark.anyio
async def test_movimientos_de_revision_muestran_cada_documento_en_su_moneda():
    r = (await _get("/api/auditoria-cuentas/cuentas/454/movimientos")).json()
    assert r["tieneDolares"] and abs(r["saldoPesos"]) < 1.0 and r["total"] == 2
    assert r["gobierna"] == "Dolares" and r["saldoGobierna"] == r["saldoDolares"] and abs(r["saldoGobierna"]) < 1.0
    pago = next(x for x in r["items"] if x["origenTipo"] != "Compras")
    factura = next(x for x in r["items"] if x["origenTipo"] == "Compras")
    assert pago["moneda"] == "Pesos" and pago["creditoPesos"] == 20952.45
    assert factura["moneda"] == "Dolares" and factura["tipoDeCambio"] == 96.69 and abs(factura["deudaPesos"] - 20952.45) < 0.01
    # una cuenta solo en pesos no cambia
    p = (await _get("/api/auditoria-cuentas/cuentas/12/movimientos?pageSize=5")).json()
    assert not p["tieneDolares"] and len(p["items"]) <= 5


@pytest.mark.anyio
async def test_revision_de_una_cuenta_en_dolares_usa_la_moneda_que_gobierna():
    r = (await _get("/api/auditoria-cuentas/cuentas/454/revision")).json()
    assert r["gobierna"] == "Dolares" and abs(r["saldo"]) < 1.0
    m = (await _get("/api/auditoria-cuentas/cuentas/61/movimientos?pageSize=1")).json()
    assert m["gobierna"] == "Mixta"


@pytest.mark.anyio
async def test_cuenta_en_dolares_con_diferencia_de_cambio_sugiere_la_nota():
    # Palaversich: los e-cheqs se entregaron el 24/04/2023; con el dólar de esa fecha quedan US$ 42 de diferencia (y no US$ 342)
    r = (await _get("/api/auditoria-cuentas/cuentas/440/revision")).json()
    av = next(a for a in r["avisos"] if a["tipo"] == "diferencia-de-cambio")
    assert av["sugerencia"]["moneda"] == "Dolares" and av["sugerencia"]["tipo"] == "credito"
    assert 30 < av["sugerencia"]["importe"] < 60 and av["sugerencia"]["tipoDeCambio"] > 1000
    assert r["dificultad"] == 2
    # Tierras de Henderson: el cheque se entregó el 10/06/2021, el día de la factura: queda en centavos y no hay aviso
    t = (await _get("/api/auditoria-cuentas/cuentas/450/revision")).json()
    assert not [a for a in t["avisos"] if a["tipo"] == "diferencia-de-cambio"]
    m = (await _get("/api/auditoria-cuentas/cuentas/450/movimientos")).json()
    assert any(x["fechaEntrega"] == "2021-06-10" for x in m["items"])


@pytest.mark.anyio
async def test_campo_y_tecnologia_ya_no_tiene_pagos_mal_imputados():
    """El 07/10/2026 se aplicó el FIFO a Campo y Tecnología (T-simulación 34): el saldo sigue en cero y el aviso de imputaciones incompletas desapareció."""
    r = (await _get("/api/auditoria-cuentas/cuentas/493/revision")).json()
    assert abs(r["saldo"]) < 10
    assert not any(a["tipo"] == "imputaciones-incompletas" for a in r["avisos"])


@pytest.mark.anyio
async def test_fifo_de_una_cuenta_exige_administrador_o_valida_sin_escribir():
    # sin usuario con rol Administrador la simulación se rechaza; con una cuenta inexistente la aplicación no existe
    r = await _enviar("POST", "/api/auditoria-cuentas/cuentas/493/fifo/simular")
    assert r.status_code in (201, 403, 409)    # 409: la puerta del FIFO (036) todavía no la deja pasar
    assert (await _enviar("POST", "/api/auditoria-cuentas/cuentas/493/fifo/99999999/aplicar")).status_code in (403, 404, 409)


@pytest.mark.anyio
async def test_asignacion_de_contacto_validaciones_sin_escribir():
    lista = (await _get("/api/auditoria-cuentas/movimientos-sin-contacto?limite=3")).json()
    assert lista and set(lista[0]) >= {"medio", "idMovimiento", "importe", "concepto"}
    url = "/api/auditoria-cuentas/movimientos-sin-contacto/asignar"
    assert (await _enviar("POST", url, json={"items": [], "idContacto": 61, "motivo": "x"})).status_code == 422
    assert (await _enviar("POST", url, json={"items": [{"medio": "bna", "idMovimiento": lista[0]["idMovimiento"]}], "idContacto": 61, "motivo": " "})).status_code == 422
    assert (await _enviar("POST", url, json={"items": [{"medio": "bna", "idMovimiento": 1}], "idContacto": 99999999, "motivo": "x"})).status_code == 404


@pytest.mark.anyio
async def test_plan_del_fifo_por_tandas_y_validaciones():
    p = (await _get("/api/auditoria-cuentas/fifo/plan")).json()
    assert p["base"]["resumen"]["contactos"] > 400 and p["tandas"] and p["excepciones"]
    assert all(t["estado"] in ("pendiente", "parcial", "aplicada") for t in p["tandas"])
    assert (await _enviar("POST", "/api/auditoria-cuentas/fifo/tandas/simular", json={"contactos": []})).status_code in (403, 422)
    assert (await _enviar("POST", "/api/auditoria-cuentas/fifo/tandas/99999999/aplicar", json={"contactos": [1]})).status_code in (403, 404)
