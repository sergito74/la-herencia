from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.features.imputacion import presentacion, repository, router


def test_contexto_comercial_batch_parametrizado_y_origen(monkeypatch):
    consultas = []

    def leer(sql, params):
        consultas.append((sql, params))
        return [{"idPropuesta": 1, "producto": "Semilla", "numeroDocumento": "A-123"}]

    monkeypatch.setattr(presentacion, "fetch_all", leer)
    assert presentacion.enriquecer_fracciones([]) == []
    filas = presentacion.enriquecer_fracciones([{"idPropuesta": 1, "cantidad": 2}, {"idPropuesta": 2}])
    assert len(consultas) == 1
    sql, params = consultas[0]
    assert params == (1, 2)
    assert "p.Origen = 'Insumo'" in sql
    assert "THEN p.IdDetalleCompra ELSE dc.IdCompra" in sql
    assert filas[0]["producto"] == "Semilla" and filas[0]["cantidad"] == 2
    assert filas[1] == {"idPropuesta": 2}


def test_api_propuesta_expone_cantidad_contexto_y_destino(monkeypatch):
    fila = dict(idPropuesta=1, idCorrida="corrida", origen="Insumo", idDetalleCompra=100,
                idOrdenTrabajo=5, idLote=2, idCultivo=3, idCampania=4, idCentroCosto=None,
                esGanaderia=None, importe=50, cantidad=2.5, unidad="LTS", estado="Pendiente",
                fechaCalculo=datetime(2026, 9, 24), fechaAprobacion=None)
    monkeypatch.setattr(repository, "listar_propuestas", lambda *a: [fila])
    monkeypatch.setattr(presentacion, "fetch_all", lambda *a: [dict(idPropuesta=1, producto="Herbicida",
                        numeroDocumento="A-123", proveedor="Proveedor", cultivo="Trigo", campania="2025/26")])
    app = FastAPI()
    app.include_router(router.router)
    respuesta = TestClient(app).get("/api/imputacion/propuestas")
    assert respuesta.status_code == 200
    dato = respuesta.json()[0]
    assert (dato["cantidad"], dato["unidad"], dato["producto"]) == (2.5, "LTS", "Herbicida")
    assert dato["numeroDocumento"] == "A-123" and dato["cultivo"] == "Trigo"


def test_api_vacia_no_consulta_contexto(monkeypatch):
    monkeypatch.setattr(repository, "listar_propuestas", lambda *a: [])
    monkeypatch.setattr(presentacion, "fetch_all", lambda *a: (_ for _ in ()).throw(AssertionError()))
    app = FastAPI()
    app.include_router(router.router)
    assert TestClient(app).get("/api/imputacion/propuestas").json() == []
