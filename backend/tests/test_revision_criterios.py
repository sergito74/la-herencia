"""Pruebas de las funciones puras de `criterios.py` — 036 (T018). No leen la base."""

from __future__ import annotations

from src.features.revision_cuentas import criterios


def _sana(**cambios) -> dict:
    ctx = {"pagos_pendientes": 0, "pagos_importe_pendiente": 0.0, "pagos_antiguos": 0, "detector_cierra": True, "hallazgos": set(),
           "retenciones_sin_certificado": 0, "imputaciones": {"sanas": True}, "tiene_inventario": True, "reabierta": False,
           "referencia_access": {"tiene": True, "explica": True, "diferencia": 0.0}, "saldo_externo": None, "sin_estado": False}
    ctx.update(cambios)
    return ctx


def _por_codigo(ctx: dict) -> dict:
    return {c["codigo"]: c for c in criterios.evaluar(ctx)}


def test_hay_siete_criterios_en_orden_con_su_etapa():
    c = criterios.evaluar(_sana())
    assert [x["codigo"] for x in c] == ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    assert {x["codigo"]: x["etapa"] for x in c} == {"C1": "E1", "C2": "E2", "C3": "E4", "C4": "E3", "C5": "E5", "C6": "E4", "C7": "E6"}
    for x in c:
        assert x["medido"] and x["texto"]


def test_una_cuenta_sin_pendientes_cumple_todo_y_queda_en_e6():
    c = criterios.evaluar(_sana())
    assert all(x["cumple"] is True for x in c)
    assert criterios.etapa_de(c, tiene_inventario=True) == "E6"
    assert criterios.faltantes_para_cerrar(c) == []


def test_sin_inventario_la_cuenta_esta_en_e0():
    c = criterios.evaluar(_sana(tiene_inventario=False))
    assert criterios.etapa_de(c, tiene_inventario=False) == "E0"
    assert _por_codigo(_sana(tiene_inventario=False))["C7"]["cumple"] is False


def test_pagos_sin_factura_sin_decision_dejan_la_cuenta_en_e1():
    ctx = _sana(pagos_pendientes=8, pagos_importe_pendiente=1872243.0)
    c = criterios.evaluar(ctx)
    assert _por_codigo(ctx)["C1"]["cumple"] is False and "8 pagos sin factura" in _por_codigo(ctx)["C1"]["medido"]
    assert criterios.etapa_de(c, True) == "E1"


def test_los_pagos_antiguos_no_bloquean_c1_pero_quedan_anotados():
    c1 = _por_codigo(_sana(pagos_antiguos=8))["C1"]
    assert c1["cumple"] is True and "8 anteriores a 2021" in c1["medido"]


def test_el_detector_sin_cerrar_bloquea_c1():
    assert _por_codigo(_sana(detector_cierra=False))["C1"]["cumple"] is False


def test_contacto_duplicado_incumple_c2_y_la_etapa_es_e2():
    ctx = _sana(hallazgos={"contacto-duplicado"})
    assert _por_codigo(ctx)["C2"]["cumple"] is False
    assert criterios.etapa_de(criterios.evaluar(ctx), True) == "E2"


def test_doble_descuento_incumple_c4_y_la_etapa_es_e3():
    ctx = _sana(hallazgos={"doble-descuento-tarjeta"})
    assert _por_codigo(ctx)["C4"]["cumple"] is False
    assert criterios.etapa_de(criterios.evaluar(ctx), True) == "E3"


def test_c3_con_saldo_externo_que_cierra_cumple_y_guarda_la_fuente():
    ctx = _sana(saldo_externo={"clasificacion": "menor-al-umbral", "fuente": "portal", "diferencia": 3.3, "fechaSaldo": "2026-09-30"})
    c3 = _por_codigo(ctx)["C3"]
    assert c3["cumple"] is True and c3["evidencia"] == "portal"


def test_c3_con_diferencia_contra_el_saldo_externo_no_cumple():
    ctx = _sana(saldo_externo={"clasificacion": "con-diferencia", "fuente": "pdf", "diferencia": 5000.0, "fechaSaldo": "2026-09-30"})
    assert _por_codigo(ctx)["C3"]["cumple"] is False
    assert criterios.etapa_de(criterios.evaluar(ctx), True) == "E4"


def test_c3_informa_cuando_el_access_discrepa_del_saldo_externo():
    ctx = _sana(saldo_externo={"clasificacion": "cierra", "fuente": "portal", "diferencia": 0.0, "fechaSaldo": "2026-09-30"},
                referencia_access={"tiene": True, "explica": False, "diferencia": 50000.0})
    c3 = _por_codigo(ctx)["C3"]
    assert c3["cumple"] is True and "Access discrepa" in c3["medido"]


