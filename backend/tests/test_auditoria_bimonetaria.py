"""Cuentas con documentos en dólares y en pesos: un solo criterio — 035 (FR-024). Fixtures puros y lectura de ArPov."""

from datetime import date

from src.features.auditoria_cuentas import bimonetaria as b

SERIE = {date(2021, 8, 16): 98.0, date(2021, 7, 30): 97.0, date(2021, 8, 2): 97.5}


def _fila(fecha, documento, nro, deuda, credito, origen, id_origen):
    return {"Fecha": fecha, "Documento": documento, "Nro Documento": nro, "Deuda": deuda, "Credito": credito, "Origen": origen, "IdOrigen": id_origen}


def test_cotizacion_del_dia_anterior():
    c = b.CotizacionBNA(SERIE)
    assert c.dia_anterior(date(2021, 8, 17)) == 98.0
    assert c.dia_anterior(date(2021, 8, 16)) == 97.5       # la del día anterior, no la del mismo día
    assert c.dia_anterior(date(2021, 7, 1)) is None
    assert c.dia_anterior(None) is None


def test_factura_en_dolares_y_pago_en_pesos_cierran_en_pesos():
    filas = [_fila(date(2021, 8, 1), "Factura", "F1", 216.6972, 0, "Compras", 1),
             _fila(date(2021, 8, 17), "Resumen Bancario", "R1", 0, 20952.45, "Galicia", 7)]
    r = b.construir(filas, {1: {"moneda": "Dolares", "tc": 96.69}}, b.CotizacionBNA(SERIE))
    assert r["saldoPesos"] == 0.0 and r["tieneDolares"] and not r["bimonetaria"]
    assert r["filas"][0]["moneda"] == "Dolares" and r["filas"][0]["deudaPesos"] == 20952.45
    assert r["filas"][1]["moneda"] == "Pesos" and r["filas"][1]["creditoPesos"] == 20952.45       # el pago NO es en dólares
    # en dólares: el pago se divide por el dólar BNA del día anterior; la diferencia es diferencia de cambio
    assert round(r["saldoDolares"], 2) == round(-216.6972 + 20952.45 / 98.0, 2)


def test_cuenta_bimonetaria_con_documentos_en_las_dos_monedas():
    filas = [_fila(date(2021, 8, 1), "Factura", "F1", 100.0, 0, "Compras", 1),
             _fila(date(2021, 8, 2), "Factura", "F2", 5000.0, 0, "Compras", 2),
             _fila(date(2021, 8, 17), "Pago", "P", 0, 15000.0, "Galicia", 7)]
    r = b.construir(filas, {1: {"moneda": "Dolares", "tc": 100.0}, 2: {"moneda": "Pesos", "tc": 1}}, b.CotizacionBNA(SERIE))
    assert r["bimonetaria"] is True
    assert r["saldoPesos"] == 0.0            # 100 US$ x 100 + 5.000 $ = 15.000 $
    assert [f["saldoPesos"] for f in r["filas"]] == [-10000.0, -15000.0, 0.0]


def test_documento_en_dolares_sin_tipo_de_cambio_usa_el_bna_y_avisa():
    filas = [_fila(date(2021, 8, 17), "Factura", "SIN-TC", 10.0, 0, "Compras", 1)]
    r = b.construir(filas, {1: {"moneda": "Dolares", "tc": 1.0}}, b.CotizacionBNA(SERIE))
    assert r["filas"][0]["tcEstimado"] is True and r["filas"][0]["tipoDeCambio"] == 98.0 and r["filas"][0]["deudaPesos"] == 980.0
    assert r["avisos"] and "no tiene tipo de cambio" in r["avisos"][0]


def test_cuenta_solo_en_pesos_no_cambia():
    filas = [_fila(date(2021, 8, 1), "Factura", "F1", 1000.0, 0, "Compras", 1), _fila(date(2021, 8, 5), "Pago", "P", 0, 400.0, "Banco Nacion", 3)]
    r = b.construir(filas, {1: {"moneda": "Pesos", "tc": 1.0}}, b.CotizacionBNA(SERIE))
    assert not r["tieneDolares"] and r["saldoPesos"] == -600.0 and [f["saldoPesos"] for f in r["filas"]] == [-1000.0, -600.0]


def test_arpov_en_la_base_real_cierra_en_pesos():
    r = b.cargar_cuenta(454)
    assert abs(r["saldoPesos"]) < 1.0 and r["tieneDolares"]
    assert [f["moneda"] for f in r["filas"]] == ["Dolares", "Pesos"]


def test_moneda_que_gobierna():
    f = lambda n: [_fila(date(2021, 8, 1), "Factura", "F", 10.0, 0, "Compras", i) for i in range(1, n + 1)]
    usd = {"moneda": "Dolares", "tc": 100.0, "ajusta": False}
    pesos = {"moneda": "Pesos", "tc": 1.0, "ajusta": False}
    nota = {"moneda": "Pesos", "tc": 1.0, "ajusta": True}
    sin_tc = b.CotizacionBNA(SERIE)
    assert b.construir(f(2), {1: usd, 2: usd}, sin_tc)["gobierna"] == "Dolares"
    assert b.construir(f(2), {1: pesos, 2: pesos}, sin_tc)["gobierna"] == "Pesos"
    assert b.construir(f(2), {1: usd, 2: pesos}, sin_tc)["gobierna"] == "Mixta"
    # una nota de ajuste de tipo de cambio en pesos no vuelve mixta a una cuenta de dólares
    assert b.construir(f(2), {1: usd, 2: nota}, sin_tc)["gobierna"] == "Dolares"
    assert b.construir([_fila(date(2021, 8, 17), "Pago", "P", 0, 5.0, "Galicia", 9)], {}, sin_tc)["gobierna"] == "Pesos"


