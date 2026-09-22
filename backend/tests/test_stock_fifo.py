from datetime import date

from src.features.remitos.costeo import costo_unitario_renglon
from src.features.remitos.stock_fifo import Capa, Salida, asignar_fifo


def _capa(id_, dia, cant, costo, orden=0):
    return Capa(id=id_, fecha=date(2025, 1, dia), cantidad=cant, costo_unitario=costo, orden=orden)


def _sal(id_, dia, cant, tipo="orden", orden=0):
    return Salida(id=id_, fecha=date(2025, 2, dia), cantidad=cant, tipo=tipo, orden=orden)


def test_una_salida_consume_primero_la_capa_mas_antigua():
    r = asignar_fifo([_capa("B", 10, 100, 12.0), _capa("A", 1, 50, 10.0)], [_sal("S1", 1, 70)])
    c = r["consumos"]["S1"]
    assert [(i["capa"], i["cantidad"]) for i in c["items"]] == [("A", 50), ("B", 20)]
    assert c["costo"] == 50 * 10.0 + 20 * 12.0
    assert r["restantes"] == {"A": 0, "B": 80}
    assert r["existencia"] == 80 and r["valor"] == 80 * 12.0


def test_salidas_sucesivas_avanzan_por_las_capas():
    r = asignar_fifo([_capa("A", 1, 10, 5.0), _capa("B", 2, 10, 7.0)], [_sal("S1", 1, 6), _sal("S2", 2, 6)])
    assert r["consumos"]["S1"]["costo"] == 30.0
    assert r["consumos"]["S2"]["costo"] == 4 * 5.0 + 2 * 7.0


def test_capa_sin_factura_deja_la_salida_provisoria_y_se_recalcula_al_vincular():
    capas = [_capa("A", 1, 10, None)]
    r = asignar_fifo(capas, [_sal("S1", 1, 4)])
    assert r["consumos"]["S1"]["provisoria"] and r["consumos"]["S1"]["cantidad_costo_pendiente"] == 4
    assert r["consumos"]["S1"]["costo"] == 0 and r["cantidad_costo_pendiente"] == 6
    # vinculada la factura, el mismo cálculo ya no es provisorio
    r2 = asignar_fifo([_capa("A", 1, 10, 3.0)], [_sal("S1", 1, 4)])
    assert not r2["consumos"]["S1"]["provisoria"] and r2["consumos"]["S1"]["costo"] == 12.0


def test_mezcla_de_capa_con_costo_y_sin_costo():
    r = asignar_fifo([_capa("A", 1, 5, 2.0), _capa("B", 2, 5, None)], [_sal("S1", 1, 8)])
    c = r["consumos"]["S1"]
    assert c["costo"] == 10.0 and c["cantidad_costo_pendiente"] == 3 and c["provisoria"]


def test_salida_mayor_que_lo_ingresado_queda_sin_cobertura_y_stock_negativo():
    r = asignar_fifo([_capa("A", 1, 10, 4.0)], [_sal("S1", 1, 15)])
    assert r["consumos"]["S1"]["sin_cobertura"] == 5
    assert r["existencia"] == -5 and r["valor"] == 0


def test_orden_de_carga_desempata_capas_del_mismo_dia():
    r = asignar_fifo([_capa("B", 1, 5, 9.0, orden=2), _capa("A", 1, 5, 1.0, orden=1)], [_sal("S1", 1, 5)])
    assert r["consumos"]["S1"]["items"][0]["capa"] == "A"


def test_sin_movimientos():
    r = asignar_fifo([], [])
    assert r["existencia"] == 0 and r["valor"] == 0


def _v(cant, compra, suma, precio, moneda="Pesos", tc=None):
    return {"cantidadRemitida": cant, "cantidadCompra": compra, "sumaRemitidaLineaCompra": suma,
            "precioUnitario": precio, "moneda": moneda, "tipoDeCambio": tc}


def test_costo_directo_cuando_las_cantidades_coinciden():
    costo, estado, vinc = costo_unitario_renglon([_v(20, 20, 20, 100.0)], 20)
    assert costo == 100.0 and estado == "completo" and vinc == 20


def test_costo_en_dolares_usa_el_tipo_de_cambio_de_la_factura():
    costo, _, _ = costo_unitario_renglon([_v(10, 10, 10, 8.0, "Dolares", 1200)], 10)
    assert costo == 9600.0


def test_prorrateo_cuando_la_factura_esta_en_otra_unidad():
    # factura: 1 bidón a $ 3.000; remito: 15 litros -> $ 200 por litro
    costo, estado, _ = costo_unitario_renglon([_v(15, 1, 15, 3000.0)], 15)
    assert round(costo, 4) == 200.0 and estado == "completo"


def test_promedio_ponderado_entre_dos_facturas():
    costo, _, vinc = costo_unitario_renglon([_v(10, 10, 10, 100.0), _v(30, 30, 30, 200.0)], 40)
    assert costo == (10 * 100 + 30 * 200) / 40 and vinc == 40


def test_renglon_parcialmente_vinculado_y_sin_vinculos():
    assert costo_unitario_renglon([_v(10, 10, 10, 50.0)], 40)[1] == "parcial"
    assert costo_unitario_renglon([], 40) == (None, "pendiente", 0.0)
