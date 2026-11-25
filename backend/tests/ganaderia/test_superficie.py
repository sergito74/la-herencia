"""052 FR-013: ha ganaderas efectivas por meses de uso (método Sup Ganadera de Sergio)."""

from src.features.ganaderia import periodos
from src.features.ganaderia.superficie import calcular, ventana

CAL = {3: (11, 4), 4: (1, 4), 8: (6, 12)}  # soja 1.ª, soja 2.ª, trigo
LOTES = [{"idLote": 1, "lote": "3B", "superficie": 55.2}, {"idLote": 2, "lote": "1A", "superficie": 20.5},
         {"idLote": 3, "lote": "7A", "superficie": 14.2}]


def test_ventana_soja_primera_cruza_el_anio():
    v = ventana(2025, 11, 4)
    assert (2025, 11) in v and (2026, 4) in v and len(v) == 6


def test_soja_primera_ejercicio_abril_marzo():
    plan = [{"idLote": 1, "idCultivo": 3, "anioCampania": 2025, "agricola": 1}]
    f = {x["lote"]: x for x in calcular(LOTES, plan, CAL, {}, 2025)}
    assert f["3B"]["mesesGanaderos"] == 7  # abr–oct 2025 ganadero; nov 2025–mar 2026 soja
    assert f["1A"]["mesesGanaderos"] == 12  # sin plan agrícola (pastura / campo natural)


def test_trigo_y_soja_segunda_en_el_mismo_lote():
    plan = [{"idLote": 3, "idCultivo": 8, "anioCampania": 2025, "agricola": 1},
            {"idLote": 3, "idCultivo": 4, "anioCampania": 2025, "agricola": 1}]
    f = calcular(LOTES, plan, CAL, {}, 2025)[2]
    assert f["mesesGanaderos"] == 2  # abr–may 2025 libres; jun–dic trigo; ene–mar soja 2.ª


def test_ajuste_manual_manda():
    f = calcular(LOTES, [], CAL, {(2, periodos.etiqueta(2025)): (6, "Bajo anegado")}, 2025)[1]
    assert (f["mesesGanaderos"], f["origen"]) == (6, "ajuste")


def test_cultivo_ganadero_no_saca_meses():
    plan = [{"idLote": 2, "idCultivo": 9, "anioCampania": 2025, "agricola": 0}]
    assert calcular(LOTES, plan, CAL, {}, 2025)[1]["mesesGanaderos"] == 12


def test_periodos():
    assert periodos.de_fecha("2026-03-31") == "2025/26" and periodos.de_fecha("2026-04-01") == "2026/27"
    assert periodos.de_fecha("2026-06-30", "campania") == "2025/26"
