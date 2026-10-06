"""Créditos entre resúmenes: fixtures puros, sin escrituras en WC."""
from src.features.tarjetas.compensaciones import calcular_compensaciones


def resumen(ident, total, pagado=0):
    return dict(idResumen=ident, codigo=str(ident), fechaCierre=f"2025-{ident:02}-01",
                total=total, pagado=pagado)


def test_mayo_se_cancela_con_dos_creditos_anteriores_y_pago_real():
    rows = [resumen(1, -3.72), resumen(2, -371.30), resumen(5, 605, 229.98)]
    r = calcular_compensaciones(rows)
    assert r[5]["saldoPendiente"] == 0
    assert r[5]["creditoAplicado"] == 375.02
    assert r[5]["compensaciones"] == [
        {"idResumen": 1, "codigo": "1", "importe": 3.72},
        {"idResumen": 2, "codigo": "2", "importe": 371.3},
    ]
    assert r[1]["creditoDisponible"] == r[2]["creditoDisponible"] == 0
    assert rows[-1]["pagado"] == 229.98


def test_sobrepago_octubre_se_distribuye_una_sola_vez():
    r = calcular_compensaciones([resumen(1, 9109.62, 10020.58),
                                resumen(2, 399.30), resumen(3, 2276579.17, 2276067.51),
                                resumen(4, 100)])
    assert r[2]["creditoAplicado"] == 399.3
    assert r[3]["creditoAplicado"] == 511.66
    assert r[4]["saldoPendiente"] == 100
    assert r[1]["creditoDisponible"] == 0


def test_credito_posterior_no_oculta_deuda_anterior():
    r = calcular_compensaciones([resumen(2, -200), resumen(1, 100), resumen(3, 50)])
    assert r[1]["saldoPendiente"] == 100
    assert r[3]["creditoAplicado"] == 50
    assert r[2]["creditoDisponible"] == 150


def test_pagos_fraccionados_con_decimales_y_recalculo_sin_pago():
    assert calcular_compensaciones([resumen(1, 785222.12, 536550.706 + 248671.414)])[1]["saldoPendiente"] == 0
    assert calcular_compensaciones([resumen(1, 785222.12)])[1]["saldoPendiente"] == 785222.12
    assert calcular_compensaciones([]) == {}


def test_resumen_historico_no_deja_pendiente_ni_credito():
    historico = {**resumen(1, 100, 40), "estado": "Cerrado"}
    sobrante = {**resumen(2, 10, 50), "estado": "Cerrado"}
    r = calcular_compensaciones([historico, sobrante, resumen(3, 20)])
    assert r[1] == {"creditoAplicado": 0.0, "saldoPendiente": 0.0, "creditoDisponible": 0.0, "compensaciones": []}
    assert r[2]["creditoDisponible"] == 0.0
    assert r[3]["saldoPendiente"] == 20 and r[3]["creditoAplicado"] == 0
