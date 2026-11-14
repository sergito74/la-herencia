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
    assert d["accion"] == "revisar" and "Varias" in d["motivo"]


def test_entrega_parcial_100_mas_100_vincula_los_dos():
    d = va.decidir(_r(), [_c(10, 100), _c(11, 100)])
    assert d["accion"] == "vincular" and sorted(i["idDetalleRemito"] for i in d["items"]) == [10, 11]


def test_nunca_supera_la_cantidad_del_renglon():
    d = va.decidir(_r(), [_c(10, 250)])
    assert d["accion"] == "revisar"
    assert va.decidir(_r(0), [_c(10, 200)])["accion"] == "nada"


def test_remito_fuera_de_ventana_no_es_candidato():
    assert va.decidir(_r(), [_c(10, 200, date(2026, 8, 1))])["accion"] == "nada"
    assert va.decidir(_r(), [_c(10, 200, date(2026, 12, 15))])["accion"] == "nada"
    assert va.decidir(_r(), [_c(10, 200, date(2026, 12, 9))])["accion"] == "vincular"
