"""048: contrato de GET/PUT /api/compras/{id}/ordenes-trabajo y reimputación de NC al relacionar (con mocks)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.compras import repository as compras_repo
from src.features.ordenes import documentos_contratista as dc
from src.main import app


def _cliente(rol="Administrador"):
    c = TestClient(app)
    c.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol=rol))
    return c


@pytest.fixture(autouse=True)
def mocks(monkeypatch):
    llamadas = {"fijar": [], "notas": []}
    monkeypatch.setattr(dc, "es_nota_credito_debito", lambda idc: idc == 900)
    monkeypatch.setattr(dc, "es_documento_de_labor", lambda idc: idc == 1)
    monkeypatch.setattr(dc, "es_contratista", lambda idc: True)
    monkeypatch.setattr(dc, "ordenes_del_contratista", lambda idc: [
        {"idOrden": 162, "fecha": "2026-10-25", "labor": "Pulverizacion terrestre", "lotes": "3A",
         "hectareas": 198.0, "vinculada": False, "tieneOtraFactura": False}])
    monkeypatch.setattr(dc, "reparto", lambda idc, ido=None: [])

    def fijar(idc, ids, usuario):
        if ids == [99]:
            raise ValueError(["Alguna orden no es de este contratista o no está ejecutada."])
        llamadas["fijar"].append((idc, ids, usuario))
        return [{"idOrden": 162, "lote": "3A", "cultivo": "Soja", "campania": "26/27", "importe": 2376000.0}]
    monkeypatch.setattr(dc, "fijar_vinculos", fijar)
    monkeypatch.setattr(dc, "recalcular_nota", lambda idnc, u: llamadas["notas"].append(idnc))
    monkeypatch.setattr(compras_repo, "agregar_documento_relacionado", lambda a, b: None)
    monkeypatch.setattr(compras_repo, "quitar_documento_relacionado", lambda a, b: None)
    import src.features.imputacion.repository as ir
    monkeypatch.setattr(ir, "nombre_usuario", lambda i: "sergio")
    return llamadas


def test_get_forma_de_la_respuesta():
    r = _cliente().get("/api/compras/1/ordenes-trabajo")
    assert r.status_code == 200
    body = r.json()
    assert body["esDocumentoDeLabor"] is True and body["esNotaCreditoDebito"] is False
    assert set(body["ordenes"][0]) == {"idOrden", "fecha", "labor", "lotes", "hectareas", "vinculada", "tieneOtraFactura"}


def test_get_nota_no_ofrece_ordenes():
    body = _cliente().get("/api/compras/900/ordenes-trabajo").json()
    assert body["esNotaCreditoDebito"] is True and body["ordenes"] == []


def test_put_fija_vinculos_con_el_usuario(mocks):
    r = _cliente().put("/api/compras/1/ordenes-trabajo", json={"idsOrden": [162]})
    assert r.status_code == 200 and r.json()["reparto"][0]["importe"] == 2376000.0
    assert mocks["fijar"] == [(1, [162], "sergio")]


def test_put_orden_invalida_422():
    r = _cliente().put("/api/compras/1/ordenes-trabajo", json={"idsOrden": [99]})
    assert r.status_code == 422 and "contratista" in r.json()["detail"]


def test_put_solo_lectura_403(mocks):
    r = _cliente("Lectura").put("/api/compras/1/ordenes-trabajo", json={"idsOrden": [162]})
    assert r.status_code == 403 and mocks["fijar"] == []


def test_relacionar_nc_la_reimputa(mocks):
    r = _cliente().post("/api/compras/1/relacionados", json={"idCompraRelacionada": 900})
    assert r.status_code == 204 and mocks["notas"] == [900]
    _cliente().delete("/api/compras/1/relacionados/900")
    assert mocks["notas"] == [900, 900]
