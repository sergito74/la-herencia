"""Tests del motor FIFO (032, quickstart §1). Datos sintéticos, sin base."""

from __future__ import annotations

from datetime import date

from src.features.recalculo_fifo import motor

HOY = date(2026, 10, 1)


def doc(id_, fecha, importe, lado="D", origen="Compras", venc=None, nro=None, moneda="ARS", tc=None,
        cuota=None, suspendido=False):
    return {"clave": (origen, id_, cuota), "lado": lado, "clase": "doc", "fecha": fecha,
            "vencimiento": venc or fecha, "nro": nro or str(id_), "moneda": moneda, "importe": importe,
            "tcDoc": tc, "suspendido": suspendido, "ajustaTc": False}


def pago(id_, fecha, importe, lado="C", origen="Banco Nacion"):
    return {"clave": (origen, id_, None), "lado": lado, "clase": "dinero", "fecha": fecha, "vencimiento": fecha,
            "nro": str(id_), "moneda": "ARS", "importe": importe, "tcDoc": None, "suspendido": False,
            "ajustaTc": False}


def sin_tc(_fecha):
    return None


def tc_fijo(valor):
    return lambda _fecha: valor


def aplicado(res, debito_id):
    return round(sum(a["importeAplicado"] for a in res["aplicaciones"] if a["debito"][1] == debito_id), 2)


def test_fifo_cubre_el_vencimiento_mas_antiguo():
    items = [doc(1, date(2024, 1, 10), 100), doc(2, date(2024, 1, 5), 100), pago(9, date(2024, 2, 1), 150)]
    res = motor.recalcular(items, [], sin_tc, HOY)
    assert aplicado(res, 2) == 100 and aplicado(res, 1) == 50


def test_desempate_por_numero_de_comprobante():
    items = [doc(1, date(2024, 1, 5), 100, nro="0002"), doc(2, date(2024, 1, 5), 100, nro="0001"),
             pago(9, date(2024, 2, 1), 100)]
    res = motor.recalcular(items, [], sin_tc, HOY)
    assert aplicado(res, 2) == 100 and aplicado(res, 1) == 0


def test_anticipo_cubre_factura_posterior_y_largo_queda_marcado():
    items = [pago(9, date(2024, 1, 1), 100), doc(1, date(2024, 1, 20), 50), doc(2, date(2024, 5, 1), 50)]
    res = motor.recalcular(items, [], sin_tc, HOY)
    reglas = {a["debito"][1]: a["regla"] for a in res["aplicaciones"]}
    assert reglas == {1: "anticipo", 2: "anticipo"}
    assert "anticipo-largo" in res["marcas"]


def test_cuotas_en_orden():
    items = [doc(1, date(2024, 1, 1), 50, venc=date(2024, 3, 1), cuota=2),
             doc(1, date(2024, 1, 1), 50, venc=date(2024, 2, 1), cuota=1), pago(9, date(2024, 2, 5), 60)]
    res = motor.recalcular(items, [], sin_tc, HOY)
    por_cuota = {a["debito"][2]: a["importeAplicado"] for a in res["aplicaciones"]}
    assert por_cuota == {1: 50, 2: 10}


def test_cadena_parcial_y_fifo_del_resto():
    items = [doc(1, date(2024, 1, 1), 100), pago(7, date(2024, 1, 2), 30, origen="Tarjetas"),
             pago(9, date(2024, 1, 3), 70)]
    fijos = [{"credito": ("Tarjetas", 7), "debito": ("Compras", 1), "importe": 30, "regla": "cadena"}]
    res = motor.recalcular(items, fijos, sin_tc, HOY)
    assert aplicado(res, 1) == 100
    assert {a["regla"] for a in res["aplicaciones"]} == {"cadena", "fifo"}


def test_eleccion_explicita_se_respeta():
    items = [doc(1, date(2024, 1, 1), 100), doc(2, date(2024, 2, 1), 100), pago(9, date(2024, 3, 1), 100)]
    fijos = [{"credito": ("Banco Nacion", 9), "debito": ("Compras", 2), "importe": 100, "regla": "eleccion"}]
    res = motor.recalcular(items, fijos, sin_tc, HOY)
    assert aplicado(res, 2) == 100 and aplicado(res, 1) == 0
    assert "manual-ajustado" not in res["marcas"]


def test_eleccion_que_sobreaplica_reasigna_exceso_y_marca():
    items = [doc(1, date(2024, 1, 1), 100), doc(2, date(2024, 2, 1), 40), pago(9, date(2024, 3, 1), 100)]
    fijos = [{"credito": ("Banco Nacion", 9), "debito": ("Compras", 2), "importe": 100, "regla": "eleccion"}]
    res = motor.recalcular(items, fijos, sin_tc, HOY)
    assert aplicado(res, 2) == 40 and aplicado(res, 1) == 60
    assert "manual-ajustado" in res["marcas"]


def test_factura_suspendida_se_saltea():
    items = [doc(1, date(2024, 1, 1), 100, suspendido=True), doc(2, date(2024, 2, 1), 100),
             pago(9, date(2024, 3, 1), 100)]
    res = motor.recalcular(items, [], sin_tc, HOY)
    assert aplicado(res, 1) == 0 and aplicado(res, 2) == 100


