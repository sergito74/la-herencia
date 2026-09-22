import pytest

from src.features.ordenes import distribucion


def _dist(dosis, superficie, aplicar=True):
    return {"dosisHa": dosis, "superficie": superficie, "aplicar": aplicar}


def test_calcular_cantidad_total_suma_dosis_por_superficie():
    total = distribucion.calcular_cantidad_total([_dist(2, 10), _dist(3, 5)])
    assert total == 2 * 10 + 3 * 5


def test_lote_no_aplicado_no_suma():
    total = distribucion.calcular_cantidad_total([_dist(2, 10), _dist(3, 5, aplicar=False)])
    assert total == 20


def test_validar_cierre_exacto_no_lanza():
    distribuciones = [_dist(2, 10), _dist(3, 5)]
    distribucion.validar_cierre(35, distribuciones)


def test_validar_cierre_sin_devolucion_lanza_si_no_cierra():
    with pytest.raises(ValueError):
        distribucion.validar_cierre(50, [_dist(2, 10), _dist(3, 5)])


def test_validar_cierre_con_devolucion_cierra():
    distribuciones = [_dist(2, 10)]  # repartido = 20
    distribucion.validar_cierre(25, distribuciones, devoluciones=[5])


def test_validar_cierre_lote_no_aplicado_no_cuenta_para_el_cierre():
    distribuciones = [_dist(2, 10), _dist(5, 5, aplicar=False)]
    # el lote no aplicado (25) no debe exigirse en el cierre
    distribucion.validar_cierre(20, distribuciones)
