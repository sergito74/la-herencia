from src.features.tarjetas_resumenes.conciliacion_documentos import (
    calcular_imputacion,
    importe_pesos,
    repartir,
    sugerir,
)


def _doc(id_, importe, moneda="Pesos", tc=None):
    return {"idCompra": id_, "importeOriginal": importe, "moneda": moneda, "tipoDeCambio": tc}


def test_pesifica_con_el_tc_del_documento_redondeando_los_dolares_a_centavos():
    assert importe_pesos(_doc(1, 100, "Dolares", 1000)) == 100000.0
    assert importe_pesos(_doc(1, 100, "Pesos", 1)) == 100.0
    assert importe_pesos(_doc(1, 100, "Dolares", None)) == 100.0
    # 161,8796 USD guardados = 161,88 USD en la factura impresa.
    assert importe_pesos(_doc(1, 161.8796, "Dolares", 1200)) == 194256.0


def test_pesos_exacto_con_factura_y_nota_de_credito():
    r = calcular_imputacion(900.0, [_doc(1, 1000.0), _doc(2, -100.0)])
    assert r["estado"] == "exacta" and r["diferencia"] == 0
    assert {i["idCompra"]: i["importeImputado"] for i in r["imputados"]} == {1: 1000.0, 2: -100.0}


def test_pesos_dentro_de_tolerancia_de_redondeo():
    assert calcular_imputacion(1000.05, [_doc(1, 1000.0)])["estado"] == "exacta"
    assert calcular_imputacion(1000.50, [_doc(1, 1000.0), _doc(2, 0.01)])["estado"] == "parcial"


def test_factura_en_dolares_mas_nota_de_ajuste_de_tc_cierra_exacto_en_pesos():
    # Factura USD 1000 a TC 1000 = $ 1.000.000. La tarjeta cobró a 1030: $ 1.030.000.
    # La ND de ajuste de tipo de cambio (en pesos) por $ 30.000 cierra la línea.
    docs = [_doc(1, 1000.0, "Dolares", 1000), _doc(2, 30000.0)]
    r = calcular_imputacion(1_030_000.0, docs)
    assert r["estado"] == "exacta" and r["diferencia"] == 0


def test_con_dolares_se_tolera_hasta_un_peso_de_redondeo_de_conversion():
    docs = [_doc(1, 100.0, "Dolares", 1000)]
    assert calcular_imputacion(100_000.68, docs)["estado"] == "exacta"
    assert calcular_imputacion(100_001.50, docs)["estado"] == "parcial"


def test_sin_la_nota_de_ajuste_no_cierra_y_orienta_con_el_tc_implicito():
    r = calcular_imputacion(1_030_000.0, [_doc(1, 1000.0, "Dolares", 1000)])
    assert r["estado"] == "parcial" and r["diferencia"] == 30000.0
    assert r["tcImplicito"] == 1030.0 and r["tcReferencia"] == 1000.0 and r["desvioTc"] == 0.03
    assert not r["pagoParcial"]


def test_un_documento_en_pesos_que_no_coincide_es_pago_parcial_e_imputa_la_linea():
    r = calcular_imputacion(250.0, [_doc(1, 1000.0)])
    assert r["pagoParcial"] and r["estado"] == "parcial" and r["diferencia"] == -750.0
    assert r["imputados"] == [{"idCompra": 1, "importeImputado": 250.0}]


def test_sugerir_encuentra_factura_usd_mas_nc_usd_que_saldan_la_cuenta():
    docs = [
        _doc(1, 918.66, "Dolares", 1200),
        _doc(2, -458.56, "Dolares", 1200),
        _doc(3, 250.0, "Dolares", 1200),
        _doc(4, 5555.0),
    ]
    sug = sugerir(552_120.0, docs)
    assert sug and sug[0]["idsCompra"] == [1, 2] and sug[0]["estado"] == "exacta"


def test_sugerir_combina_documentos_de_distintos_proveedores():
    docs = [{**_doc(1, 700.0), "proveedor": "A"}, {**_doc(2, 300.0), "proveedor": "B"}, _doc(3, 5.0)]
    assert sugerir(1000.0, docs)[0]["idsCompra"] == [1, 2]


def test_sugerir_prioriza_menos_documentos():
    docs = [_doc(1, 700.0), _doc(2, 300.0), _doc(3, 1000.0)]
    sug = sugerir(1000.0, docs)
    assert [s["idsCompra"] for s in sug] == [[3], [1, 2]]


def test_sugerir_sin_coincidencias_devuelve_vacio():
    assert sugerir(123.45, [_doc(1, 1000.0), _doc(2, 2000.0)]) == []


def _lin(id_, importe):
    return {"idLinea": id_, "importe": importe}


def test_repartir_asigna_cada_documento_entero_cuando_hay_una_solucion_exacta():
    r = repartir([_lin(10, 600.0), _lin(11, 400.0)], [_doc(1, 400.0), _doc(2, 600.0)])
    por_doc = {x["idCompra"]: x["idLinea"] for x in r["reparto"]}
    assert por_doc == {1: 11, 2: 10} and r["diferencias"] == {10: 0.0, 11: 0.0}


def test_repartir_parte_un_documento_entre_varias_lineas():
    r = repartir([_lin(10, 600.0), _lin(11, 400.0)], [_doc(1, 1000.0)])
    assert sorted((x["idLinea"], x["importe"]) for x in r["reparto"]) == [(10, 600.0), (11, 400.0)]
    assert r["diferencias"] == {10: 0.0, 11: 0.0}


def test_repartir_con_nota_de_credito_y_factura_entre_dos_lineas():
    r = repartir([_lin(10, 900.0), _lin(11, 500.0)], [_doc(1, 1500.0), _doc(2, -100.0)])
    assert r["diferencias"] == {10: 0.0, 11: 0.0}
    assert sum(x["importe"] for x in r["reparto"]) == 1400.0


def test_repartir_informa_la_diferencia_cuando_no_alcanza():
    r = repartir([_lin(10, 1000.0)], [_doc(1, 400.0)])
    assert r["diferencias"] == {10: 600.0}
