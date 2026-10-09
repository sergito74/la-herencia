"""Pruebas del detector de pagos sin factura — 036 (T010, funciones puras con fixtures; no escribe)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.features.revision_cuentas import datos, detector

FIXTURES = Path(__file__).parent / "fixtures"


def _cargar(nombre: str, clave: str | None = None) -> list[dict]:
    d = json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))
    if clave:
        d = d[clave]
    movs = d["movimientos"]
    for m in movs:
        m["fecha"] = date.fromisoformat(m["fecha"])
    return movs


def _mov(fecha: str, origen: str, id_origen: int, deuda: float = 0.0, credito: float = 0.0, nro: str | None = None) -> dict:
    return {"fecha": date.fromisoformat(fecha), "origen": origen, "idOrigen": id_origen, "deuda": deuda, "credito": credito,
            "nro": nro, "documento": origen}


# ---- Caso testigo: Jauregui y Morales antes del 09/10/2026

ESPERADOS_DESDE_2021 = {20000.04, 79114.02, 1563484.73, 30017.03, 33000.00, 39011.00, 43056.90, 46044.04}


@pytest.fixture(scope="module")
def jauregui() -> dict:
    return detector.detectar(_cargar("jauregui_antes.json"))


def test_jauregui_devuelve_exactamente_los_8_pagos_esperados(jauregui):
    desde_2021 = [p for p in jauregui["pagos"] if not p["anteriorA2021"]]
    assert {p["importe"] for p in desde_2021} == ESPERADOS_DESDE_2021
    assert len(desde_2021) == 8
    assert all(p["medio"] == "galicia" and p["lado"] == "proveedor" for p in desde_2021)


def test_el_pago_con_retencion_sugiere_la_suma_como_factura(jauregui):
    p = next(p for p in jauregui["pagos"] if p["importe"] == 1563484.73)
    assert p["retencionAsociada"] == 18515.27
    assert p["importeEsperadoFactura"] == 1582000.00
    # la retención no figura aparte
    assert not any(x["medio"] == "retencion" and not x["anteriorA2021"] for x in jauregui["pagos"])


def test_el_pago_cuya_retencion_esta_21_dias_antes_no_figura(jauregui):
    """10.594,55 del 06/01/2025 cubre la factura de 25.000,04 junto con la retención de 14.405,49 del 16/12/2024."""
    assert not any(abs(p["importe"] - 10594.55) < 0.01 for p in jauregui["pagos"])
    assert not any(abs(p["importe"] - 14405.49) < 0.01 for p in jauregui["pagos"])


def test_pago_que_cubre_muchas_facturas_no_figura_como_sin_factura(jauregui):
    """El pago de 80.541,43 del BNA de 2021 cubre más de 4 facturas seguidas: se empareja por FIFO parcial."""
    assert not any(abs(p["importe"] - 80541.43) < 0.01 for p in jauregui["pagos"])


def test_los_pagos_anteriores_a_2021_se_marcan_aparte(jauregui):
    for p in jauregui["pagos"]:
        assert p["anteriorA2021"] == (p["fecha"] < date(2021, 1, 1))
    assert any(p["anteriorA2021"] for p in jauregui["pagos"])


def test_fecha_esperada_es_un_rango_anterior_al_pago(jauregui):
    for p in jauregui["pagos"]:
        assert p["fechaEsperadaDesde"] <= p["fechaEsperadaHasta"] <= p["fecha"]


def test_consistencia_cierra_en_jauregui(jauregui):
    c = jauregui["consistencia"]
    assert c["cierra"] is True
    assert c["saldo"] == pytest.approx(1872239.81, abs=0.05)
    assert c["pagosSinFactura"] - c["facturasSinPago"] == pytest.approx(c["saldo"], abs=10)


def test_ningun_pago_de_tarjeta_figura_como_sin_factura(jauregui):
    assert not any(p["medio"] == "tarjetas" for p in jauregui["pagos"])


# ---- Casos sintéticos

def test_un_pago_de_tarjeta_empareja_con_su_factura():
    movs = [_mov("2024-03-01", "Compras", 1, deuda=1000.0, nro="A-1"), _mov("2024-03-20", "Tarjetas", 10, credito=1000.0)]
    r = detector.detectar(movs)
    assert r["pagos"] == [] and r["facturasSinPago"] == []


def test_un_pago_que_cubre_seis_facturas_se_empareja_por_fifo_con_el_resto_cubierto():
    movs = [_mov(f"2024-0{m}-10", "Compras", m, deuda=100.0, nro=f"A-{m}") for m in range(1, 7)]
    movs.append(_mov("2024-07-05", "Galicia", 50, credito=600.0))
    r = detector.detectar(movs)
    assert r["pagos"] == []
    assert r["facturasSinPago"] == []


def test_un_pago_sin_ninguna_factura_figura_con_el_importe_esperado():
    movs = [_mov("2025-05-27", "Galicia", 2578, credito=79114.02)]
    r = detector.detectar(movs)
    assert len(r["pagos"]) == 1
    p = r["pagos"][0]
    assert p["importe"] == 79114.02 and p["importeEsperadoFactura"] == 79114.02
    assert p["medio"] == "galicia" and p["idMovimiento"] == 2578 and p["confianza"] == "alta"


def test_una_retencion_cercana_se_suma_al_pago_sin_factura():
    movs = [_mov("2025-09-16", "Retenciones", 209, credito=100.0), _mov("2025-09-18", "Galicia", 2794, credito=900.0)]
    r = detector.detectar(movs)
    assert len(r["pagos"]) == 1
    assert r["pagos"][0]["retencionAsociada"] == 100.0 and r["pagos"][0]["importeEsperadoFactura"] == 1000.0
    assert not any(p["medio"] == "retencion" for p in r["pagos"])


def test_una_retencion_sin_pago_cercano_figura_sola():
    r = detector.detectar([_mov("2025-09-16", "Retenciones", 209, credito=100.0)])
    assert [p["medio"] for p in r["pagos"]] == ["retencion"]


def test_una_devolucion_del_proveedor_no_se_toma_como_cobro_de_cliente():
    """Crédito negativo en una cuenta de proveedor: funciona como documento del lado proveedor, no como cobro."""
    movs = [_mov("2020-01-10", "Pagos efectivo", 1, credito=-500.0), _mov("2020-01-12", "Banco Nacion", 2, credito=500.0)]
    r = detector.detectar(movs)
    assert all(p["lado"] == "proveedor" for p in r["pagos"])
    assert r["pagos"] == [] and r["facturasSinPago"] == []


def test_el_pago_de_una_factura_con_pago_posterior_a_siete_dias_no_se_empareja_con_facturas_futuras():
    movs = [_mov("2024-03-01", "Galicia", 1, credito=1000.0), _mov("2024-03-20", "Compras", 2, deuda=1000.0, nro="A-2")]
    r = detector.detectar(movs)
    assert len(r["pagos"]) == 1 and len(r["facturasSinPago"]) == 1


def test_el_saldo_inicial_antes_de_2011_se_informa_sin_apertura():
    r = detector.detectar([_mov("2010-04-19", "Ajuste Interno", 1, deuda=942.22)])
    assert r["consistencia"]["sinApertura"] is True
    assert detector.detectar([_mov("2012-04-19", "Compras", 1, deuda=10.0)])["consistencia"]["sinApertura"] is False


# ---- Traducción de origen a medio (data-model.md)

@pytest.mark.parametrize("origen,medio", [
    ("Banco Nacion", "bna"), ("Galicia", "galicia"), ("Pagos efectivo", "efectivo"), ("Tarjetas", "tarjetas"),
    ("Retenciones", "retencion"), ("Cobros Valores Recibidos", "valores"), ("Pagos Valores Recibidos", "valores"),
    ("Venta Granos", "venta-granos"),
])
def test_cada_origen_se_traduce_a_su_medio(origen, medio):
    assert datos.medio_de_origen(origen) == medio


def test_un_origen_desconocido_se_normaliza_con_minusculas_y_guiones():
    assert datos.medio_de_origen("Mercado Pago") == "mercado-pago"
    assert datos.medio_de_origen("Conciliación Tesorería") == "conciliacion-tesoreria"


# ---- Clientes y mixtas (US1 escenario 6, research D1)

def test_cuenta_de_cliente_con_cobros_cubiertos_por_liquidaciones_no_tiene_pagos_sin_factura():
    movs = _cargar("cliente_mixta.json", "cliente")
    assert datos.sentido_de_cuenta(movs) == "cliente"
    r = detector.detectar(movs)
    assert r["pagos"] == []
    assert r["facturasSinPago"] == []
    assert r["consistencia"]["cierra"] is True


def test_cuenta_mixta_separa_el_lado_proveedor_y_el_lado_cliente():
    movs = _cargar("cliente_mixta.json", "mixta")
    assert datos.sentido_de_cuenta(movs) == "mixta"
    r = detector.detectar(movs)
    lados = {p["lado"] for p in r["pagos"]} | {f["lado"] for f in r["facturasSinPago"]}
    assert lados <= {"proveedor", "cliente"}
    assert r["consistencia"]["cierra"] is True
