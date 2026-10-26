from fastapi.testclient import TestClient
from src.main import app
from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME

client = TestClient(app)
client.cookies.set(COOKIE_NAME, crear_token(id_usuario=0, rol="Administrador"))


def test_cotizaciones_endpoint():
    response = client.get("/api/finanzas/cotizaciones?mes=2026-10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    primer = data[0]
    assert "fecha" in primer
    assert "inmag" in primer
    assert "dolarPromedioBillete" in primer

