"""Tests del motor de auto-clasificación (017), sin tocar la base real (monkeypatch)."""

from __future__ import annotations

from src.features.imputacion import motor, repository

ID_PRODUCTO = 500
ID_DETALLE_COMPRA = 900
ID_CENTRO_GANADERIA = 2
ID_CENTRO_ADM_GENERAL = 3


def _preparar(monkeypatch, *, id_producto=ID_PRODUCTO, vinculos=None, stock=None, ordenes=None, distribuciones=None, referencias=None):
    vinculos = vinculos if vinculos is not None else [{"idDetalleRemito": 1, "cantidadRemitida": 10.0}]
    ordenes = ordenes or {}
    distribuciones = distribuciones or {}
    referencias = referencias or {}

    monkeypatch.setattr(repository, "det_compra_producto", lambda idc: id_producto)
    monkeypatch.setattr(repository, "vinculos_remito_para_compra", lambda idc: vinculos)
    monkeypatch.setattr(repository, "orden_trabajo_info", lambda ido: ordenes.get(ido))
    monkeypatch.setattr(repository, "distribucion_de_orden_insumo", lambda idi: distribuciones.get(idi, []))
    monkeypatch.setattr(repository, "obtener_referencia", lambda idp, es_ganaderia: referencias.get((idp, es_ganaderia)))
    monkeypatch.setattr(motor, "calcular_stock", lambda idp: {idp: stock} if stock else {})
    monkeypatch.setattr(
        motor,
        "get_id_centro_costo_por_nombre",
        lambda nombre: ID_CENTRO_GANADERIA if nombre == "Ganaderia" else ID_CENTRO_ADM_GENERAL,
    )


def test_consumo_integro_una_sola_orden(monkeypatch):
    stock = {
        "capas": [{"id": "R1", "cantidad": 10.0, "restante": 0.0, "costoUnitario": 100.0}],
        "consumos": {"OT1": {"items": [{"capa": "R1", "cantidad": 10.0}]}},
        "salidaMeta": {"OT1": {"tipo": "ordenTrabajo", "idOrdenTrabajo": 55}},
    }
    _preparar(
        monkeypatch,
        stock=stock,
        ordenes={55: {"idOrdenTrabajo": 55, "idRubro": None, "idCentroCostos": None}},
        distribuciones={1: [{"idLote": 10, "idCultivo": 20, "idCampania": 30, "cantidadAsignada": 10.0}]},
    )
    fracciones = motor.calcular_propuesta_insumo(ID_DETALLE_COMPRA)
    assert len(fracciones) == 1
    f = fracciones[0]
    assert f["idCultivo"] == 20 and f["idCampania"] == 30
    assert f["importe"] == 1000.0


def test_consumo_parcial_multi_campania_y_stock(monkeypatch):
    stock = {
        "capas": [{"id": "R1", "cantidad": 10.0, "restante": 2.0, "costoUnitario": 100.0}],
        "consumos": {
            "OT1": {"items": [{"capa": "R1", "cantidad": 5.0}]},
            "OT2": {"items": [{"capa": "R1", "cantidad": 3.0}]},
        },
        "salidaMeta": {
            "OT1": {"tipo": "ordenTrabajo", "idOrdenTrabajo": 55},
            "OT2": {"tipo": "ordenTrabajo", "idOrdenTrabajo": 56},
        },
    }
    _preparar(
        monkeypatch,
        stock=stock,
        ordenes={
            55: {"idOrdenTrabajo": 55, "idRubro": None, "idCentroCostos": None},
            56: {"idOrdenTrabajo": 56, "idRubro": None, "idCentroCostos": None},
        },
        distribuciones={
            1: [{"idLote": 10, "idCultivo": 20, "idCampania": 30, "cantidadAsignada": 5.0}],
            2: [{"idLote": 11, "idCultivo": 21, "idCampania": 31, "cantidadAsignada": 3.0}],
        },
    )
    fracciones = motor.calcular_propuesta_insumo(ID_DETALLE_COMPRA)
    stock_fracciones = [f for f in fracciones if f.get("esStock")]
    consumo_fracciones = [f for f in fracciones if not f.get("esStock")]
    assert len(stock_fracciones) == 1
    assert stock_fracciones[0]["importe"] == 200.0
    assert len(consumo_fracciones) == 2
    total = sum(f["importe"] for f in fracciones)
    assert total == 1000.0  # 10 unidades * 100 costo unitario


def test_reparto_agricultura_ganaderia(monkeypatch):
    stock = {
        "capas": [{"id": "R1", "cantidad": 10.0, "restante": 0.0, "costoUnitario": 100.0}],
        "consumos": {
            "OT1": {"items": [{"capa": "R1", "cantidad": 6.0}]},
            "B1": {"items": [{"capa": "R1", "cantidad": 4.0}]},
        },
        "salidaMeta": {
            "OT1": {"tipo": "ordenTrabajo", "idOrdenTrabajo": 55},
            "B1": {"tipo": "baja", "idCentro": ID_CENTRO_GANADERIA},
        },
    }
    _preparar(
        monkeypatch,
        stock=stock,
        ordenes={55: {"idOrdenTrabajo": 55, "idRubro": None, "idCentroCostos": None}},
        distribuciones={1: [{"idLote": 10, "idCultivo": 20, "idCampania": 30, "cantidadAsignada": 6.0}]},
    )
    fracciones = motor.calcular_propuesta_insumo(ID_DETALLE_COMPRA)
    agro = [f for f in fracciones if not f.get("esGanaderia") and not f.get("esStock")]
    ganaderia = [f for f in fracciones if f.get("esGanaderia")]
    assert len(agro) == 1 and agro[0]["importe"] == 600.0
    assert len(ganaderia) == 1 and ganaderia[0]["importe"] == 400.0


