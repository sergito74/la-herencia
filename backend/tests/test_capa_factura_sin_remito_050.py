"""Capa FC de factura sin remito (050 R-03)."""

from datetime import datetime

from src.features.remitos import capas_factura, stock_datos


def _sin_base(monkeypatch, renglones):
    monkeypatch.setattr(stock_datos, "fetch_all", lambda *a, **k: [])
    monkeypatch.setattr(stock_datos, "unidades_base", lambda: {})
    monkeypatch.setattr(stock_datos, "equivalencias", lambda: {})
    monkeypatch.setattr(capas_factura, "renglones_sin_remito", lambda id_producto=None: renglones)
    monkeypatch.setattr(capas_factura, "flete_por_renglon", lambda: {})


def test_renglon_sin_remito_genera_capa_a_la_fecha_de_la_factura(monkeypatch):
    _sin_base(monkeypatch, [{"idDetalleCompra": 9, "idCompra": 1, "idProducto": 50, "unidad": "LTS", "cantidad": 200,
                             "precio": 10, "moneda": "Dolares", "tc": 1000, "fecha": datetime(2026, 11, 10), "nroDocumento": "A-1"}])
    st = stock_datos.calcular_stock(50)
    capa = st[50]["capas"][0]
    assert capa["id"] == "FC9" and capa["origen"] == "factura" and capa["cantidad"] == 200
    assert capa["costoUnitario"] == 10_000 and str(capa["fecha"]) == "2026-11-10"


def test_al_vincular_el_remito_la_capa_desaparece(monkeypatch):
    _sin_base(monkeypatch, [])  # renglones_sin_remito excluye los que tienen tblRemitoCompra
    assert stock_datos.calcular_stock(50) == {}
