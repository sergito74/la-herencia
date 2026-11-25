"""052 FR-013: ha ganaderas efectivas (Sergio 25/11/2026: total = loteo vigente; antes de 2021/22, su planilla)."""

from src.features.ganaderia import periodos
from src.features.ganaderia.superficie import calcular, ventana

CAL = {3: (11, 4), 4: (1, 4), 8: (6, 12)}  # soja 1.ª, soja 2.ª, trigo
LOTES = [{"idLote": 1, "lote": "3B", "superficie": 60.0}, {"idLote": 2, "lote": "1A", "superficie": 20.0},
         {"idLote": 3, "lote": "7A", "superficie": 12.0}]


def test_ventana_soja_primera_cruza_el_anio():
    v = ventana(2025, 11, 4)
    assert (2025, 11) in v and (2026, 4) in v and len(v) == 6


def test_soja_primera_descuenta_sus_meses():
    plan = [{"idLote": 1, "idCultivo": 3, "anioCampania": 2025, "agricola": 1}]
    r = calcular(400.0, None, LOTES, plan, CAL, {}, 2025)
    assert r["haEfectivas"] == 375.0  # 60 ha × 5 meses (nov–mar del ejercicio) / 12 = 25


def test_trigo_y_soja_segunda_cuentan_una_vez_por_mes():
    plan = [{"idLote": 3, "idCultivo": 8, "anioCampania": 2025, "agricola": 1},
            {"idLote": 3, "idCultivo": 4, "anioCampania": 2025, "agricola": 1}]
    r = calcular(400.0, None, LOTES, plan, CAL, {}, 2025)
    assert r["haEfectivas"] == 390.0  # 12 ha × 10 meses / 12


def test_cultivo_ganadero_no_descuenta():
    plan = [{"idLote": 2, "idCultivo": 9, "anioCampania": 2025, "agricola": 0}]
    assert calcular(400.0, None, LOTES, plan, CAL, {}, 2025)["haEfectivas"] == 400.0


def test_ajuste_manual_manda():
    r = calcular(400.0, None, LOTES, [], CAL, {(2, periodos.etiqueta(2025)): (6, "Bajo anegado")}, 2025)
    assert r["haEfectivas"] == 390.0 and r["lotesAgricolas"][0]["origen"] == "ajuste"


def test_periodo_historico_usa_planilla():
    r = calcular(None, 223.9, LOTES, [], CAL, {}, 2018)
    assert (r["haEfectivas"], r["origen"]) == (223.9, "planilla")


def test_periodos():
    assert periodos.de_fecha("2026-03-31") == "2025/26" and periodos.de_fecha("2026-04-01") == "2026/27"
    assert periodos.de_fecha("2026-06-30", "campania") == "2025/26"
