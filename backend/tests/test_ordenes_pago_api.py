import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.db import connection
from src.features.auth.router import COOKIE_NAME
from src.auth.tokens import crear_token
from src.features.ordenes_pago import router as router_module
from src.features.ordenes_pago import repository as repo


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(connection.pyodbc,'connect',lambda *a,**k:pytest.fail('No acceder a WC'))
    monkeypatch.setattr(router_module,'usuario_actual',lambda *a:'test')
    c=TestClient(app);c.cookies.set(COOKIE_NAME,crear_token(1,'Administrador'))
    return c


def test_listas_vacias_y_limites(client,monkeypatch):
    monkeypatch.setattr(repo,'listar',lambda *a:{'items':[],'total':0})
    monkeypatch.setattr(repo,'recibos',lambda *a:{'items':[],'total':0})
    assert client.get('/api/ordenes-pago').json()=={'items':[],'total':0}
    assert client.get('/api/ordenes-pago/recibos').json()['total']==0
    assert client.get('/api/ordenes-pago?pageSize=101').status_code==422
    assert client.get('/api/ordenes-pago?estado=Otro').status_code==422


def test_roles_y_sesion(client):
    client.cookies.set(COOKIE_NAME,crear_token(1,'Lectura'))
    for path in ['/api/ordenes-pago/1/emitir','/api/ordenes-pago/1/anular','/api/ordenes-pago/recibos/1/vincular']:
        assert client.post(path,json={}).status_code==403
    client.cookies.clear()
    assert client.get('/api/ordenes-pago').status_code==401


def test_error_y_inexistente(client,monkeypatch):
    def missing(*a):raise LookupError('No existe')
    def conflict(*a):raise ValueError('Saldo cambió')
    monkeypatch.setattr(repo,'obtener',missing)
    monkeypatch.setattr(repo,'cambiar_estado',conflict)
    assert client.get('/api/ordenes-pago/99').status_code==404
    assert client.post('/api/ordenes-pago/1/emitir').status_code==409
