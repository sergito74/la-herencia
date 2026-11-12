"""Regla de Sergio (12/11/2026): en compras con cuotas, la retención cancela la cuota siguiente al adelanto."""
from datetime import date
from decimal import Decimal as D

from src.features.ordenes_pago.repository import _cuotas

L = [(date(2026, 11, 13), 2500000), (date(2026, 11, 30), 2424125), (date(2026, 12, 14), 2424125.13)]


def saldos(pagado, retenido=D(0)):
    return [c["saldo"] for c in _cuotas(L, D("7348250.13"), D(pagado), None, retenido)]


def test_adelanto_completo_y_retencion_en_la_cuota_2():
    assert saldos("2600000", D("100000")) == [D("0.00"), D("2324125.00"), D("2424125.13")]


def test_sin_retencion_cubre_la_mas_vieja():
    assert saldos("3000000") == [D("0.00"), D("1924125.00"), D("2424125.13")]


def test_retencion_que_supera_la_cuota_2_sigue_en_la_3():
    assert saldos("5000000", D("2500000")) == [D("0.00"), D("0.00"), D("2348250.13")]


def test_sin_importes_reparte_en_partes_iguales():
    lista = [(d, None) for d, _ in L]
    assert [c["importe"] for c in _cuotas(lista, D("300"), D(0))] == [D("100.00"), D("100.00"), D("100.00")]
