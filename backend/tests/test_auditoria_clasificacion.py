"""Clasificación de cuentas contra la referencia del Access — 035 (T008). Fixtures puros, sin base."""

from datetime import date

from src.features.auditoria_cuentas import clasificacion as c


def _fila(origen, id_origen, credito=0.0, deuda=0.0, fecha=date(2025, 1, 1)):
    return {"Origen": origen, "IdOrigen": id_origen, "Credito": credito, "Deuda": deuda, "Fecha": fecha}


ORIGENES_REF = {"Compras", "Banco Nacion"}
MAX_REF = {"Compras": date(2026, 9, 14), "Banco Nacion": date(2026, 7, 30)}


def _desc(wc, ref, reasignados=frozenset(), claves=None):
    claves = claves if claves is not None else {(f["Origen"], f["IdOrigen"]) for f in ref}
    return c.descomponer(wc, ref, ORIGENES_REF, set(reasignados), MAX_REF, claves)


def test_sin_diferencias_no_hay_componentes():
    f = [_fila("Compras", 1, deuda=100), _fila("Banco Nacion", 2, credito=100)]
    assert all(v == 0 for v in _desc(f, f).values())


def test_fuentes_que_el_access_no_contaba():
    wc = [_fila("Compras", 1, deuda=100), _fila("Tarjetas", 9, credito=100)]
    comp = _desc(wc, [_fila("Compras", 1, deuda=100)])
    assert comp["fuentes-no-contadas"] == 100 and comp["otros"] == 0


def test_datos_posteriores_a_lo_ultimo_que_tenia_el_access():
    wc = [_fila("Banco Nacion", 5, credito=50, fecha=date(2026, 9, 1))]
    assert _desc(wc, [])["datos-posteriores"] == 50


def test_fila_nueva_con_fecha_vieja_queda_sin_explicar():
    wc = [_fila("Banco Nacion", 5, credito=50, fecha=date(2025, 3, 1))]
    assert _desc(wc, [])["otros"] == 50


def test_reasignacion_y_correccion_de_importe():
    comp = _desc([_fila("Banco Nacion", 7, credito=30)], [], reasignados={("Banco Nacion", 7)})
    assert comp["reasignacion"] == 30
    comp = _desc([_fila("Compras", 1, deuda=120)], [_fila("Compras", 1, deuda=100)])
    assert comp["correccion-importe"] == -20


def test_la_descomposicion_suma_la_diferencia_exacta():
    wc = [_fila("Compras", 1, deuda=100), _fila("Tarjetas", 9, credito=100), _fila("Banco Nacion", 5, credito=50, fecha=date(2026, 9, 1)),
          _fila("Banco Nacion", 6, credito=10, fecha=date(2024, 1, 1))]
    ref = [_fila("Compras", 1, deuda=90), _fila("Banco Nacion", 3, credito=5)]
    diferencia = sum(f["Credito"] - f["Deuda"] for f in wc) - sum(f["Credito"] - f["Deuda"] for f in ref)
    assert round(sum(_desc(wc, ref).values()), 2) == round(diferencia, 2)


def test_causas_con_umbral_en_pesos_y_sin_umbral_en_dolares():
    comp = {"otros": 0.0}
    assert c.clasificar_cuenta(1, "A", "Pesos", 1000.0, 1000.0, comp, 300)["causa"] == "coincide"
    assert c.clasificar_cuenta(1, "A", "Pesos", 1200.0, 1000.0, comp, 300)["causa"] == "diferencia-menor-umbral"
    # en dólares una diferencia de 200 no es menor a ningún umbral: se explica o es "otros"
    assert c.clasificar_cuenta(1, "A", "Dolares", 20200.0, 20000.0, {"otros": 200.0}, 300)["causa"] == "otros"
    assert c.clasificar_cuenta(1, "A", "Dolares", 20200.0, 20000.0, {"otros": 0.0}, 300)["causa"] == "coincide-causa-conocida"


def test_coincide_con_causa_conocida_y_otros():
    ok = c.clasificar_cuenta(1, "A", "Pesos", 5000.0, 100.0, {"fuentes-no-contadas": 4900.0, "otros": 0.0}, 300)
    assert ok["causa"] == "coincide-causa-conocida" and ok["sinExplicar"] == 0
    mal = c.clasificar_cuenta(1, "A", "Pesos", 5000.0, 100.0, {"otros": 4900.0}, 300)
    assert mal["causa"] == "otros"
    assert c.clasificar_cuenta(1, "A", "Pesos", 5000.0, None, None, 300)["causa"] == "sin-referencia"


def test_el_total_cuenta_una_vez_cada_cuenta_y_excluye_lo_excluido():
    datos = {"saldoWc": {1: 100.0, 2: 500.0, 3: 0.0}, "saldoRef": {1: 100.0, 2: 0.0, 3: 0.0}, "filasWc": {}, "filasRef": {},
             "origenesRef": set(), "reasignados": set(), "maxFechaRef": {}, "clavesRef": set(), "razon": {}, "moneda": {},
             "excluidos": {3}}
    cuentas = c.clasificar_cuentas(datos, {"umbralPesos": 300})
    assert [x["idContacto"] for x in cuentas] == [1, 2]
    r = c.resumen(cuentas)
    assert r["totalCuentas"] == 2 and sum(g["cuentas"] for g in r["causas"]) == 2


def test_diferencia_documentada_deja_de_ser_excepcion_hasta_que_cambia():
    comp = {"otros": 5000.0}
    doc = {"importeRef": 5000.0, "motivo": "Pago de Mercado Pago aceptado"}
    sin = c.clasificar_cuenta(1, "A", "Pesos", 5100.0, 100.0, comp, 300)
    assert sin["causa"] == "otros"
    con = c.clasificar_cuenta(1, "A", "Pesos", 5100.0, 100.0, comp, 300, doc)
    assert con["causa"] == "coincide-causa-conocida" and con["documentada"] == "Pago de Mercado Pago aceptado"
    # la diferencia cambió respecto de la documentada: vuelve a aparecer
    cambio = c.clasificar_cuenta(1, "A", "Pesos", 9100.0, 100.0, {"otros": 9000.0}, 300, doc)
    assert cambio["causa"] == "otros"
