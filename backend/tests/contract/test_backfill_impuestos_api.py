import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.features.backfill_impuestos import repository
import src.main as main

@pytest.fixture(autouse=True)
def no_db(monkeypatch):
    import pyodbc
    monkeypatch.setattr(pyodbc,'connect',lambda *a,**k: pytest.fail('SQL real bloqueado'))

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main,'verificar_token',lambda t: {'idUsuario':1,'rol':'Lectura'} if t=='read' else None)
    with TestClient(app,raise_server_exceptions=False) as c:
        from src.features.auth.router import COOKIE_NAME
        c.cookies.set(COOKIE_NAME,'read')
        yield c

def test_diagnostico_y_limite(client,monkeypatch):
    monkeypatch.setattr(repository,'diagnostico',lambda *a: dict(items=[],total=0,page=1,pageSize=50))
    res=client.get('/api/impuestos/backfill/diagnostico')
    assert res.status_code==200 and res.json()['items']==[]
    assert client.get('/api/impuestos/backfill/diagnostico?pageSize=201').status_code==422

def test_auth(client):
    assert client.post('/api/impuestos/backfill/validar',json={}).status_code==403
    client.cookies.clear()
    assert client.get('/api/impuestos/backfill/diagnostico').status_code==401

def test_db_error(client,monkeypatch):
    import pyodbc
    def fail(*a): raise pyodbc.Error('private details')
    monkeypatch.setattr(repository,'diagnostico',fail)
    res=client.get('/api/impuestos/backfill/diagnostico')
    assert res.status_code==503 and 'private' not in res.text
