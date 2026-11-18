from src.features.resultado_cultivo.superficies import base_por_ha


def test_sembrada_de_factura_es_denominador():
    s = base_por_ha(116.4, 104.0, 104.0)
    assert s["sembrada"] == 104.0 and not s["teorica"] and s["aprovechamiento"] == round(104 / 116.4, 4)


def test_sin_siembra_registrada_usa_bruta_teorica():
    s = base_por_ha(88.6, None, None)
    assert s["sembrada"] == 88.6 and s["teorica"] and s["aprovechamiento"] is None


def test_cosecha_mayor_que_siembra_manda_cosecha():
    s = base_por_ha(60.0, 50.0, 55.0)
    assert s["sembrada"] == 55.0 and s["segunCosecha"]


def test_cultivo_no_sembrado_no_tiene_superficie():
    s = base_por_ha(0.0, None, None, no_sembrada=76.4)
    assert s["noSembrado"] and s["sembrada"] == 0.0


def test_reparto_por_lote_proporcional_a_la_orden():
    from src.features.resultado_cultivo.superficies import repartir_por_lote

    r = repartir_por_lote({"1B1": 20.3, "3C": 9.2, "6": 12.7, "6A": 11.7, "6B": 3.9, "6C": 6.8, "8A": 13.5}, 70.0)
    assert r == {"1B1": 18.2, "3C": 8.2, "6": 11.4, "6A": 10.5, "6B": 3.5, "6C": 6.1, "8A": 12.1}
    assert round(sum(r.values()), 1) == 70.0 and repartir_por_lote({}, 70) == {}


def test_aviso_orden_y_factura_de_siembra():
    from src.features.imputacion.control_integridad import superficie_siembra_difiere

    assert superficie_siembra_difiere(78.1, 70.0) and not superficie_siembra_difiere(104.5, 104.0)
