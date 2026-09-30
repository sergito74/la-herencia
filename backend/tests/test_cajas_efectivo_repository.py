"""Tests de `cajas_efectivo.repository` (027) — monkeypatch sobre
`fetch_all`/`fetch_one`, sin tocar `WC` real (mismo criterio que
021/023)."""

from __future__ import annotations

from src.features.cajas_efectivo import repository


def test_calcular_saldo_suma_con_signo(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"saldo": 152340.18})
    assert repository.calcular_saldo("GiamigliSA") == 152340.18


def test_calcular_saldo_sin_movimientos_es_cero(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"saldo": None})
    assert repository.calcular_saldo("GiamigliSA") == 0.0


def test_listar_movimientos_orden_por_fecha_e_id(monkeypatch):
    capturado = {}

    def fake_fetch_all(sql, params=()):
        capturado["sql"] = sql
        capturado["params"] = params
        return [
            {
                "idMovimiento": 1, "fecha": "2011-02-17", "concepto": "AFIP", "detalle": None,
                "importe": -1214.19, "cuenta": "White", "formaPago": None, "numeroDocumento": None,
                "idContactoRelacionado": None,
            }
        ]

    monkeypatch.setattr(repository, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"total": 1})
    items, total = repository.listar_movimientos("GiamigliSA", 1, 50)
    assert "ORDER BY Fecha ASC, IdMovimiento ASC" in capturado["sql"]
    assert total == 1
    assert items[0]["importe"] == -1214.19


def test_listar_movimientos_pagina_con_offset(monkeypatch):
    capturado = {}

    def fake_fetch_all(sql, params=()):
        capturado["params"] = params
        return []

    monkeypatch.setattr(repository, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"total": 0})
    repository.listar_movimientos("CampoChica", 2, 20)
    # offset = (page-1)*pageSize = 20, pageSize = 20
    assert capturado["params"][-2:] == (20, 20)
