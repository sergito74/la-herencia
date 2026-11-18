from src.features.tesoreria.informes_tarjetas import estado_linea


def test_estado_de_consumo():
    assert estado_linea(None, 100, 100, True, "YPF", "Combustible") == "Conciliado"
    assert estado_linea(None, 40, 100, True, "YPF", "Combustible") == "Parcial"
    assert estado_linea("DiferenciaAceptada", 98, 100, True, "YPF", "x") == "Conciliado con diferencia"
    assert estado_linea("SinDocumento", 0, 100, False, None, "x") == "Sin documento"
    assert estado_linea(None, 0, 50, False, None, "IVA 21%") == "Cargo de la tarjeta"
    assert estado_linea(None, 0, 50, False, "YPF", "Combustible") == "Pendiente"
