"""031 — control de integridad y propuesta de corrección (funciones puras)."""

from __future__ import annotations

from datetime import date

from src.features.vinculos import cadenas, control, correccion


def ap(id_ap, origen, id_mov, id_doc, importe, tipo="CompraDeuda", carga="automatica-exacta"):
    return {"idAplicacion": id_ap, "origenMovimiento": origen, "idMovimiento": id_mov, "tipoDocumento": tipo,
            "idDocumento": id_doc, "importe": importe, "origenCarga": carga}


def armar(**kw):
    raw = {"aplicaciones": [], "lineasCompras": [], "tesoreria": [], "backfill": [], "lineas": {}, "pagosResumen": [],
           "valores": [], "movimientos": {}, "documentos": {}, "fechasOtros": {}}
    raw.update(kw)
    raw["vinculos"] = cadenas.construir_vinculos(raw)
    return raw


def doc(fecha, total, contacto=48, moneda="Pesos", tc=1.0):
    return {"fecha": fecha, "totalArs": total, "idContacto": contacto, "moneda": moneda, "tc": tc}


def mov(fecha, importe, contacto=48):
    return {"fecha": fecha, "importe": importe, "idContacto": contacto, "concepto": "TRANSF"}


def categorias(raw):
    return sorted(h["categoria"] for h in control.hallazgos(raw))


def test_sin_inconsistencias_da_cero():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 100)], documentos={("CompraDeuda", 10): doc(date(2026, 1, 1), 100)},
                movimientos={("bna", 1): mov(date(2026, 1, 5), -100)})
    assert control.totales(control.hallazgos(raw)) == {c: 0 for c in control.CATEGORIAS}


def test_doble_imputacion_y_documento_excedido_por_tarjeta():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 100)], lineasCompras=[{"idLinea": 5, "idCompra": 10, "importe": 150}],
                lineas={5: {"idResumen": 1}}, documentos={("CompraDeuda", 10): doc(date(2026, 1, 1), 100)},
                movimientos={("bna", 1): mov(date(2026, 1, 5), -100)})
    hs = control.hallazgos(raw)
    assert sorted(h["categoria"] for h in hs) == ["doble-imputacion", "documento-excedido"]
    excedido = next(h for h in hs if h["categoria"] == "documento-excedido")
    assert excedido["exceso"] == 50 and excedido["imputadoPorVia"] == {"aplicacion (redundante)": 100, "tarjeta": 150}


def test_fecha_incoherente_mas_de_60_dias_y_nunca_manual():
    base = dict(documentos={("CompraDeuda", 10): doc(date(2023, 5, 1), 1000)},
                movimientos={("bna", 1): mov(date(2019, 4, 11), -1000)})
    assert categorias(armar(aplicaciones=[ap(1, "bna", 1, 10, 1000)], **base)) == ["fecha-incoherente"]
    assert categorias(armar(aplicaciones=[ap(1, "bna", 1, 10, 1000, carga="manual")], **base)) == []
    cerca = dict(base, movimientos={("bna", 1): mov(date(2023, 3, 2), -1000)})
    assert categorias(armar(aplicaciones=[ap(1, "bna", 1, 10, 1000)], **cerca)) == []


def test_moneda_mezclada():
    raw = armar(aplicaciones=[ap(1, "galicia", 1, 10, 22137.18)],
                documentos={("CompraDeuda", 10): doc(date(2026, 5, 1), 22137.18 * 197.15, moneda="Dolares", tc=197.15)},
                movimientos={("galicia", 1): mov(date(2026, 5, 28), -7868575.41)})
    assert categorias(raw) == ["moneda-mezclada"]


def test_movimiento_excedido():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 500), ap(2, "bna", 1, 11, 500)],
                documentos={("CompraDeuda", 10): doc(date(2026, 1, 1), 500), ("CompraDeuda", 11): doc(date(2026, 1, 1), 500)},
                movimientos={("bna", 1): mov(date(2026, 1, 5), -600)})
    assert categorias(raw) == ["movimiento-excedido"]


def test_propuesta_moneda_mezclada_pesifica():
    raw = armar(aplicaciones=[ap(1, "galicia", 1, 10, 100)],
                documentos={("CompraDeuda", 10): doc(date(2026, 5, 1), 19715, moneda="Dolares", tc=197.15)},
                movimientos={("galicia", 1): mov(date(2026, 5, 28), -19715)})
    items = correccion.proponer(raw, control.hallazgos(raw))
    assert [(i["accion"], i["grupo"], i["importe"]) for i in items] == [("pesificar", "moneda-mezclada/alta", 19715.0)]


def test_fecha_incoherente_anula_y_propone_reemplazo_en_los_dos_sentidos():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 1000)],
                documentos={("CompraDeuda", 10): doc(date(2023, 5, 1), 1000), ("CompraDeuda", 11): doc(date(2019, 3, 1), 1000)},
                movimientos={("bna", 1): mov(date(2019, 4, 11), -1000), ("bna", 2): mov(date(2023, 5, 20), -1000)})
    items = correccion.proponer(raw, control.hallazgos(raw))
    assert [(i["accion"], i["grupo"]) for i in items][0] == ("anular", "fecha-incoherente/alta")
    reemplazos = {(i["origenMovimiento"], i["idMovimientoOrigen"], i["idDocumento"]) for i in items if i["accion"] == "reemplazo"}
    assert reemplazos == {("bna", 2, 10), ("bna", 1, 11)}
    assert all(i["elegido"] for i in items if i["accion"] == "reemplazo")


