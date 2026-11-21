"""Costo de un remito en kg vinculado a renglones de factura en toneladas (21/11/2026)."""

from src.features.remitos.stock_datos import _unidad_factura_a_remito


def _v(cant_remitida, cant_compra, suma, unidad="TON"):
    return {"cantidadRemitida": cant_remitida, "cantidadCompra": cant_compra, "sumaRemitidaLineaCompra": suma, "unidadCompra": unidad}


def test_granel_repartido_entre_remitos_convierte_toneladas_a_kg():
    # Remito de 14.660 kg cubierto por 14,66 t de dos renglones; uno de ellos repartido con otro remito.
    vinculos = [_v(0.66, 0.7188, 0.66), _v(14.0, 20.0, 20.0)]
    total = 14.66 * 100_000.0  # $ 100.000 por tonelada
    costo, estado, vinculada = _unidad_factura_a_remito(vinculos, "KGS", 14660.0, total / 14.66, "parcial", 14.66)
    assert round(costo, 2) == 100.0  # $ 100 por kg
    assert estado == "completo"
    assert vinculada == 14660.0


def test_cobertura_parcial_queda_parcial():
    vinculos = [_v(10.0, 10.0, 10.0)]
    costo, estado, vinculada = _unidad_factura_a_remito(vinculos, "KGS", 20000.0, 500.0, "parcial", 10.0)
    assert round(costo, 4) == 0.5
    assert estado == "parcial"
    assert vinculada == 10000.0


def test_misma_unidad_no_cambia():
    vinculos = [_v(100.0, 100.0, 100.0, unidad="LTS")]
    assert _unidad_factura_a_remito(vinculos, "LTS", 100.0, 7.0, "completo", 100.0) == (7.0, "completo", 100.0)
