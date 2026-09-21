from src.features.tarjetas_resumenes.conciliacion_documentos import (
    calcular_imputacion,
    importe_pesos,
    sugerir,
)


def _doc(id_, importe, moneda="Pesos", tc=None):
    return {"idCompra": id_, "importeOriginal": importe, "moneda": moneda, "tipoDeCambio": tc}


def test_pesifica_con_el_tc_del_documento():
    assert importe_pesos(_doc(1, 100, "Dolares", 1000)) == 100000.0
    assert importe_pesos(_doc(1, 100, "Pesos", 1)) == 100.0
    assert importe_pesos(_doc(1, 100, "Dolares", None)) == 100.0


def test_pesos_exacto_con_factura_y_nota_de_credito():
    r = calcular_imputacion(900.0, [_doc(1, 1000.0), _doc(2, -100.0)])
    assert r["estado"] == "exacta" and r["diferencia"] == 0
    assert {i["idCompra"]: i["importeImputado"] for i in r["imputados"]} == {1: 1000.0, 2: -100.0}


def test_pesos_dentro_de_tolerancia_de_redondeo():
    assert calcular_imputacion(1000.05, [_doc(1, 1000.0)])["estado"] == "exacta"
    assert calcular_imputacion(1000.50, [_doc(1, 1000.0)])["estado"] == "parcial"


def test_dolares_despeja_tc_implicito_y_cierra_exacto_con_la_linea():
    # Factura USD 1000 (TC 1000) + NC USD -100: neto USD 900. Línea $ 927.000 → TC implícito 1030.
    docs = [_doc(1, 1000.0, "Dolares", 1000), _doc(2, -100.0, "Dolares", 1000)]
    r = calcular_imputacion(918000.0, docs)
    assert r["tcImplicito"] == 1020.0 and r["tcReferencia"] == 1000.0
    assert r["desvioTc"] == 0.02 and r["estado"] == "aproximada"
    assert r["diferencia"] == 0
    assert sum(i["importeImputado"] for i in r["imputados"]) == 918000.0


def test_dolares_con_tc_muy_distinto_queda_parcial():
    r = calcular_imputacion(1_030_000.0, [_doc(1, 1000.0, "Dolares", 1000)])
    assert r["tcImplicito"] == 1030.0 and r["estado"] == "parcial"


def test_mezcla_pesos_y_dolares():
    # ARS 10.000 + USD 100 (TC 1000). Línea 111.000 → TC implícito (111000-10000)/100 = 1010.
    r = calcular_imputacion(111000.0, [_doc(1, 10000.0), _doc(2, 100.0, "Dolares", 1000)])
    assert r["tcImplicito"] == 1010.0 and r["estado"] == "aproximada" and r["diferencia"] == 0


def test_redondeo_por_documento_no_rompe_el_cierre():
    docs = [_doc(1, 33.33, "Dolares", 1000), _doc(2, 33.33, "Dolares", 1000), _doc(3, 33.34, "Dolares", 1000)]
    r = calcular_imputacion(100_003.01, docs)
    assert round(sum(i["importeImputado"] for i in r["imputados"]), 2) == 100003.01


def test_usd_neto_cero_no_se_puede_despejar_y_usa_tc_propio():
    r = calcular_imputacion(500.0, [_doc(1, 100.0, "Dolares", 1000), _doc(2, -100.0, "Dolares", 1000)])
    assert r["tcImplicito"] is None and r["estado"] == "parcial"


def test_un_documento_en_pesos_que_no_coincide_es_pago_parcial_e_imputa_la_linea():
    r = calcular_imputacion(250.0, [_doc(1, 1000.0)])
    assert r["pagoParcial"] and r["estado"] == "parcial" and r["diferencia"] == -750.0
    assert r["imputados"] == [{"idCompra": 1, "importeImputado": 250.0}]


def test_sugerir_encuentra_la_combinacion_que_salda_la_cuenta():
    docs = [
        _doc(1, 1000.0, "Dolares", 1000),
        _doc(2, -100.0, "Dolares", 1000),
        _doc(3, 250.0, "Dolares", 1000),
        _doc(4, 5555.0),
    ]
    sug = sugerir(918000.0, docs)
    assert sug and sug[0]["idsCompra"] == [1, 2] and sug[0]["estado"] == "aproximada"


def test_sugerir_prioriza_exactas_en_pesos():
    docs = [_doc(1, 700.0), _doc(2, 300.0), _doc(3, 1000.0), _doc(4, 50.0, "Dolares", 1000)]
    sug = sugerir(1000.0, docs)
    assert sug[0]["estado"] == "exacta"
    assert sorted(map(tuple, (s["idsCompra"] for s in sug if s["estado"] == "exacta"))) == [(1, 2), (3,)]


def test_sugerir_sin_coincidencias_devuelve_vacio():
    assert sugerir(123.45, [_doc(1, 1000.0), _doc(2, 2000.0)]) == []