def test_certeza_media_entre_61_y_365_dias():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 1000)], documentos={("CompraDeuda", 10): doc(date(2023, 5, 1), 1000)},
                movimientos={("bna", 1): mov(date(2023, 1, 1), -1000)})
    assert correccion.proponer(raw, control.hallazgos(raw))[0]["grupo"] == "fecha-incoherente/media"


def test_reemplazo_con_varios_candidatos_es_ambiguo_y_cada_candidato_se_usa_una_vez():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 1000), ap(2, "bna", 3, 12, 1000)],
                documentos={("CompraDeuda", 10): doc(date(2023, 5, 1), 1000), ("CompraDeuda", 12): doc(date(2023, 5, 2), 1000)},
                movimientos={("bna", 1): mov(date(2019, 4, 11), -1000), ("bna", 3): mov(date(2019, 4, 12), -1000),
                             ("bna", 2): mov(date(2023, 5, 20), -1000), ("bna", 4): mov(date(2023, 5, 21), -1000)})
    items = [i for i in correccion.proponer(raw, control.hallazgos(raw)) if i["accion"] == "reemplazo"]
    assert all(i["grupo"] == "reemplazo-ambiguo" and len(i["candidatos"]) == 2 for i in items)


def test_manual_nunca_entra_en_la_propuesta():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 1000, carga="manual")], lineasCompras=[{"idLinea": 5, "idCompra": 10, "importe": 1000}],
                lineas={5: {"idResumen": 1}}, documentos={("CompraDeuda", 10): doc(date(2023, 5, 1), 1000)},
                movimientos={("bna", 1): mov(date(2019, 4, 11), -1000)})
    assert correccion.proponer(raw, control.hallazgos(raw)) == []


def test_doble_imputacion_anula_y_busca_factura_para_el_movimiento_libre():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 500)], lineasCompras=[{"idLinea": 5, "idCompra": 10, "importe": 500}],
                lineas={5: {"idResumen": 1}},
                documentos={("CompraDeuda", 10): doc(date(2026, 1, 1), 500), ("CompraDeuda", 11): doc(date(2026, 1, 3), 500)},
                movimientos={("bna", 1): mov(date(2026, 1, 10), -500)})
    items = correccion.proponer(raw, control.hallazgos(raw))
    assert [(i["accion"], i["idDocumento"]) for i in items] == [("anular", 10), ("reemplazo", 11)]


def test_documento_excedido_anula_la_aplicacion_automatica_mas_alejada_sin_buscar_reemplazo_para_la_factura():
    raw = armar(aplicaciones=[ap(1, "tarjetas", 730, 10, 160)], lineasCompras=[{"idLinea": 1520, "idCompra": 10, "importe": 160}],
                lineas={730: {"idResumen": 478, "fecha": date(2025, 11, 26)}, 1520: {"idResumen": 700, "fecha": date(2020, 12, 1)}},
                documentos={("CompraDeuda", 10): doc(date(2020, 12, 1), 160)},
                fechasOtros={("tarjetas", 730): date(2025, 11, 26), ("tarjetas", 1520): date(2020, 12, 1)})
    items = correccion.proponer(raw, control.hallazgos(raw))
    assert [(i["accion"], i["grupo"], i["idAplicacion"]) for i in items] == [("anular", "documento-excedido/alta", 1)]


def test_excedido_anula_primero_banco_y_ajusta_parcialmente():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 600), ap(2, "tarjetas", 5, 10, 1000)],
                documentos={("CompraDeuda", 10): doc(date(2026, 1, 1), 1000)},
                movimientos={("bna", 1): mov(date(2026, 1, 2), -600)},
                lineas={5: {"idResumen": 1, "fecha": date(2026, 1, 1)}}, fechasOtros={("tarjetas", 5): date(2026, 1, 1)})
    items = correccion.proponer(raw, control.hallazgos(raw))
    anulada = [i for i in items if i["accion"] == "anular"]
    assert [i["idAplicacion"] for i in anulada] == [1]  # banco antes que la cadena de tarjeta


def test_excedido_con_aplicacion_mayor_al_exceso_se_ajusta():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 600), ap(2, "bna", 2, 10, 500)],
                documentos={("CompraDeuda", 10): doc(date(2026, 1, 1), 1000)},
                movimientos={("bna", 1): mov(date(2026, 1, 20), -600), ("bna", 2): mov(date(2026, 1, 2), -500)})
    items = correccion.proponer(raw, control.hallazgos(raw))
    assert [(i["accion"], i["idAplicacion"], i["importe"]) for i in items] == [("anular", 1, 600), ("reemplazo", None, 500)]
    assert items[1]["origenMovimiento"] == "bna" and items[1]["idMovimientoOrigen"] == 1 and items[1]["elegido"]


def test_venta_con_cobro_muy_anterior_es_certeza_media():
    raw = armar(aplicaciones=[ap(1, "bna", 1, 10, 1000, tipo="VentaHacienda")],
                documentos={("VentaHacienda", 10): doc(date(2023, 5, 1), 1000)},
                movimientos={("bna", 1): mov(date(2019, 4, 11), 1000)})
    assert correccion.proponer(raw, control.hallazgos(raw))[0]["grupo"] == "fecha-incoherente/media"
