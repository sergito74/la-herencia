"""031 — reglas puras de la fuente unificada de vínculos. No toca WC."""

from __future__ import annotations

from datetime import date

from src.features.vinculos import cadenas


def ap(id_ap, origen, id_mov, id_doc, importe, tipo="CompraDeuda", carga="automatica-exacta"):
    return {"idAplicacion": id_ap, "origenMovimiento": origen, "idMovimiento": id_mov, "tipoDocumento": tipo,
            "idDocumento": id_doc, "importe": importe, "origenCarga": carga}


def raw(**kw):
    base = {"aplicaciones": [], "lineasCompras": [], "tesoreria": [], "backfill": [], "lineas": {},
            "pagosResumen": [], "valores": [], "movimientos": {}, "documentos": {}}
    base.update(kw)
    return base


def test_debito_de_resumen_hereda_consumos_en_proporcion_y_resto_pendiente():
    r = raw(lineasCompras=[{"idLinea": 1, "idCompra": 10, "importe": 600}, {"idLinea": 2, "idCompra": 11, "importe": 200}],
            lineas={1: {"idResumen": 7}, 2: {"idResumen": 7}},
            pagosResumen=[{"idResumen": 7, "importe": 500, "origen": "bna", "idMovimiento": 99},
                          {"idResumen": 7, "importe": 500, "origen": "bna", "idMovimiento": 98}])
    docs = cadenas.documentos_de_movimiento(cadenas.construir_vinculos(r))
    assert sorted((d["idDocumentoAplicado"], d["importeAplicado"]) for d in docs[("bna", 99)]) == [(10, 300.0), (11, 100.0)]
    assert all(d["via"] == "tarjeta" for d in docs[("bna", 99)])


def test_cheque_se_empareja_por_numero_e_importe_y_elige_el_mas_cercano():
    movs = {("bna", 1): {"fecha": date(2020, 3, 12), "importe": -2050.0, "concepto": "48HS. BANCOS 003620071"},
            ("galicia", 5): {"fecha": date(2026, 3, 2), "importe": -308519.75, "concepto": "Echeq Galicia Nro:     120"}}
    valores = [{"idValor": 1, "numero": 3620071, "importe": 2050.0, "fechaEmision": date(2019, 1, 1)},
               {"idValor": 2, "numero": 3620071, "importe": 2050.0, "fechaEmision": date(2020, 3, 1)},
               {"idValor": 3, "numero": 120, "importe": 308519.75, "fechaEmision": date(2026, 2, 20)},
               {"idValor": 4, "numero": 3620071, "importe": 999.0, "fechaEmision": date(2020, 3, 1)}]
    assert cadenas.emparejar_cheques(movs, valores) == {("bna", 1): 2, ("galicia", 5): 3}


def test_cheque_no_empareja_si_el_debito_es_anterior_a_la_emision():
    movs = {("bna", 1): {"fecha": date(2020, 1, 1), "importe": -10.0, "concepto": "48HS. BANCOS 000000055"}}
    assert cadenas.emparejar_cheques(movs, [{"idValor": 1, "numero": 55, "importe": 10.0, "fechaEmision": date(2020, 2, 1)}]) == {}


def test_debito_de_cheque_hereda_la_factura_del_cheque():
    r = raw(tesoreria=[{"medio": "valores-propios", "idMovimiento": 3, "tipoDocumento": "Compras", "idDocumento": 50, "importe": 100}],
            valores=[{"idValor": 3, "numero": 77, "importe": 100, "fechaEmision": date(2020, 1, 1)}],
            movimientos={("bna", 8): {"fecha": date(2020, 1, 5), "importe": -100.0, "concepto": "48HS. BANCOS 000000077"}})
    docs = cadenas.documentos_de_movimiento(cadenas.construir_vinculos(r))
    assert docs[("bna", 8)] == [{"tipoDocumento": "CompraDeuda", "idDocumentoAplicado": 50, "importeAplicado": 100.0, "via": "valor-propio"}]


def test_aplicacion_directa_a_factura_pagada_por_tarjeta_es_redundante():
    r = raw(aplicaciones=[ap(1, "bna", 14984, 10, 255600)], lineasCompras=[{"idLinea": 1, "idCompra": 10, "importe": 255600}],
            lineas={1: {"idResumen": 667}})
    vinculos = cadenas.construir_vinculos(r)
    directa = next(v for v in vinculos if v["via"] == "aplicacion")
    assert directa["redundante"]
    assert cadenas.pagado_por_documento(vinculos)[("CompraDeuda", 10)] == 255600
    assert ("bna", 14984) not in cadenas.documentos_de_movimiento(vinculos)


def test_mismo_consumo_en_dos_lugares_cuenta_una_vez():
    r = raw(aplicaciones=[ap(1, "tarjetas", 5, 10, 100)], lineasCompras=[{"idLinea": 5, "idCompra": 10, "importe": 100}])
    assert cadenas.pagado_por_documento(cadenas.construir_vinculos(r))[("CompraDeuda", 10)] == 100


def test_documento_en_dolares_se_pesifica_salvo_manual():
    docs = {("CompraDeuda", 10): {"moneda": "Dolares", "tc": 197.15}}
    auto = cadenas.construir_vinculos(raw(aplicaciones=[ap(1, "galicia", 1, 10, 100)], documentos=docs))
    assert auto[0]["importeArs"] == 19715.0 and auto[0]["monedaMezclada"]
    manual = cadenas.construir_vinculos(raw(aplicaciones=[ap(1, "galicia", 1, 10, 100, carga="manual")], documentos=docs))
    assert manual[0]["importeArs"] == 100 and not manual[0]["monedaMezclada"]


def test_consumo_sin_pago_de_resumen_cuenta_como_pagado_pero_no_en_movimientos():
    r = raw(lineasCompras=[{"idLinea": 1, "idCompra": 10, "importe": 50}], lineas={1: {"idResumen": 9}})
    vinculos = cadenas.construir_vinculos(r)
    assert cadenas.pagado_por_documento(vinculos) == {("CompraDeuda", 10): 50}
    assert cadenas.documentos_de_movimiento(vinculos) == {}


def test_tesoreria_a_impuesto_y_sueldo_mapea_tipos_y_va_al_movimiento():
    r = raw(tesoreria=[{"medio": "galicia", "idMovimiento": 1, "tipoDocumento": "Impuestos", "idDocumento": 218, "importe": 3509.12},
                       {"medio": "galicia", "idMovimiento": 2, "tipoDocumento": "Remuneraciones", "idDocumento": 9, "importe": 430000}])
    docs = cadenas.documentos_de_movimiento(cadenas.construir_vinculos(r))
    assert docs[("galicia", 1)][0]["tipoDocumento"] == "Impuesto"
    assert docs[("galicia", 2)][0]["tipoDocumento"] == "Remuneracion"


def test_aplicacion_a_factura_en_dolares_ya_cargada_en_pesos_no_se_pesifica():
    docs = {("CompraDeuda", 10): {"moneda": "Dolares", "tc": 350.0}}
    movs = {("bna", 1): {"fecha": date(2023, 9, 4), "importe": -79717.23, "concepto": "DEB.TRAN"}}
    v = cadenas.construir_vinculos(raw(aplicaciones=[ap(1, "bna", 1, 10, 79717.23)], documentos=docs, movimientos=movs))
    assert v[0]["importeArs"] == 79717.23 and not v[0]["monedaMezclada"]
