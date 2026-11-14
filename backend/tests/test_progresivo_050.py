"""Imputación progresiva (050 US9): el glifosato del quickstart §3 y los renglones directos."""

from src.features.imputacion import progresivo as pg


def test_glifosato_200_l_uso_80_quedan_120_en_stock_y_cierra_al_centavo():
    # 200 l a $10.000 + $100.000 de flete → $10.500/l. Una orden usa 80 l.
    fr = [{"idOrdenTrabajo": 1, "idCultivo": 3, "idCampania": 32, "importe": 840_000.0},
          {"esStock": True, "importe": 1_260_000.0, "cantidad": 120}]
    total = pg.total_renglon({"cantidad": 200, "precio": 10_000, "moneda": "Pesos", "tc": None}, 100_000)
    fr, _ = pg.asignar_partes(fr, 3, False, None)
    out, motivo = pg.decidir_estado(fr, total, None)
    assert total == 2_100_000 and motivo is None
    assert all(f["estado"] == "Aprobada" for f in out) and out[0]["idParte"] == 3


def test_si_no_cierra_al_centavo_queda_pendiente():
    out, motivo = pg.decidir_estado([{"importe": 99.0, "idCultivo": 1}], 100.0, None)
    assert motivo and out[0].get("estado") is None


def test_silobolsa_segun_uso():
    fr = [{"idCultivo": 7, "importe": 1}, {"idCultivo": 3, "importe": 1}, {"idCentroCosto": 2, "importe": 1}]
    out, motivo = pg.asignar_partes(fr, None, True, 2)
    assert out[0]["idParte"] is None and out[1]["idParte"] == pg.PARTE_COMERCIALIZACION and out[2]["esGanaderia"]
    assert motivo is None
    _, motivo = pg.asignar_partes([{"importe": 1}], None, True, 2)
    assert motivo


def test_directo_por_destino():
    assert pg.fracciones_directo({"destino": "Cultivo", "idParte": 7, "idCultivo": 3, "idCampania": 32}, 500, 3)[0]["idCultivo"] == 3
    assert pg.fracciones_directo({"destino": "Estructura", "idParte": None}, 500, 3)[0]["idCentroCosto"] == 3
    assert pg.fracciones_directo({"destino": "Financiero", "idParte": None}, 500, 3) == []
