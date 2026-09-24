"""Tests del calendario agrícola (017, pedido del usuario 2026-09-24)."""

from __future__ import annotations

from datetime import date

from src.features.imputacion.calendario_agricola import es_fecha_plausible


def test_soja_primera_labor_previa_es_plausible():
    # Caso real confirmado por el usuario: orden ejecutada 19/09, sembrada en noviembre.
    assert es_fecha_plausible("Soja primera", "2026/2027", date(2026, 9, 19)) is True


def test_soja_primera_muy_anticipada_no_es_plausible():
    # Más de 2 meses antes de la siembra de noviembre: no es una labor previa razonable.
    assert es_fecha_plausible("Soja primera", "2026/2027", date(2026, 1, 15)) is False


def test_trigo_en_plena_campania_es_plausible():
    assert es_fecha_plausible("Trigo", "2026/2027", date(2026, 8, 1)) is True


def test_trigo_fuera_de_campania_no_es_plausible():
    # Trigo termina dic/ene; en abril ya no corresponde a esta campaña.
    assert es_fecha_plausible("Trigo", "2026/2027", date(2027, 4, 1)) is False


def test_pastura_multianio_es_plausible_varios_anios_despues():
    assert es_fecha_plausible("Pastura", "2026", date(2029, 6, 1)) is True


def test_cultivo_o_campania_desconocidos_no_bloquean():
    assert es_fecha_plausible("Cultivo Inexistente", "2026/2027", date(2026, 9, 19)) is None
    assert es_fecha_plausible("Trigo", "No Aplica", date(2026, 9, 19)) is None
    assert es_fecha_plausible("Trigo", "2026/2027", None) is None


def test_pastura_preparacion_de_suelo_seis_meses_antes_es_plausible():
    # Caso real (WC, 2026-09-24): orden de laboreo el 2025-09-15 para pastura
    # implantada recién en feb/marzo 2026 (~5-6 meses de preparación previa).
    assert es_fecha_plausible("Pastura", "2026", date(2025, 9, 15)) is True


def test_avena_mantenimiento_despues_de_cosecha_es_plausible():
    # Caso real (WC, orden 12, 2017-03-15): fertilización/mantenimiento de
    # Avena 2016 varios meses después del fin teórico (noviembre) — no hay
    # corte estricto para estas labores en cultivos forrajeros de la hacienda.
    assert es_fecha_plausible("Avena", "2016", date(2017, 3, 15)) is True
