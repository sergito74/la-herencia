"""13/11/2026: el reparto por órdenes respeta la imputación manual por cultivo/campaña de cada renglón."""
from src.features.imputacion import motor, repository


def test_reparto_respeta_cultivo_de_los_renglones(monkeypatch):
    monkeypatch.setattr(repository, "ordenes_vinculadas_a_compra", lambda i: [67])
    monkeypatch.setattr(repository, "total_neto_compra", lambda i: {"neto": 100.0, "tipoDeCambio": 1, "moneda": "Pesos"})
    monkeypatch.setattr(repository, "orden_trabajo_info", lambda i: {"idRubro": None})
    # la orden tiene 90 ha de trigo y 10 de soja; la factura imputa mitad y mitad
    monkeypatch.setattr(repository, "distribucion_de_orden", lambda i: [
        {"idLote": 1, "idCultivo": 8, "idCampania": 5, "superficie": 90},
        {"idLote": 2, "idCultivo": 3, "idCampania": 5, "superficie": 10}])
    monkeypatch.setattr(repository, "renglones_repartibles", lambda i: [
        {"neto": 50.0, "idCultivo": 8, "idCampania": 5}, {"neto": 50.0, "idCultivo": 3, "idCampania": 5}])
    fr, motivo = motor.evaluar_contratista(1)
    assert motivo is None
    assert {f["idLote"]: f["importe"] for f in fr} == {1: 50.0, 2: 50.0}


def test_renglon_sin_cultivo_en_ordenes_va_por_superficie(monkeypatch):
    monkeypatch.setattr(repository, "ordenes_vinculadas_a_compra", lambda i: [67])
    monkeypatch.setattr(repository, "total_neto_compra", lambda i: {"neto": 100.0, "tipoDeCambio": 1, "moneda": "Pesos"})
    monkeypatch.setattr(repository, "orden_trabajo_info", lambda i: {"idRubro": None})
    monkeypatch.setattr(repository, "distribucion_de_orden", lambda i: [
        {"idLote": 1, "idCultivo": 8, "idCampania": 5, "superficie": 75},
        {"idLote": 2, "idCultivo": 3, "idCampania": 5, "superficie": 25}])
    monkeypatch.setattr(repository, "renglones_repartibles", lambda i: [{"neto": 100.0, "idCultivo": None, "idCampania": 5}])
    fr, _ = motor.evaluar_contratista(1)
    assert {f["idLote"]: f["importe"] for f in fr} == {1: 75.0, 2: 25.0}


def test_cultivo_sin_orden_queda_en_su_cultivo_sin_lote(monkeypatch):
    monkeypatch.setattr(repository, "ordenes_vinculadas_a_compra", lambda i: [67])
    monkeypatch.setattr(repository, "total_neto_compra", lambda i: {"neto": 100.0, "tipoDeCambio": 1, "moneda": "Pesos"})
    monkeypatch.setattr(repository, "orden_trabajo_info", lambda i: {"idRubro": None})
    monkeypatch.setattr(repository, "distribucion_de_orden", lambda i: [{"idLote": 1, "idCultivo": 8, "idCampania": 5, "superficie": 75}])
    monkeypatch.setattr(repository, "renglones_repartibles", lambda i: [
        {"neto": 60.0, "idCultivo": 8, "idCampania": 5}, {"neto": 40.0, "idCultivo": 9, "idCampania": 6}])
    fr, _ = motor.evaluar_contratista(1)
    assert {(f["idLote"], f["idCultivo"]): f["importe"] for f in fr} == {(1, 8): 60.0, (None, 9): 40.0}


def test_misma_cultivo_otra_campania_manda_la_manual(monkeypatch):
    monkeypatch.setattr(repository, "ordenes_vinculadas_a_compra", lambda i: [67])
    monkeypatch.setattr(repository, "total_neto_compra", lambda i: {"neto": 100.0, "tipoDeCambio": 1, "moneda": "Pesos"})
    monkeypatch.setattr(repository, "orden_trabajo_info", lambda i: {"idRubro": None})
    monkeypatch.setattr(repository, "distribucion_de_orden", lambda i: [{"idLote": 1, "idCultivo": 3, "idCampania": 6, "superficie": 50}])
    monkeypatch.setattr(repository, "renglones_repartibles", lambda i: [{"neto": 100.0, "idCultivo": 3, "idCampania": 5}])
    fr, _ = motor.evaluar_contratista(1)
    assert [(f["idLote"], f["idCampania"], f["importe"]) for f in fr] == [(1, 5, 100.0)]
