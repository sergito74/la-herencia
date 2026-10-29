import os
os.environ.setdefault("LA_HERENCIA_SIN_PLANIFICADOR","1")
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.features.trabajos_eventuales import repository as repo
from src.db import connection


@pytest.fixture
def cliente(monkeypatch):
    def prohibido(*a,**k):raise AssertionError("No escribir ni consultar WC en pruebas")
    monkeypatch.setattr(connection.pyodbc,"connect",prohibido)
    client=TestClient(app)
    client.cookies.set(COOKIE_NAME,crear_token(1,"Administrador"))
    return client


def test_lista_y_vacio(cliente,monkeypatch):
    monkeypatch.setattr(repo,"listar",lambda *a:{"items":[],"total":0,"resumen":{"cantidad":0,"totalTrabajos":0,"totalVinculado":0,"sinVincular":0},"page":1,"pageSize":50})
    assert cliente.get("/api/trabajos-eventuales").json()["items"]==[]
    assert cliente.get("/api/trabajos-eventuales?pageSize=101").status_code==422
    assert cliente.get("/api/trabajos-eventuales?desde=2026-10-29&hasta=2026-01-01").status_code==400


def test_conflicto_vinculo(cliente,monkeypatch):
    def falla(*a):raise ValueError("La liquidación corresponde a otro trabajador")
    monkeypatch.setattr(repo,"vincular",falla)
    r=cliente.post("/api/trabajos-eventuales/1/vinculos",json={"idSalario":2,"importe":10})
    assert r.status_code==409 and "otro trabajador" in r.json()["detail"]
    assert cliente.post("/api/trabajos-eventuales/1/vinculos",json={"idSalario":2,"importe":-1}).status_code==422


def test_solo_lectura_no_escribe(cliente):
    cliente.cookies.set(COOKIE_NAME,crear_token(1,"Lectura"))
    assert cliente.post("/api/trabajos-eventuales/1/vinculos",json={"idSalario":2,"importe":10}).status_code==403
    assert cliente.delete("/api/trabajos-eventuales/1/vinculos/2").status_code==403


def test_detalle_inexistente_y_desvinculo(cliente,monkeypatch):
    monkeypatch.setattr(repo,"obtener",lambda *a:None)
    monkeypatch.setattr(repo,"desvincular",lambda *a:None)
    assert cliente.get("/api/trabajos-eventuales/1").status_code==404
    assert cliente.delete("/api/trabajos-eventuales/1/vinculos/2").status_code==404



def test_adicional_no_permite_otro_trabajador_y_lectura(cliente,monkeypatch):
    from src.features.remuneraciones import adicional
    def otro(*a):raise ValueError("Este cálculo corresponde al adicional de Marcelo Sierra")
    monkeypatch.setattr(adicional,"obtener",otro)
    assert cliente.get("/api/remuneraciones/1/adicional").status_code==400
    cliente.cookies.set(COOKIE_NAME,crear_token(1,"Lectura"))
    assert cliente.post("/api/remuneraciones/1/adicional",json={}).status_code==403