def test_nota_credito_con_origen_va_primero_a_su_factura():
    items = [doc(1, date(2024, 1, 1), 100), doc(2, date(2024, 2, 1), 100),
             doc(3, date(2024, 2, 10), 30, lado="C"), pago(9, date(2024, 3, 1), 170)]
    fijos = [{"credito": ("Compras", 3), "debito": ("Compras", 2), "importe": 30, "regla": "nota-origen"}]
    res = motor.recalcular(items, fijos, sin_tc, HOY)
    assert aplicado(res, 2) == 100 and aplicado(res, 1) == 100
    assert any(a["regla"] == "nota-origen" and a["debito"][1] == 2 for a in res["aplicaciones"])


def test_documento_usd_pagado_en_pesos_con_diferencia_de_cambio():
    items = [doc(1, date(2024, 1, 1), 100, moneda="USD", tc=1000), pago(9, date(2024, 3, 1), 110000)]
    res = motor.recalcular(items, [], tc_fijo(1100), HOY)
    a = res["aplicaciones"][0]
    assert a["importeAplicado"] == 100 and a["moneda"] == "USD"
    assert a["importeArs"] == 110000 and a["tipoCambio"] == 1100
    assert a["diferenciaCambio"] == 10000
    assert res["pendienteDebitos"] == 0


def test_compensacion_cruzada_en_usd():
    items = [doc(1, date(2024, 1, 1), 100, moneda="USD", tc=1000),
             doc(5, date(2024, 4, 1), 55000, lado="C", origen="Venta Granos")]
    res = motor.recalcular(items, [], tc_fijo(1100), HOY)
    a = res["aplicaciones"][0]
    assert a["regla"] == "compensacion" and a["importeAplicado"] == 50 and a["moneda"] == "USD"


def test_pago_de_mas_sin_factura_posterior_es_excepcion():
    items = [doc(1, date(2024, 1, 1), 100), pago(9, date(2024, 2, 1), 150)]
    res = motor.recalcular(items, [], sin_tc, HOY)
    assert res["anticipoAbierto"] == 50
    assert "pago-de-mas" in res["marcas"]


def test_anticipo_reciente_no_es_excepcion():
    items = [pago(9, date(2026, 9, 20), 100)]
    res = motor.recalcular(items, [], sin_tc, HOY)
    assert res["anticipoAbierto"] == 100 and "pago-de-mas" not in res["marcas"]


def test_idempotencia_misma_huella():
    items = [doc(1, date(2024, 1, 1), 100), doc(2, date(2024, 2, 1), 80), pago(9, date(2024, 3, 1), 150)]
    h1 = motor.recalcular([dict(i) for i in items], [], sin_tc, HOY)["huella"]
    h2 = motor.recalcular(list(reversed([dict(i) for i in items])), [], sin_tc, HOY)["huella"]
    assert h1 == h2 and len(h1) == 64


def test_cuenta_mixta_compensa_documentos_antes_que_dinero():
    # Compra 100 (D), venta 60 (C), pago nuestro 40 (C), cobro de ellos 10 (D).
    items = [doc(1, date(2024, 1, 1), 100), pago(9, date(2024, 1, 2), 40),
             doc(5, date(2024, 2, 1), 60, lado="C", origen="Venta Granos"),
             pago(8, date(2024, 2, 2), 10, lado="D")]
    res = motor.recalcular(items, [], sin_tc, HOY)
    reglas = sorted((a["regla"], a["importeAplicado"]) for a in res["aplicaciones"])
    assert reglas == [("compensacion", 60), ("fifo", 40)]
    assert res["anticipoAbierto"] == 10


def test_compra_pagada_y_venta_posterior_cobrada_no_se_cruzan():
    # 2014: compra 100 pagada en efectivo. 2016: venta 80 cobrada por banco.
    items = [doc(1, date(2014, 3, 1), 100), pago(9, date(2014, 3, 5), 100, origen="Pagos efectivo"),
             doc(5, date(2016, 5, 1), 80, lado="C", origen="Venta Granos"), pago(8, date(2016, 5, 10), 80, lado="D")]
    res = motor.recalcular(items, [], sin_tc, HOY)
    pares = sorted((a["debito"][0], a["credito"][0], a["regla"]) for a in res["aplicaciones"])
    assert pares == [("Compras", "Pagos efectivo", "fifo"), ("Venta Granos", "Banco Nacion", "fifo")]
    assert "reintegro" not in res["marcas"]


def test_tc_del_anticipo_es_el_del_dia_anterior_al_pago():
    vistos = []
    def tc(fecha):
        vistos.append(fecha)
        return 1000.0
    items = [pago(9, date(2024, 1, 10), 100000), doc(1, date(2024, 2, 1), 100, moneda="USD", tc=900)]
    motor.recalcular(items, [], tc, HOY)
    assert vistos[0] == date(2024, 1, 9)


def test_proveedor_con_nota_de_ajuste_usa_tc_de_factura():
    factura = doc(1, date(2021, 2, 17), 822.80, moneda="USD", tc=88.54)
    factura["usarTcDoc"] = True
    nd = doc(2, date(2021, 6, 11), 5422.25)
    items = [factura, nd, pago(9, date(2021, 6, 11), 78272.96)]
    res = motor.recalcular(items, [], tc_fijo(95.13), HOY)
    assert res["pendienteDebitos"] == 0 and res["anticipoAbierto"] == 0
