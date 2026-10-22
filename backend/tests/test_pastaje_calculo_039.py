"""039: cálculo de liquidación de pastaje (puro, sin base)."""

from datetime import date
from decimal import Decimal as D

import pytest

from src.features.pastaje.calculo import (
    Movimiento as M, SinIndice, Tarifa as T, campania, liquidar, texto_factura, validar_bitacora,
)

VAQ, TERN = 3, 2
TAR = [T(VAQ, "kg_novillo", D("5"), date(2026, 9, 1))]
SEP = {date(2026, 9, 25): D("4068.212"), date(2026, 9, 29): D("4241.828")}


def test_septiembre_2026_reproduce_la_factura_real():
    liq = liquidar(date(2026, 9, 1), [M(date(2026, 9, 25), "ingreso", VAQ, 70)], TAR, SEP)
    assert liq.kg == D(70) and liq.precio == D("4155.02")
    assert (liq.neto, liq.iva, liq.total) == (D("290851.40"), D("61078.79"), D("351930.19"))
    assert [(t.desde.day, t.hasta.day, t.cabezas, t.dias) for t in liq.tramos] == [(25, 30, 70, 6)]
    assert texto_factura(liq, {VAQ: "Vaquillonas"}) == ["Servicio de pastaje de 70 Vaquillonas del 25 al 30 de septiembre de 2026"]


def test_mes_de_31_dias_completo_son_5_kg_por_cabeza():
    idx = {date(2026, 10, d): D("4000") for d in (2, 6, 9)}
    liq = liquidar(date(2026, 10, 1), [M(date(2026, 9, 25), "ingreso", VAQ, 70)], TAR, idx)
    assert liq.kg == D(350) and liq.neto == D("1400000.00")


def test_egreso_a_mitad_de_mes_no_cobra_el_dia_del_egreso():
    movs = [M(date(2026, 9, 25), "ingreso", VAQ, 70), M(date(2026, 10, 15), "egreso", VAQ, 10)]
    liq = liquidar(date(2026, 10, 1), movs, TAR, {date(2026, 10, 2): D("4000")})
    assert [(t.cabezas, t.dias) for t in liq.tramos] == [(70, 14), (60, 17)]
    assert abs(liq.kg - D(70 * 14 + 60 * 17) * 5 / 31) < D("1e-20")


def test_muerte_ese_dia_no_se_cobra():
    movs = [M(date(2026, 10, 1), "ingreso", VAQ, 10), M(date(2026, 10, 31), "muerte", VAQ, 1)]
    liq = liquidar(date(2026, 10, 1), movs, TAR, {date(2026, 10, 2): D("1")})
    assert [(t.cabezas, t.dias) for t in liq.tramos] == [(10, 30), (9, 1)]


def test_crias_pagan_desde_el_destete():
    tar = TAR + [T(TERN, "kg_novillo", D("2"), date(2026, 1, 1))]
    movs = [M(date(2026, 10, 1), "ingreso", VAQ, 10), M(date(2026, 10, 5), "nacimiento", TERN, 4),
            M(date(2026, 10, 30), "destete", TERN, 4)]
    liq = liquidar(date(2026, 10, 1), movs, tar, {date(2026, 10, 2): D("1")})
    assert [(t.categoria, t.cabezas, t.dias) for t in liq.tramos] == [(VAQ, 10, 31), (TERN, 4, 2)]


def test_recuento_no_cambia_cabezas():
    movs = [M(date(2026, 10, 1), "ingreso", VAQ, 10), M(date(2026, 10, 10), "recuento", VAQ, 12)]
    liq = liquidar(date(2026, 10, 1), movs, TAR, {date(2026, 10, 2): D("1")})
    assert [(t.cabezas, t.dias) for t in liq.tramos] == [(10, 31)]


def test_sin_indice_en_los_dias_con_hacienda_bloquea():
    with pytest.raises(SinIndice):
        liquidar(date(2026, 9, 1), [M(date(2026, 9, 25), "ingreso", VAQ, 70)], TAR, {date(2026, 9, 2): D("1")})


def test_precio_fijo_en_pesos_sin_indice():
    tar = [T(VAQ, "fijo_ars", D("30000"), date(2026, 1, 1))]
    liq = liquidar(date(2026, 9, 1), [M(date(2026, 9, 25), "ingreso", VAQ, 70)], tar, {})
    assert liq.neto == D("420000.00") and liq.precio is None and liq.moneda == "ARS"


def test_tarifa_cambia_dentro_del_mes():
    tar = TAR + [T(VAQ, "kg_novillo", D("6"), date(2026, 10, 16))]
    liq = liquidar(date(2026, 10, 1), [M(date(2026, 9, 1), "ingreso", VAQ, 10)], tar, {date(2026, 10, 2): D("1")})
    assert [(t.valor_mes, t.dias) for t in liq.tramos] == [(D(5), 15), (D(6), 16)]


def test_bitacora_negativa_se_rechaza():
    with pytest.raises(ValueError):
        validar_bitacora([M(date(2026, 10, 1), "ingreso", VAQ, 5), M(date(2026, 10, 2), "egreso", VAQ, 6)])
    with pytest.raises(ValueError):
        validar_bitacora([M(date(2026, 10, 1), "nacimiento", TERN, 2), M(date(2026, 10, 2), "destete", TERN, 3)])


def test_campania_julio_junio():
    assert campania(date(2026, 9, 1)) == "2026/2027" and campania(date(2027, 6, 1)) == "2026/2027"


def test_muerte_de_cria_al_pie_no_resta_cabezas_cobrables():
    tar = TAR + [T(TERN, "kg_novillo", D("2"), date(2026, 1, 1))]
    movs = [M(date(2026, 10, 1), "ingreso", VAQ, 10), M(date(2026, 10, 1), "ingreso", TERN, 5),
            M(date(2026, 10, 5), "nacimiento", TERN, 3), M(date(2026, 10, 10), "muerte", TERN, 1)]
    liq = liquidar(date(2026, 10, 1), movs, tar, {date(2026, 10, 2): D("1")})
    assert [(t.categoria, t.cabezas, t.dias) for t in liq.tramos if t.categoria == TERN] == [(TERN, 5, 31)]


def test_texto_factura_una_linea_por_cantidad_de_cabezas():
    movs = [M(date(2026, 10, 1), "ingreso", VAQ, 30), M(date(2026, 10, 25), "ingreso", VAQ, 40)]
    liq = liquidar(date(2026, 10, 1), movs, TAR, {date(2026, 10, 2): D("1")})
    assert texto_factura(liq, {VAQ: "Vaquillonas"}) == [
        "Servicio de pastaje de 30 Vaquillonas del 1 al 24 de octubre de 2026",
        "Servicio de pastaje de 70 Vaquillonas del 25 al 31 de octubre de 2026"]
