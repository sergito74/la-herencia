"""050 (17/11/2026): el control de integridad detecta los errores que encontró la revisión de especialistas."""

from src.features.imputacion import control_integridad as C


def test_renglon_que_reparte_de_mas_o_de_menos():
    renglones = [{"id": 1, "importePesos": 1000.0}, {"id": 2, "importePesos": 500.0},
                 {"id": 3, "importePesos": -200.0}, {"id": 4, "importePesos": 300.0, "esFlete": 1}]
    fracciones = {1: 1000.0, 2: 659.35, 3: -200.0}  # 2: intereses de Cargill repartidos de más
    malos = C.renglones_que_no_cierran(renglones, fracciones, {})
    assert [r["id"] for r in malos] == [2]


def test_flete_atribuido_cuenta_en_lo_esperado():
    assert C.renglones_que_no_cierran([{"id": 1, "importePesos": 1000.0}], {1: 1100.0}, {1: 100.0}) == []


def test_contratista_contado_por_dos_caminos():
    lineas = [{"concepto": "Contratista", "origen": "OrdenTrabajo", "idCompra": 10, "idDetalleCompra": None},
              {"concepto": "Compra", "origen": "Alcance050", "idCompra": 10, "idDetalleCompra": 101}]
    assert C.dobles_en_resultado(lineas) == [("contratista", 10)]


def test_imputacion_manual_vieja_y_esquema_nuevo():
    lineas = [{"concepto": "x", "origen": "Compra", "idCompra": 20, "idDetalleCompra": 201},
              {"concepto": "Insumo", "origen": "Alcance050", "idCompra": 20, "idDetalleCompra": 201}]
    assert C.dobles_en_resultado(lineas) == [("manual", 201)]


def test_sin_dobles():
    lineas = [{"concepto": "Contratista", "origen": "OrdenTrabajo", "idCompra": 10, "idDetalleCompra": None},
              {"concepto": "Insumo", "origen": "Alcance050", "idCompra": 11, "idDetalleCompra": 111}]
    assert C.dobles_en_resultado(lineas) == []
