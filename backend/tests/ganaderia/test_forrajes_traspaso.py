"""052 SC-005: el costo que sale del resultado agrícola es exactamente el que pasa a Ganadería (sin base de datos)."""

from src.features.resultado_cultivo.resultado import pasa_a_ganaderia


def _c(nombre, idc, costo, silo=0.0):
    return {"idCultivo": idc, "cultivo": nombre, "costoTotalPesos": costo * 1000, "costoTotalDolares": costo,
            "costoSiloGanaderiaPesos": silo * 1000, "costoSiloGanaderiaDolares": silo}


def test_cultivos_ganaderos_enteros_mas_silo_de_los_agricolas():
    ganaderos = [_c("Sorgo", 5, 100.0), _c("Maiz diferido", 2, 50.0)]
    agricolas = [_c("Maiz", 1, 300.0, silo=40.0), _c("Soja primera", 3, 200.0)]
    p = pasa_a_ganaderia(ganaderos, agricolas)
    assert p["dolares"] == 190.0
    assert {(i["cultivo"], i["concepto"]) for i in p["items"]} == {
        ("Sorgo", "Cultivo ganadero"), ("Maiz diferido", "Cultivo ganadero"), ("Maiz", "Picado para silo")}


def test_invariante_costo_total():
    ganaderos = [_c("Sorgo", 5, 100.0)]
    agricolas = [_c("Maiz", 1, 300.0, silo=40.0)]
    antes = 300.0 + 100.0  # el silo se restaba del maíz y no aparecía en ningún lado
    despues_agricola = 300.0
    p = pasa_a_ganaderia(ganaderos, agricolas)
    assert round(antes + 40.0, 2) == round(despues_agricola + p["dolares"], 2)


def test_sin_ganaderos_no_pasa_nada():
    assert pasa_a_ganaderia([], [_c("Soja primera", 3, 200.0)])["dolares"] == 0.0
