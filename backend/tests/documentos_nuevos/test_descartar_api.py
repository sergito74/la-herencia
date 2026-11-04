"""04/11/2026: 'No es una compra' respondía 'Field required' (faltaba importar Descarte en el router)."""

from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME
from src.main import app


def test_descartar_lee_el_motivo_del_cuerpo():
    c = TestClient(app, cookies={COOKIE_NAME: crear_token(id_usuario=0, rol="Administrador")})
    r = c.post("/api/documentos-nuevos/999999999/descartar", json={"motivo": "es un recordatorio"})
    assert r.status_code == 409  # llega al repositorio: el id no existe
