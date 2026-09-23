from fastapi.testclient import TestClient

from src.auth.tokens import crear_token

from src.features.sesion import router as sesion
from src.main import app

client = TestClient(app)
client.cookies.set(
    "la_herencia_session",
    crear_token(id_usuario=0, rol="Administrador"),
)  # 016-autenticacion: la API ahora exige sesión; estos tests preexistentes
# simulan un Administrador para no cambiar su comportamiento (SC-003).


def _post(path: str, body: str) -> None:
    r = client.post(f"/api/sesion/{path}", content=body, headers={"content-type": "text/plain"})
    assert r.status_code == 204


def setup_function() -> None:
    sesion._estado.reiniciar()


def test_latido_abre_pestana_y_cierre_la_quita():
    _post("latido", '{"tabId": "a", "activo": true}')
    e = client.get("/api/sesion/estado").json()
    assert e["pestanasAbiertas"] == 1 and e["huboPestana"] and e["segundosSinPestanas"] == 0

    _post("cierre", '{"tabId": "a"}')
    e = client.get("/api/sesion/estado").json()
    assert e["pestanasAbiertas"] == 0 and e["huboPestana"]


def test_una_pestana_cerrada_con_otra_abierta_no_deja_sin_pestanas():
    _post("latido", '{"tabId": "a"}')
    _post("latido", '{"tabId": "b"}')
    _post("cierre", '{"tabId": "a"}')
    assert client.get("/api/sesion/estado").json()["pestanasAbiertas"] == 1


def test_latido_pasivo_no_cuenta_como_actividad():
    sesion._estado.ultima_actividad -= 500
    _post("latido", '{"tabId": "a", "activo": false}')
    assert client.get("/api/sesion/estado").json()["segundosSinActividad"] >= 500
    _post("latido", '{"tabId": "a", "activo": true}')
    assert client.get("/api/sesion/estado").json()["segundosSinActividad"] < 5


def test_pestana_sin_latidos_expira():
    _post("latido", '{"tabId": "a"}')
    sesion._estado.tabs["a"] -= sesion.TAB_TIMEOUT_S + 1
    assert client.get("/api/sesion/estado").json()["pestanasAbiertas"] == 0


def test_cuerpo_invalido_se_ignora():
    _post("latido", "no es json")
    assert client.get("/api/sesion/estado").json()["pestanasAbiertas"] == 0
