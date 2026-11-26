"""052 T026: el silo va al período en que se consume; sin registro, estimado al ejercicio siguiente."""

from datetime import date

from src.features.ganaderia import reservas


def test_sin_consumo_registrado_estima_ejercicio_siguiente():
    r = reservas.imputar(1000, 10, 2024, [], None, "ejercicio")
    assert [(x["periodo"], x["pesos"]) for x in r] == [(2025, 1000)]
    assert "estimado" in r[0]["detalle"]


def test_consumo_registrado_va_al_periodo_de_su_fecha_y_el_resto_no_es_costo():
    cons = [{"fecha": date(2025, 6, 1), "pct": 30}, {"fecha": date(2026, 11, 26), "pct": 20}]
    r = reservas.imputar(1000, 10, 2024, cons, None, "ejercicio")
    assert [(x["periodo"], round(x["pesos"])) for x in r] == [(2025, 300), (2026, 200)]


def test_consumo_en_kg():
    assert reservas.fraccion({"kg": 250, "pct": None}, 1000) == 0.25
