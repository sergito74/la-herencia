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