def test_orden_sin_cultivo_imputa_adm_general(monkeypatch):
    stock = {
        "capas": [{"id": "R1", "cantidad": 10.0, "restante": 0.0, "costoUnitario": 50.0}],
        "consumos": {"OT1": {"items": [{"capa": "R1", "cantidad": 10.0}]}},
        "salidaMeta": {"OT1": {"tipo": "ordenTrabajo", "idOrdenTrabajo": 60}},
    }
    _preparar(
        monkeypatch,
        stock=stock,
        ordenes={60: {"idOrdenTrabajo": 60, "idRubro": 7, "idCentroCostos": ID_CENTRO_ADM_GENERAL}},
    )
    fracciones = motor.calcular_propuesta_insumo(ID_DETALLE_COMPRA)
    assert len(fracciones) == 1
    f = fracciones[0]
    assert f["idCentroCosto"] == ID_CENTRO_ADM_GENERAL
    assert f.get("idLote") is None and f.get("idCultivo") is None and f.get("idCampania") is None
    assert f["importe"] == 500.0


def test_compra_fuera_de_alcance_no_genera_propuesta(monkeypatch):
    monkeypatch.setattr(repository, "det_compra_producto", lambda idc: None)
    assert motor.calcular_propuesta_insumo(ID_DETALLE_COMPRA) == []

    monkeypatch.setattr(repository, "det_compra_producto", lambda idc: ID_PRODUCTO)
    monkeypatch.setattr(repository, "vinculos_remito_para_compra", lambda idc: [])
    assert motor.calcular_propuesta_insumo(ID_DETALLE_COMPRA) == []


def test_contratista_sin_orden_requiere_intervencion(monkeypatch):
    monkeypatch.setattr(repository, "ordenes_vinculadas_a_compra", lambda idc: [])
    fracciones = motor.calcular_propuesta_contratista(ID_DETALLE_COMPRA)
    assert fracciones == []
    assert motor.evaluar_inconsistencia(100_000, 0) is True


def test_diferencia_grande_requiere_intervencion():
    # $100.000 de factura, se reparte solo $50.000 -> 50% de diferencia, > umbral
    assert motor.evaluar_inconsistencia(100_000, 50_000) is True
    # $100.000 de factura, se reparte $99.500 -> $500 de diferencia, tolerable
    assert motor.evaluar_inconsistencia(100_000, 99_500) is False
    # factura chica, $1.000 de diferencia sobre $5.000 (20%) pero por debajo del piso absoluto no aplica:
    # aca el piso absoluto de $10.000 es el que manda para que no se dispare por montos chicos
    assert motor.evaluar_inconsistencia(5_000, 4_000) is False


def test_propuesta_contratista_prorratea_entre_ordenes(monkeypatch):
    monkeypatch.setattr(repository, "ordenes_vinculadas_a_compra", lambda idc: [10, 11])
    monkeypatch.setattr(
        repository,
        "total_neto_compra",
        lambda idc: {"moneda": "Pesos", "tipoDeCambio": None, "neto": 1000.0},
    )
    monkeypatch.setattr(
        repository,
        "orden_trabajo_info",
        lambda ido: {"idOrdenTrabajo": ido, "idRubro": None, "idCentroCostos": None},
    )
    monkeypatch.setattr(
        repository,
        "distribucion_de_orden",
        lambda ido: (
            [{"idLote": 1, "idCultivo": 20, "idCampania": 30, "superficie": 30.0}]
            if ido == 10
            else [{"idLote": 2, "idCultivo": 21, "idCampania": 31, "superficie": 10.0}]
        ),
    )
    monkeypatch.setattr(
        motor,
        "get_id_centro_costo_por_nombre",
        lambda nombre: ID_CENTRO_GANADERIA if nombre == "Ganaderia" else ID_CENTRO_ADM_GENERAL,
    )

    fracciones = motor.calcular_propuesta_contratista(ID_DETALLE_COMPRA)
    assert len(fracciones) == 2
    total = sum(f["importe"] for f in fracciones)
    assert total == 1000.0
    por_cultivo = {f["idCultivo"]: f["importe"] for f in fracciones}
    assert por_cultivo[20] == 750.0  # 30 de 40 hectareas
    assert por_cultivo[21] == 250.0  # 10 de 40 hectareas


def test_propuesta_contratista_orden_sin_cultivo(monkeypatch):
    monkeypatch.setattr(repository, "ordenes_vinculadas_a_compra", lambda idc: [60])
    monkeypatch.setattr(
        repository,
        "total_neto_compra",
        lambda idc: {"moneda": "Pesos", "tipoDeCambio": None, "neto": 500.0},
    )
    monkeypatch.setattr(
        repository,
        "orden_trabajo_info",
        lambda ido: {"idOrdenTrabajo": ido, "idRubro": 7, "idCentroCostos": None},
    )
    monkeypatch.setattr(
        motor,
        "get_id_centro_costo_por_nombre",
        lambda nombre: ID_CENTRO_GANADERIA if nombre == "Ganaderia" else ID_CENTRO_ADM_GENERAL,
    )

    fracciones = motor.calcular_propuesta_contratista(ID_DETALLE_COMPRA)
    assert len(fracciones) == 1
    assert fracciones[0]["idCentroCosto"] == ID_CENTRO_ADM_GENERAL
    assert fracciones[0]["importe"] == 500.0
