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


# ---- 17/11/2026: controles de razonabilidad y fotos de campañas cerradas
from datetime import date


def test_campania_anterior():
    assert C.campania_anterior("2025/2026") == "2024/2025"
    assert C.campania_anterior("2026") == "2025"
    assert C.campania_anterior("No Aplica") is None


def test_fuera_de_rango():
    assert C.fuera_de_rango(803, 300)  # el seguro cobrado sumado como costo
    assert C.fuera_de_rango(100, 300)
    assert not C.fuera_de_rango(400, 300)
    assert not C.fuera_de_rango(30, 300)  # casi sin costo: no alarma


def test_campania_cerrada_y_siembra():
    hoy = date(2026, 11, 17)
    assert C.campania_cerrada("2025/2026", hoy) and C.campania_cerrada("2024/2025", hoy)
    assert not C.campania_cerrada("2026/2027", hoy)
    assert C.campania_cerrada("2025", hoy) and not C.campania_cerrada("2026", hoy)
    assert not C.siembra_terminada("2026/2027", hoy)
    assert C.siembra_terminada("2025/2026", hoy) and C.siembra_terminada("2026", hoy)


def test_diferencias_por_documento():
    antes = {"D1": 100.0, "D2": 50.0}
    ahora = {"D1": 100.0, "D2": 80.0, "C9|": 10.0}
    assert C.diferencias(antes, ahora) == {"D2": 30.0, "C9|": 10.0}
    assert C.diferencias(antes, dict(antes)) == {}


def test_clave_documento():
    assert C.clave_documento({"idDetalleCompra": 5}) == "D5"
    assert C.clave_documento({"idCompra": 7, "idOrdenTrabajo": 3}) == "C7|3"
    assert C.clave_documento({"idOrdenTrabajo": 3, "concepto": "Insumo"}) == "O3|Insumo"