def test_saldo_que_gobierna_es_el_de_la_moneda():
    filas = [_fila(date(2021, 8, 1), "Factura", "F1", 216.6972, 0, "Compras", 1), _fila(date(2021, 8, 17), "Pago", "R1", 0, 20952.45, "Galicia", 7)]
    r = b.construir(filas, {1: {"moneda": "Dolares", "tc": 96.69, "ajusta": False}}, b.CotizacionBNA(SERIE))
    assert r["gobierna"] == "Dolares" and r["saldoGobierna"] == r["saldoDolares"]


def test_cargar_varias_cuentas_da_lo_mismo_que_una_por_una():
    varias = b.cargar_cuentas([454, 450])
    for i in (454, 450):
        una = b.cargar_cuenta(i)
        assert varias[i]["saldoPesos"] == una["saldoPesos"] and varias[i]["saldoDolares"] == una["saldoDolares"] and varias[i]["gobierna"] == una["gobierna"]
    assert b.cargar_cuentas([]) == {}


def test_un_pago_con_cheque_se_pasa_a_dolares_con_el_dolar_del_dia_de_entrega():
    serie = {date(2023, 4, 23): 218.0, date(2023, 5, 15): 230.0}
    filas = [_fila(date(2023, 4, 13), "Factura", "F", 2129.6, 0, "Compras", 1), _fila(date(2023, 5, 16), "Resumen Bancario", "R", 0, 456245.52, "Galicia", 9)]
    compras = {1: {"moneda": "Dolares", "tc": 214.24, "ajusta": False}}
    sin = b.construir(filas, compras, b.CotizacionBNA(serie))
    con = b.construir(filas, compras, b.CotizacionBNA(serie), {("Galicia", 9): date(2023, 4, 24)})
    assert round(sin["saldoDolares"], 2) == round(-2129.6 + 456245.52 / 230.0, 2)       # con el día del débito
    assert round(con["saldoDolares"], 2) == round(-2129.6 + 456245.52 / 218.0, 2)       # con el día de la entrega
    assert con["filas"][1]["fechaEntrega"] == date(2023, 4, 24)


def test_tolerancia_en_dolares_es_el_mayor_entre_un_dolar_y_el_medio_por_ciento():
    chica = b.construir([_fila(date(2021, 8, 1), "Factura", "F", 100.0, 0, "Compras", 1)], {1: {"moneda": "Dolares", "tc": 100.0, "ajusta": False}}, b.CotizacionBNA(SERIE))
    grande = b.construir([_fila(date(2021, 8, 1), "Factura", "F", 5251.42, 0, "Compras", 1)], {1: {"moneda": "Dolares", "tc": 95.0, "ajusta": False}}, b.CotizacionBNA(SERIE))
    assert chica["toleranciaDolares"] == 1.0 and grande["toleranciaDolares"] == 26.26


def test_tc_pactado_pasa_los_pagos_a_dolares_con_el_tipo_de_cambio_de_la_factura():
    """Seguros Galicia: US$ 1.795,54 a $ 1.200 pagados con $ 2.154.648. Sin declarar el tipo de cambio pactado se usa el dólar BNA
    (diferencia de cambio); declarado por Sergio no hay diferencia. Nunca se deduce solo: el caso Palaversich tiene la misma forma."""
    serie = {date(2024, 9, 10): 960.0}
    filas = [_fila(date(2024, 9, 16), "Factura", "F", 1795.54, 0, "Compras", 1), _fila(date(2024, 9, 16), "Tarjeta", "T", 0, 2154648.0, "Tarjetas", 5)]
    compras = {1: {"moneda": "Dolares", "tc": 1200.0, "ajusta": False}}
    sin = b.construir(filas, compras, b.CotizacionBNA(serie))
    con = b.construir(filas, compras, b.CotizacionBNA(serie), None, True)
    assert sin["tcPactado"] is False and abs(sin["saldoDolares"] - (-1795.54 + 2154648.0 / 960.0)) < 0.02
    assert con["tcPactado"] is True and abs(con["saldoDolares"]) < 0.01 and con["saldoGobierna"] == con["saldoDolares"]
    assert con["saldoPesos"] == sin["saldoPesos"]  # el saldo en pesos no cambia


def test_tc_pactado_no_aplica_si_la_cuenta_tiene_documentos_en_pesos():
    filas = [_fila(date(2021, 8, 1), "Factura", "F1", 10.0, 0, "Compras", 1), _fila(date(2021, 8, 1), "Factura", "F2", 1000.0, 0, "Compras", 2)]
    compras = {1: {"moneda": "Dolares", "tc": 100.0, "ajusta": False}, 2: {"moneda": "Pesos", "tc": 1.0, "ajusta": False}}
    r = b.construir(filas, compras, b.CotizacionBNA(SERIE), None, True)
    assert r["gobierna"] == "Mixta" and r["tcPactado"] is False
