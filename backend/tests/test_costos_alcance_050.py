"""Costos sin doble conteo para renglones en alcance (050 T028/T029)."""

from src.features.remitos import capas_factura
from src.features.resultado_cultivo import costos


def _sql_capturado(monkeypatch, activo):
    vistos = []
    monkeypatch.setattr(costos, "esquema_050_activo", lambda: activo)
    monkeypatch.setattr(costos.mapeo, "idCultivo_a_destino", lambda c: 99)
    monkeypatch.setattr(costos, "fetch_all", lambda sql, params=(): vistos.append(sql) or [])
    costos.costos_heredados(3, 32)
    return vistos[0]


def test_renglon_en_alcance_queda_excluido_de_costos_heredados(monkeypatch):
    assert "TamizRenglones" in _sql_capturado(monkeypatch, True)


def test_con_activo_0_el_sql_es_el_de_hoy(monkeypatch):
    assert "TamizRenglones" not in _sql_capturado(monkeypatch, False)
    assert costos.costos_alcance(3, 32) == []


def test_consumo_de_capa_en_alcance_no_se_cuenta_en_ordenes():
    assert capas_factura.parte_en_alcance("FC10", 200, {}) == 1.0
    assert capas_factura.parte_en_alcance("R5", 200, {5: 50}) == 0.25
    assert capas_factura.parte_en_alcance("R6", 200, {5: 50}) == 0.0
    assert capas_factura.parte_en_alcance("A1", 10, {}) == 0.0


def test_fracciones_aprobadas_se_cuentan(monkeypatch):
    monkeypatch.setattr(costos, "esquema_050_activo", lambda: True)
    monkeypatch.setattr(costos, "fetch_all", lambda sql, params=(): [{"montoPesos": 840_000, "montoDolares": None}]
                        if "ImputacionPropuestas" in sql and "Alcance050" in sql else [])
    assert costos.costos_alcance(3, 32)[0]["montoPesos"] == 840_000
