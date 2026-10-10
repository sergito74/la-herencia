"""Hallazgos de imputaciones (plazo, doble descuento, sobrepago, notas, duplicados) — 035 (T016). Fixtures puros."""

from datetime import date

from src.features.auditoria_cuentas import hallazgos as h


def _app(**kw):
    a = {"idAplicacion": 1, "medio": "galicia", "idMovimiento": 3240, "fechaPago": date(2026, 5, 28), "idContacto": 258, "idCompra": 1,
         "fechaFactura": date(2023, 4, 10), "importe": 100.0, "origenAplicacion": "automatica-exacta"}
    a.update(kw)
    return a


def test_sumar_meses():
    assert h.sumar_meses(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert h.sumar_meses(date(2023, 4, 10), 24) == date(2025, 4, 10)


def test_pago_fuera_de_plazo_se_agrupa_por_movimiento():
    apps = [_app(), _app(idAplicacion=2, idCompra=2, fechaFactura=date(2019, 5, 7), importe=50.0), _app(idAplicacion=3, idCompra=3, fechaFactura=date(2026, 3, 1))]
    r = h.hallazgos_plazo(apps, 24, 60)
    assert len(r) == 1 and r[0]["causa"] == "aplicacion-fuera-de-plazo"
    assert r[0]["cantidadFacturas"] == 2 and r[0]["importe"] == 150.0 and r[0]["facturaMasVieja"] == date(2019, 5, 7)


def test_el_plazo_se_ajusta_y_dentro_del_plazo_no_se_marca():
    a = [_app(fechaFactura=date(2025, 6, 1))]  # 11 meses antes
    assert h.hallazgos_plazo(a, 24, 60) == [] and len(h.hallazgos_plazo(a, 6, 60)) == 1


def test_anticipo_normal_y_anticipo_largo():
    normal = _app(fechaPago=date(2026, 1, 1), fechaFactura=date(2026, 2, 15))   # 45 días antes
    largo = _app(fechaPago=date(2026, 1, 1), fechaFactura=date(2026, 5, 1))     # 120 días antes
    assert h.hallazgos_plazo([normal], 24, 60) == []
    assert h.hallazgos_plazo([largo], 24, 60)[0]["motivo"].startswith("Pago anterior")


def test_manual_o_fifo_va_al_grupo_que_no_es_excepcion():
    r = h.hallazgos_plazo([_app(origenAplicacion="fifo-032")], 24, 60)
    assert r[0]["causa"] == "fuera-de-plazo-decidido"


def test_medios_sin_fecha_propia_no_se_miden():
    assert h.hallazgos_plazo([_app(medio="tarjetas")], 24, 60) == []
    assert h.hallazgos_plazo([_app(fechaPago=None)], 24, 60) == []


def _doc(**kw):
    d = {"idCompra": 1, "idContacto": 22, "nro": "F1", "total": 1000.0, "tarjeta": 1000.0, "aplicado": 1000.0,
         "bancarias": [{"medio": "bna", "idMovimiento": 14417, "importe": 300.0, "fechaPago": date(2025, 1, 1), "origenAplicacion": "automatica-exacta"}]}
    d.update(kw)
    return d


def test_doble_descuento_con_tarjeta():
    r = h.hallazgos_doble_descuento([_doc(), _doc(idCompra=2)])
    assert len(r) == 1 and r[0]["cantidadFacturas"] == 2 and r[0]["importe"] == 600.0
    assert h.hallazgos_doble_descuento([_doc(tarjeta=400.0)]) == []          # la tarjeta no cubre la factura
    assert h.hallazgos_doble_descuento([_doc(bancarias=[{**_doc()["bancarias"][0], "origenAplicacion": "manual"}])]) == []


def test_sobrepago_excluye_los_casos_de_tarjeta():
    assert h.hallazgos_sobrepago([_doc(tarjeta=0.0, aplicado=1500.0)])[0]["importe"] == 500.0
    assert h.hallazgos_sobrepago([_doc(aplicado=1500.0)]) == []               # eso es doble descuento
    assert h.hallazgos_sobrepago([_doc(tarjeta=0.0, aplicado=1000.5)]) == []  # dentro de la tolerancia
    assert h.hallazgos_sobrepago([_doc(total=-50.0, tarjeta=0.0, aplicado=50.0)]) == []  # nota de crédito


def test_nota_sin_imputar_y_contacto_duplicado():
    n = [{"idContacto": 303, "nro": "ND1", "total": 180411.3, "aplicado": 0.0, "tarjeta": 0.0},
         {"idContacto": 303, "nro": "ND2", "total": 180411.3, "aplicado": 180411.3, "tarjeta": 0.0},
         {"idContacto": 303, "nro": "ND3", "total": 100.0, "aplicado": 0.0, "tarjeta": 0.0}]
    assert [x["motivo"] for x in h.hallazgos_nota_sin_imputar(n, 300)] == ["La nota de débito ND1 no está imputada"]
    c = [{"idContacto": 1, "razonSocial": "A", "cuit": "30-71211460-2"}, {"idContacto": 2, "razonSocial": "B", "cuit": "30712114602"},
         {"idContacto": 3, "razonSocial": "C", "cuit": None}]
    assert sorted(x["idContacto"] for x in h.hallazgos_contacto_duplicado(c)) == [1, 2]


def test_impuesto_sin_boleta_solo_en_organismos_con_saldo_a_favor():
    r = h.hallazgos_impuesto_sin_boleta({119: 14_000_000.0, 12: 100.0, 12345: 9_999_999.0, 72: -50.0}, 300)
    assert [x["idContacto"] for x in r] == [119] and "AFIP" in r[0]["motivo"]


def test_movimiento_sin_contacto_de_cualquier_monto_agrupado_por_concepto():
    movs = [
        {"medio": "bna", "idMovimiento": 1, "fecha": date(2025, 1, 1), "importe": 250_000.0, "concepto": "TRANSFERENCIA A 123 JUAN"},
        {"medio": "bna", "idMovimiento": 2, "fecha": date(2025, 2, 1), "importe": 500.0, "concepto": "TRANSFERENCIA A 456 JUAN"},
        {"medio": "galicia", "idMovimiento": 3, "fecha": date(2025, 1, 1), "importe": -300_000.0, "concepto": "Imp. Cre. Ley 25413"},
        {"medio": "galicia", "idMovimiento": 4, "fecha": date(2025, 1, 1), "importe": -90.0, "concepto": "Imp. Deb. Ley 25413 Gral."},
    ]
    r = h.hallazgos_movimiento_sin_contacto(movs, ["LEY 25413"])
    assert r["movimientosSinExplicar"] == 2 and len(r["sinExplicar"]) == 1          # el chico también cuenta
    assert r["sinExplicar"][0]["concepto"] == "TRANSFERENCIA A JUAN" and r["sinExplicar"][0]["movimientos"] == 2
    assert r["explicados"][0]["clave"] == "LEY 25413" and r["explicados"][0]["movimientos"] == 2
    assert h.hallazgos_movimiento_sin_contacto(movs, [])["movimientosSinExplicar"] == 4


def test_normalizar_concepto():
    assert h.normalizar_concepto("TRANSF. 1234 / ABC-99") == "TRANSF ABC"
    assert h.normalizar_concepto(None) == "(SIN CONCEPTO)"


def test_una_regla_sin_numeros_alcanza_conceptos_con_numeros():
    assert h.explicado_por("TRANSF 1234 JUAN", ["TRANSF JUAN"]) == "TRANSF JUAN"
    assert h.explicado_por("DEP.CH.HS O/B", ["DEP CH HS O B"]) == "DEP CH HS O B"
    assert h.explicado_por("Imp. Cre. Ley 25413", ["LEY 25413"]) == "LEY 25413"
    assert h.explicado_por("Imp. Cre. Ley 99999", ["LEY 25413"]) is None
    assert h.explicado_por(None, ["LEY"]) is None


def test_un_cuit_declarado_como_compartido_no_se_informa_como_contacto_duplicado():
    c = [{"idContacto": 1, "razonSocial": "EESS Saladillo", "cuit": "30-67877449-5"},
         {"idContacto": 2, "razonSocial": "YPF Nordelta", "cuit": "30678774495"},
         {"idContacto": 3, "razonSocial": "YPF Pacheco", "cuit": "30678774495"},
         {"idContacto": 4, "razonSocial": "Otro", "cuit": "20111111112"},
         {"idContacto": 5, "razonSocial": "Otro duplicado", "cuit": "20111111112"}]
    sin_regla = h.hallazgos_contacto_duplicado(c)
    assert sorted(x["idContacto"] for x in sin_regla) == [1, 2, 3, 4, 5]
    con_regla = h.hallazgos_contacto_duplicado(c, {"30678774495"})
    assert sorted(x["idContacto"] for x in con_regla) == [4, 5]       # los demás siguen informándose
