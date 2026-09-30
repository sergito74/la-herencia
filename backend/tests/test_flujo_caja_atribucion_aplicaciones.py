"""019 User Story 4: el flujo de caja por rubro usa las aplicaciones reales
como fuente primaria, y distingue histórico/pendiente/aplicado (nunca una
única etiqueta genérica) — ver research.md §7 y FR-010."""

from __future__ import annotations

from datetime import date

from src.features.aplicaciones_pago import repository as aplicaciones_repository
from src.features.flujo_caja import atribucion, repository


def test_movimiento_con_aplicacion_usa_rubro_del_documento(monkeypatch):
    monkeypatch.setattr(
        aplicaciones_repository,
        "aplicaciones_vigentes_por_movimiento",
        lambda: {("galicia", 1): [{"tipoDocumento": "VentaGranos", "idDocumentoAplicado": 1, "importeAplicado": 500.0}]},
    )
    monkeypatch.setattr(atribucion, "_rubro_de_venta", lambda tipo, id_doc: "Venta Maiz")

    movimientos = [
        {
            "fecha": date(2026, 6, 15),
            "banco": "Galicia",
            "origenMovimiento": "galicia",
            "idMovimientoOrigen": 1,
            "importe": 500.0,
            "idContacto": 1,
            "esInterno": False,
        }
    ]
    resultado = repository.atribuir_movimientos(movimientos)
    assert resultado[0]["rubro"] == "Venta Maiz"
    assert [(p["rubro"], p["importeArs"]) for p in resultado[0]["partes"]] == [("Venta Maiz", 500.0)]


def test_movimiento_ley_25413_tiene_rubro_fijo_sin_pasar_por_aplicaciones(monkeypatch):
    """Pedido explícito de Sergio (2026-09-29): el impuesto al débito/crédito
    bancario no es imputable a ningún contacto — nunca debe intentar
    matchear contra una aplicación o compra inexistente."""

    def fail_if_called(*a, **k):
        raise AssertionError("no debe consultar aplicaciones para un movimiento Ley 25413")

    monkeypatch.setattr(aplicaciones_repository, "aplicaciones_vigentes_de_movimiento", fail_if_called)

    movimientos = [
        {
            "fecha": date(2026, 6, 15),
            "banco": "BNA",
            "origenMovimiento": "bna",
            "idMovimientoOrigen": 1,
            "importe": -123.45,
            "concepto": "IMPUESTO LEY 25413 ALIC GRAL S/DEBITOS",
            "idContacto": 0,
            "esInterno": False,
        }
    ]
    resultado = repository.atribuir_movimientos(movimientos)
    assert resultado[0]["rubro"] == atribucion.RUBRO_LEY_25413
    assert resultado[0]["centroCosto"] == atribucion.CENTRO_COSTO_LEY_25413


def test_movimiento_arba_recaudacion_tiene_rubro_fijo_sin_pasar_por_aplicaciones(monkeypatch):
    """Mismo criterio que Ley 25413 (2026-09-29, revisión de casos "sin
    candidata" de la conciliación masiva): ARBA retiene/percibe sobre el
    movimiento bancario en sí, no es una compra a un proveedor."""

    def fail_if_called(*a, **k):
        raise AssertionError("no debe consultar aplicaciones para un movimiento de recaudación ARBA")

    monkeypatch.setattr(aplicaciones_repository, "aplicaciones_vigentes_de_movimiento", fail_if_called)

    movimientos = [
        {
            "fecha": date(2012, 4, 20),
            "banco": "BNA",
            "origenMovimiento": "bna",
            "idMovimientoOrigen": 10450,
            "importe": -105.47,
            "concepto": "RECAUDACION ARBA",
            "idContacto": 0,
            "esInterno": False,
        }
    ]
    resultado = repository.atribuir_movimientos(movimientos)
    assert resultado[0]["rubro"] == atribucion.RUBRO_ARBA_RECAUDACION
    assert resultado[0]["centroCosto"] == atribucion.CENTRO_COSTO_LEY_25413


def test_movimiento_sin_aplicacion_anterior_al_corte_es_historico(monkeypatch):
    monkeypatch.setattr(aplicaciones_repository, "aplicaciones_vigentes_de_movimiento", lambda origen, id_mov: [])
    monkeypatch.setattr(atribucion, "atribuir_egreso", lambda *a, **k: {"rubro": atribucion.SIN_RUBRO, "centroCosto": None})

    movimientos = [
        {
            "fecha": date(2012, 1, 1),
            "banco": "BNA",
            "origenMovimiento": "bna",
            "idMovimientoOrigen": 1,
            "importe": -500.0,
            "idContacto": 1,
            "esInterno": False,
        }
    ]
    resultado = repository.atribuir_movimientos(movimientos)
    assert resultado[0]["rubro"] == atribucion.HISTORICO_SIN_APLICAR


def test_movimiento_sin_aplicacion_posterior_al_corte_es_pendiente(monkeypatch):
    monkeypatch.setattr(aplicaciones_repository, "aplicaciones_vigentes_de_movimiento", lambda origen, id_mov: [])
    monkeypatch.setattr(atribucion, "atribuir_egreso", lambda *a, **k: {"rubro": atribucion.SIN_RUBRO, "centroCosto": None})

    movimientos = [
        {
            "fecha": date(2026, 6, 1),
            "banco": "BNA",
            "origenMovimiento": "bna",
            "idMovimientoOrigen": 1,
            "importe": -500.0,
            "idContacto": 1,
            "esInterno": False,
        }
    ]
    resultado = repository.atribuir_movimientos(movimientos)
    assert resultado[0]["rubro"] == atribucion.PENDIENTE_DE_APLICAR
