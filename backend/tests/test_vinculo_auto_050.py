"""Vínculo automático remito↔factura (050 R-04): exacto, único, sin tolerancias."""

from datetime import date

from src.features.remitos import vinculo_auto as va

F = date(2026, 11, 10)


def _c(id_, disp, fecha=F):
    return {"idDetalleRemito": id_, "fecha": fecha, "disponible": disp, "factor": 1.0}


def _r(pend=200):
    return {"idDetalleCompra": 1, "fecha": F, "pendiente": pend}


def test_coincidencia_exacta_unica_vincula():
    d = va.decidir(_r(), [_c(10, 200), _c(11, 50)])
    assert d["accion"] == "vincular" and [i["idDetalleRemito"] for i in d["items"]] == [10]


def test_dos_combinaciones_posibles_van_a_revision():
    d = va.decidir(_r(), [_c(10, 200), _c(11, 200)])
    assert d["accion"] == "revisar" and "Varios" in d["motivo"]


def test_entrega_parcial_100_mas_100_vincula_los_dos():
    d = va.decidir(_r(), [_c(10, 100), _c(11, 100)])
    assert d["accion"] == "vincular" and sorted(i["idDetalleRemito"] for i in d["items"]) == [10, 11]


def test_nunca_supera_la_cantidad_del_renglon():
    d = va.decidir(_r(), [_c(10, 250)])
    assert d["accion"] == "revisar"
    assert va.decidir(_r(0), [_c(10, 200)])["accion"] == "nada"


def test_remito_fuera_de_ventana_no_es_candidato():
    # Ventana de 270 días entre factura y remito (Bayá Casal factura hasta 199 días después).
    assert va.decidir(_r(), [_c(10, 200, date(2026, 2, 1))])["accion"] == "nada"
    assert va.decidir(_r(), [_c(10, 200, date(2027, 9, 1))])["accion"] == "nada"
    assert va.decidir(_r(), [_c(10, 200, date(2026, 4, 30))])["accion"] == "vincular"


def test_entre_dos_iguales_gana_el_mas_cercano_anterior():
    d = va.decidir(_r(), [_c(10, 200, date(2026, 9, 1)), _c(11, 200, date(2026, 11, 1))])
    assert d["accion"] == "vincular" and d["items"][0]["idDetalleRemito"] == 11


def test_cantidad_con_tolerancia_de_uno_por_ciento():
    assert va.decidir(_r(), [_c(10, 201.5)])["accion"] == "vincular"


def test_familia_de_fertilizante():
    assert va.familia_fertilizante("MZCLA 7N-39P-00-5S") == "ARRANCADOR"
    assert va.familia_fertilizante("YPF FERTILIZANTES NP 326") == "ARRANCADOR"
    assert va.familia_fertilizante("UREA GRANULADA GRANEL") == "UREA"
