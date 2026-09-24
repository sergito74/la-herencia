"""Cantidades físicas y reconstrucción estricta; sin acceso a SQL Server."""

from src.features.imputacion import motor, repository
from src.features.imputacion.cantidades import cantidades_coincidentes


def test_cantidades_en_unidad_remito_con_capa_convertida(monkeypatch):
    monkeypatch.setattr(repository, "det_compra_producto", lambda _: 7)
    monkeypatch.setattr(repository, "vinculos_remito_para_compra", lambda _: [
        {"idDetalleRemito": 10, "cantidadRemitida": 2, "unidad": "BIDON"},
    ])
    monkeypatch.setattr(motor, "calcular_stock", lambda _: {7: {
        "unidadBase": "L",
        "capas": [{"id": "R10", "cantidad": 40, "restante": 10, "costoUnitario": 5}],
        "consumos": {"OT5": {"items": [{"capa": "R10", "cantidad": 30}]}},
        "salidaMeta": {"OT5": {"tipo": "ordenTrabajo", "idOrdenTrabajo": 3}},
    }})
    monkeypatch.setattr(repository, "orden_trabajo_info", lambda _: {"idRubro": None})
    monkeypatch.setattr(repository, "distribucion_de_orden_insumo", lambda _: [
        {"idLote": 1, "idCultivo": 2, "idCampania": 3, "cantidadAsignada": 20},
        {"idLote": 2, "idCultivo": 2, "idCampania": 3, "cantidadAsignada": 10},
    ])
    fracciones = motor.calcular_propuesta_insumo(20)
    assert [(f["cantidad"], f["unidad"]) for f in fracciones] == [
        (0.5, "BIDON"), (1.0, "BIDON"), (0.5, "BIDON"),
    ]
    # Regresión: este cambio de presentación no corrige/recalcula importes
    # preexistentes al incorporar las cantidades.
    assert [f["importe"] for f in fracciones] == [2.5, 5.0, 2.5]


def _guardada(**cambios):
    return {"idPropuesta": 1, "idCorrida": "c", "idDetalleCompra": 10,
            "origen": "Insumo", "estado": "Aprobada", "idLote": 7,
            "importe": 50, **cambios}


def _calculada(**cambios):
    return {"idLote": 7, "importe": 50, "cantidad": 2, "unidad": "L", **cambios}


def test_reconstruccion_coincidente_no_modifica_aprobacion():
    guardada = _guardada()
    assert cantidades_coincidentes([guardada], [_calculada()]) == {1: {"cantidad": 2.0, "unidad": "L"}}
    assert guardada["estado"] == "Aprobada"
    assert "cantidad" not in guardada


def test_reconstruccion_rechaza_destino_o_importe_corregido_y_conteo_distinto():
    assert cantidades_coincidentes([_guardada(idLote=8)], [_calculada()]) == {}
    assert cantidades_coincidentes([_guardada(importe=51)], [_calculada()]) == {}
    assert cantidades_coincidentes([_guardada()], [_calculada(), _calculada()]) == {}


def test_reconstruccion_rechaza_duplicados_ambiguos_y_admite_identicos():
    guardadas = [_guardada(), _guardada(idPropuesta=2)]
    assert cantidades_coincidentes(guardadas, [_calculada(), _calculada(cantidad=3)]) == {}
    assert cantidades_coincidentes(guardadas, [_calculada(), _calculada(unidad="KG")]) == {}
    assert cantidades_coincidentes(guardadas, [_calculada(), _calculada()]) == {
        1: {"cantidad": 2.0, "unidad": "L"}, 2: {"cantidad": 2.0, "unidad": "L"},
    }


def test_reconstruccion_rechaza_servicios_intervencion_y_corridas_mezcladas():
    assert cantidades_coincidentes([_guardada(origen="Contratista")], [_calculada()]) == {}
    assert cantidades_coincidentes([_guardada(estado="RequiereIntervencion")], [_calculada()]) == {}
    assert cantidades_coincidentes([_guardada(), _guardada(idCorrida="otra")], [_calculada(), _calculada()]) == {}


def test_guardar_corrida_persiste_cantidad_y_unidad_sin_exigirlas_en_servicios(monkeypatch):
    capturadas = []
    monkeypatch.setattr(repository, "execute_write_transaction", lambda filas: capturadas.extend(filas))
    repository.guardar_corrida("Insumo", 10, [_calculada()])
    repository.guardar_corrida("Contratista", 20, [{"importe": 100}])
    assert "Cantidad, Unidad" in capturadas[0][0]
    assert capturadas[0][1][-2:] == (2, "L")
    assert capturadas[1][1][-2:] == (None, None)
