"""Cálculo de la Campaña "actual" (FR-001), sin tocar la base real."""

from datetime import date

from src.features.resultado_cultivo import campania_actual


def _campanias():
    return [
        {"id": 30, "texto": "2024/2025"},
        {"id": 31, "texto": "2025/2026"},
        {"id": 32, "texto": "2026/2027"},
        {"id": 20, "texto": "No Aplica"},
        {"id": 25, "texto": "2026"},
    ]


def test_campania_doble_anio_que_contiene_hoy(monkeypatch):
    monkeypatch.setattr(campania_actual, "fetch_all", lambda sql, *a, **k: _campanias())
    monkeypatch.setattr(campania_actual, "_hoy", lambda: date(2026, 9, 22))
    assert campania_actual.campania_actual() == 32


def test_campania_anio_simple_que_contiene_hoy(monkeypatch):
    monkeypatch.setattr(campania_actual, "fetch_all", lambda sql, *a, **k: [{"id": 25, "texto": "2026"}])
    monkeypatch.setattr(campania_actual, "_hoy", lambda: date(2026, 3, 1))
    assert campania_actual.campania_actual() == 25


def test_no_aplica_no_es_parseable_y_cae_al_resguardo(monkeypatch):
    monkeypatch.setattr(campania_actual, "fetch_all", lambda sql, *a, **k: [{"id": 20, "texto": "No Aplica"}])
    monkeypatch.setattr(campania_actual, "_campania_mas_reciente_con_datos", lambda: 99)
    assert campania_actual.campania_actual() == 99


def test_campania_doble_anio_gana_a_una_simple_superpuesta(monkeypatch):
    """Hallazgo real durante la implementación: "2026" y "2026/2027" pueden
    contener la misma fecha de hoy simultáneamente, ambas con datos reales
    en WC — se prioriza el formato agrícola típico "YYYY/YYYY+1"."""
    monkeypatch.setattr(campania_actual, "fetch_all", lambda sql, *a, **k: _campanias())
    monkeypatch.setattr(campania_actual, "_hoy", lambda: date(2026, 9, 22))
    assert campania_actual.campania_actual() == 32


def test_sin_ninguna_coincidencia_cae_a_la_mas_reciente_con_datos(monkeypatch):
    monkeypatch.setattr(campania_actual, "fetch_all", lambda sql, *a, **k: [{"id": 1, "texto": "2009/2010"}])
    monkeypatch.setattr(campania_actual, "_hoy", lambda: date(2026, 9, 22))
    monkeypatch.setattr(campania_actual, "_campania_mas_reciente_con_datos", lambda: 32)
    assert campania_actual.campania_actual() == 32
