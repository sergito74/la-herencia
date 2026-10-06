"""Cruces de devoluciones — 034 (T038). Fixtures puros, sin base."""

from datetime import date

import pytest

from src.features.tarjetas_cuenta import cruces as c


def _o(**kw):
    o = {"medio": "bna", "idMovimiento": 1, "fecha": date(2025, 9, 17), "importe": 966654.20}
    o.update(kw)
    return o


def _d(**kw):
    d = {"medio": "bna", "idMovimiento": 2, "fecha": date(2025, 9, 1), "importe": 966654.20}
    d.update(kw)
    return d


def test_sugiere_dentro_de_la_ventana_y_con_mismo_importe():
    s = c.emparejar([_o()], [_d()])
    assert len(s) == 1 and s[0]["diasDiferencia"] == 16 and s[0]["diferenciaImporte"] == 0
    assert c.emparejar([_o()], [_d(importe=966654.50)]) == []
    assert c.emparejar([_o(fecha=date(2025, 12, 1))], [_d()]) == []
    assert c.emparejar([_o(fecha=date(2025, 8, 1))], [_d()]) == []  # la devolución no puede ser anterior al débito


def test_ordena_por_puntaje_y_excluye_cruzados():
    cerca, lejos = _d(idMovimiento=3, fecha=date(2025, 9, 15)), _d(idMovimiento=4, fecha=date(2025, 8, 20))
    s = c.emparejar([_o()], [lejos, cerca])
    assert [x["destino"]["idMovimiento"] for x in s] == [3, 4]
    assert c.emparejar([_o()], [cerca], excluidos={("bna", 1)}) == []


def test_validar_devolucion_debito():
    c.validar_devolucion_debito(100, 100, 0)
    c.validar_devolucion_debito(40, 100, 60)
    with pytest.raises(c.CruceError) as e:
        c.validar_devolucion_debito(150, 100, 0)
    assert e.value.codigo == 422
    with pytest.raises(c.CruceError):
        c.validar_devolucion_debito(50, 100, 60)
    with pytest.raises(c.CruceError):
        c.validar_devolucion_debito(-5, 100, 0)


def test_validar_consumo_devolucion():
    c.validar_consumo_devolucion(100, 100, False, 0, 4, 4)
    for args in [(100, 100, False, 0, 3, 4), (100, 90, False, 0, 4, 4), (100, 100, True, 0, 4, 4), (100, 100, False, 100, 4, 4)]:
        with pytest.raises(c.CruceError) as e:
            c.validar_consumo_devolucion(*args)
        assert e.value.codigo == 422