def test_c3_sin_estado_de_cuenta_cumple_como_excepcion():
    ctx = _sana(referencia_access={"tiene": False, "explica": False, "diferencia": None}, sin_estado=True)
    c3 = _por_codigo(ctx)["C3"]
    assert c3["cumple"] is True and c3["evidencia"] == "sin-estado"


def test_c3_se_cumple_con_el_access_solo_si_no_hay_hallazgos_de_saldo_ni_pagos_sin_factura():
    sana = _por_codigo(_sana())["C3"]
    assert sana["cumple"] is True and sana["evidencia"] == "access"
    assert _por_codigo(_sana(hallazgos={"contacto-duplicado"}))["C3"]["cumple"] is False
    assert _por_codigo(_sana(hallazgos={"impuesto-sin-boleta"}))["C3"]["cumple"] is False
    assert _por_codigo(_sana(pagos_pendientes=1, pagos_importe_pendiente=100.0))["C3"]["cumple"] is False


def test_los_hallazgos_de_imputacion_no_invalidan_la_evidencia_del_access_pero_si_impiden_cerrar():
    """Si invalidaran la evidencia, el FIFO (que los arregla) quedaría bloqueado por la puerta: sería un círculo."""
    ctx = _sana(hallazgos={"aplicacion-fuera-de-plazo"})
    assert _por_codigo(ctx)["C3"]["cumple"] is True
    c = criterios.evaluar(ctx)
    assert criterios.etapa_de(c, True) == "E5"
    assert [x["codigo"] for x in criterios.faltantes_para_cerrar(c)] == ["C5"]


def test_c3_sin_ninguna_evidencia_no_cumple():
    ctx = _sana(referencia_access={"tiene": False, "explica": False, "diferencia": None})
    assert _por_codigo(ctx)["C3"]["cumple"] is False


def test_imputaciones_incompletas_o_hallazgos_de_plazo_incumplen_c5():
    for ctx in (_sana(imputaciones={"sanas": False}), _sana(hallazgos={"aplicacion-fuera-de-plazo"}), _sana(hallazgos={"sobrepago"}),
                _sana(hallazgos={"nota-sin-imputar"})):
        assert _por_codigo(ctx)["C5"]["cumple"] is False


def test_c5_no_aplica_a_clientes_o_cuentas_en_dolares():
    assert _por_codigo(_sana(imputaciones={"sanas": None}))["C5"]["cumple"] is None


def test_retenciones_sin_certificado_o_impuestos_sin_boleta_incumplen_c6():
    assert _por_codigo(_sana(retenciones_sin_certificado=2))["C6"]["cumple"] is False
    assert _por_codigo(_sana(hallazgos={"impuesto-sin-boleta"}))["C6"]["cumple"] is False


def test_una_cuenta_reabierta_incumple_c7():
    assert _por_codigo(_sana(reabierta=True))["C7"]["cumple"] is False


def test_los_criterios_que_no_aplican_no_impiden_cerrar():
    assert criterios.faltantes_para_cerrar(criterios.evaluar(_sana(imputaciones={"sanas": None}))) == []


def test_la_etapa_es_la_primera_con_un_criterio_sin_cumplir():
    ctx = _sana(pagos_pendientes=2, pagos_importe_pendiente=10.0, hallazgos={"doble-descuento-tarjeta", "aplicacion-fuera-de-plazo"})
    assert criterios.etapa_de(criterios.evaluar(ctx), True) == "E1"


def test_la_puerta_del_fifo_exige_e1_a_e4_pero_no_e0_ni_e5():
    c = criterios.evaluar(_sana(tiene_inventario=False, hallazgos={"aplicacion-fuera-de-plazo"}))
    puede, etapa, faltan = criterios.previos_al_fifo(c)
    assert puede is True and etapa is None and faltan == []
    puede, etapa, faltan = criterios.previos_al_fifo(criterios.evaluar(_sana(pagos_pendientes=1, pagos_importe_pendiente=5.0)))
    assert puede is False and etapa == "E1" and faltan[0]["codigo"] == "C1"
    puede, etapa, _ = criterios.previos_al_fifo(criterios.evaluar(_sana(hallazgos={"doble-descuento-tarjeta"})))
    assert puede is False and etapa == "E3"


def test_las_imputaciones_de_tarjeta_duplicadas_incumplen_c4_y_la_etapa_es_e3():
    ctx = _sana(tarjetas_duplicadas=5)
    c4 = _por_codigo(ctx)["C4"]
    assert c4["cumple"] is False and "5 imputaciones de tarjeta que sobran" in c4["medido"]
    assert criterios.etapa_de(criterios.evaluar(ctx), True) == "E3"
    assert _por_codigo(_sana(tarjetas_duplicadas=0))["C4"]["cumple"] is True
