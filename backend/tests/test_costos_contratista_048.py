"""048: el Resultado toma el reparto de contratista y no cuenta dos veces lo repartido (forma de las consultas;
el caso real se valida de punta a punta en validacion.md)."""

from __future__ import annotations

from src.features.imputacion.repository import RUBROS_FUERA_REPARTO
from src.features.resultado_cultivo import costos


def _capturar(monkeypatch):
    llamadas = []
    monkeypatch.setattr(costos, "fetch_all", lambda sql, params=(): llamadas.append((sql, params)) or [])
    monkeypatch.setattr(costos.mapeo, "idCultivo_a_destino", lambda i: 7)
    return llamadas


def test_reparto_vigente_es_la_ultima_aprobada_con_orden():
    assert "Estado = 'Aprobada'" in costos._REPARTO_VIGENTE
    assert "Pendiente" not in costos._REPARTO_VIGENTE
    assert "conOrden = 1" in costos._REPARTO_VIGENTE and "rn = 1" in costos._REPARTO_VIGENTE


def test_heredados_excluye_exactamente_lo_repartido(monkeypatch):
    llamadas = _capturar(monkeypatch)
    costos.costos_heredados(5, 9)
    sql, params = llamadas[0]
    assert "NOT EXISTS" in sql and "NOT IN" in sql
    # los rubros fuera del reparto (insumos, hacienda...) siguen contando por la vista heredada
    assert params == (7, 9, *RUBROS_FUERA_REPARTO)


def test_contratista_sale_del_reparto_vigente(monkeypatch):
    llamadas = _capturar(monkeypatch)
    costos.costos_contratista(5, 9)
    sql, params = llamadas[0]
    assert "ImputacionPropuestas" in sql and "Ordenes_Trabajo_Contratista_Factura" not in sql
    assert params == (5, 9)
