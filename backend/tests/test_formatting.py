from src.formatting import formatear_moneda, formatear_monto


def test_miles_con_punto_y_decimales_con_coma():
    assert formatear_monto(1234) == "1.234,00"
    assert formatear_monto(1234567.891) == "1.234.567,89"
    assert formatear_monto(0) == "0,00"
    assert formatear_monto(999.995 + 0.0001) == "1.000,00"


def test_negativos_y_cero_negativo():
    assert formatear_monto(-1214016) == "-1.214.016,00"
    assert formatear_monto(-0.001) == "0,00"


def test_simbolos_de_moneda():
    assert formatear_moneda(1234.5) == "$ 1.234,50"
    assert formatear_moneda(-550272) == "$ -550.272,00"
    assert formatear_moneda(161.88, "Dolares") == "us$ 161,88"
