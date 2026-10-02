"""Tests de controles (032, T010). Sin base: `pagado_antes` se reemplaza."""

from __future__ import annotations

from datetime import date

from src.features.recalculo_fifo import controles, motor
from tests.recalculo_fifo.test_motor import HOY, doc, pago, sin_tc


def _evaluar(items, antes, monkeypatch, fijos=()):
    monkeypatch.setattr(controles, "pagado_antes", lambda totales: antes)
    res = motor.recalcular(items, list(fijos), sin_tc, HOY)
    return controles.evaluar({"items": items, "excepcionesDatos": []}, res, sin_tc)


def test_cuenta_que_cerraba_sigue_cerrando(monkeypatch):
    items = [doc(1, date(2024, 1, 1), 100), pago(9, date(2024, 1, 5), 100)]
    ev = _evaluar(items, {("Compras", 1): 100.0}, monkeypatch)
    assert ev["cerrabaAntes"] and ev["cierraDespues"] and ev["tendencia"] == "igual"


def test_sobreaplicada_antes_mejora(monkeypatch):
    items = [doc(1, date(2024, 1, 1), 100), pago(9, date(2024, 1, 5), 100)]
    ev = _evaluar(items, {("Compras", 1): 180.0}, monkeypatch)
    assert not ev["cerrabaAntes"] and ev["cierraDespues"] and ev["tendencia"] == "mejora"
    assert ev["documentosSobreaplicadosAntes"] == 1


def test_pago_de_mas_es_excepcion(monkeypatch):
    items = [doc(1, date(2024, 1, 1), 100), pago(9, date(2024, 1, 5), 150)]
    ev = _evaluar(items, {("Compras", 1): 100.0}, monkeypatch)
    assert not ev["cierraDespues"] and ev["controles"][0]["codigo"] == "pago-de-mas"
    assert not ev["cerrabaAntes"] and ev["tendencia"] == "igual"


def test_compensacion_no_registrada_antes_no_cerraba(monkeypatch):
    items = [doc(1, date(2024, 1, 1), 100), doc(5, date(2024, 2, 1), 60, lado="C", origen="Venta Granos"),
             pago(9, date(2024, 3, 1), 40)]
    ev = _evaluar(items, {("Compras", 1): 40.0}, monkeypatch)
    assert not ev["cerrabaAntes"] and ev["cierraDespues"] and ev["tendencia"] == "mejora"


def test_compensacion_ya_registrada_cerraba(monkeypatch):
    items = [doc(1, date(2024, 1, 1), 100), doc(5, date(2024, 2, 1), 60, lado="C", origen="Venta Granos"),
             pago(9, date(2024, 3, 1), 40)]
    ev = _evaluar(items, {("Compras", 1): 100.0}, monkeypatch)
    assert ev["cerrabaAntes"] and ev["cierraDespues"] and ev["tendencia"] == "igual"


def test_usd_pagado_en_pesos_no_queda_sobreaplicado(monkeypatch):
    items = [doc(1, date(2024, 1, 1), 100, moneda="USD", tc=1000), pago(9, date(2024, 3, 1), 110000)]
    monkeypatch.setattr(controles, "pagado_antes", lambda totales: {("Compras", 1): 100000.0})
    res = motor.recalcular(items, [], lambda _f: 1100.0, HOY)
    ev = controles.evaluar({"items": items, "excepcionesDatos": []}, res, lambda _f: 1100.0)
    assert ev["aplicadoDespues"] == 100000 and ev["documentosSobreaplicadosAntes"] == 0
