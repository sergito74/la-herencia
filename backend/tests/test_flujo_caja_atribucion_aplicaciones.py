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
        "aplicaciones_vigentes_de_movimiento",
        lambda origen, id_mov: [{"tipoDocumento": "VentaGranos", "idDocumentoAplicado": 1, "importeAplicado": 500.0}],
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
