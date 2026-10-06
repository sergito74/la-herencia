"""Anular imputaciones y notas de ajuste — 035 (T050, T051). Validaciones puras: no escriben."""

from datetime import date, timedelta

import pytest

from src.features.auditoria_cuentas import ajustes as a
from src.features.auditoria_cuentas import correcciones as c


def test_pedido_de_anulacion():
    assert c.validar_pedido([3, 1, 3, 2], "No corresponde") == [1, 2, 3]
    for ids, motivo in [([], "x"), ([1], " "), ([1], "")]:
        with pytest.raises(c.CorreccionError) as e:
            c.validar_pedido(ids, motivo)
        assert e.value.codigo == 422
    with pytest.raises(c.CorreccionError):
        c.validar_pedido(list(range(c.MAX_APLICACIONES + 1)), "x")


def test_validar_nota_de_ajuste():
    hoy = date.today()
    a.validar("debito", 100.0, "Diferencia de cambio", "Pesos", hoy)
    a.validar("credito", 0.01, "Redondeo", "Dolares", hoy)
    for args in [("otro", 100.0, "x", "Pesos", hoy), ("debito", 0.0, "x", "Pesos", hoy), ("debito", -5.0, "x", "Pesos", hoy),
                 ("debito", 100.0, " ", "Pesos", hoy), ("debito", 100.0, "x", "Euros", hoy), ("debito", 100.0, "x", "Pesos", hoy + timedelta(days=1))]:
        with pytest.raises(a.AjusteError) as e:
            a.validar(*args)
        assert e.value.codigo == 422


def test_el_neto_mas_iva_da_el_importe():
    assert round(a.neto_de_iva(1210.0) * 1.21, 2) == 1210.0
    assert round(a.neto_de_iva(332.87) * 1.21, 2) == 332.87
