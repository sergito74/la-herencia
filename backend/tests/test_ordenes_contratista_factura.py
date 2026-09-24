"""Tests del vínculo N a N factura de contratista↔Orden (017-imputacion-automatica-costos)."""

from __future__ import annotations

from src.features.ordenes import repository


def _orden(facturas=None):
    return {
        "idOrdenTrabajo": 1,
        "insumos": [],
        "facturasContratista": facturas or [],
    }


def test_vincular_misma_factura_a_dos_ordenes(monkeypatch):
    inserts = []
    monkeypatch.setattr(repository, "obtener_orden", lambda ido: _orden(facturas=[{"idCompra": 77}]))
    monkeypatch.setattr(repository.costeo, "costo_contratista", lambda idc, dist: {"montoPesos": 1000.0})
    monkeypatch.setattr(repository, "execute_write_transaction", lambda stmts: inserts.extend(stmts) or [1])

    # No debe lanzar aunque la orden ya tenga una factura vinculada.
    repository.vincular_factura_contratista(1, 77)
    repository.vincular_factura_contratista(2, 77)

    assert len(inserts) == 2
    assert all("INSERT INTO dbo.OrdenesContratistaFacturas" in s for s, _ in inserts)


def test_desvincular_factura_puntual(monkeypatch):
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params: {"id": 5})
    borrados = []
    monkeypatch.setattr(repository, "execute_write_transaction", lambda stmts: borrados.extend(stmts) or [1])

    repository.desvincular_factura_contratista(1, 77)

    assert len(borrados) == 1
    assert "DELETE FROM dbo.OrdenesContratistaFacturas WHERE IdVinculo = ?" == borrados[0][0]
    assert borrados[0][1] == (5,)
