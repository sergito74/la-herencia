"""Flete de insumos como costo de adquisición (050 R-06b)."""

from src.features.remitos import capas_factura


def test_flete_se_reparte_por_importe():
    partes = capas_factura.repartir_por_importe({1: 1_500_000, 2: 500_000}, 100_000)
    assert partes == {1: 75_000.0, 2: 25_000.0}


def test_un_uso_del_40_se_lleva_el_40_del_flete():
    unitario = capas_factura.costo_unitario_factura({"cantidad": 200, "precio": 10_000, "moneda": "Pesos"}, 100_000)
    assert unitario == 10_500  # 80 l (40%) → 840.000 = 800.000 de producto + 40.000 de flete
    assert unitario * 80 - 10_000 * 80 == 0.4 * 100_000


def test_flete_aparte_sin_relacionar_queda_pendiente():
    from src.features.imputacion import tamiz
    reglas = {5: {"destino": "CultivoStock", "idParte": 6, "regla": "FleteInsumo"}}
    r = {"idDetalleCompra": 1, "idRubro": 5, "producto": "Flete", "idFormulado": None, "idCultivo": None,
         "idCampania": None, "cantidad": 1, "precio": 100_000}
    assert tamiz.clasificar_renglon(r, reglas, [], {"particular": None, "tieneInsumos": False})["estado"] == "Pendiente"


def test_residuo_del_redondeo_va_al_mayor():
    partes = capas_factura.repartir_por_importe({1: 1, 2: 1, 3: 1}, 100)
    assert round(sum(partes.values()), 2) == 100
