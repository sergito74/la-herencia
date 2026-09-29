"""Tests de /api/reasignacion-contacto — ver contracts/api.md. Monkeypatch
sobre repository (no escribe/lee WC real, mismo criterio que
test_aplicaciones_pago_endpoints.py)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.reasignacion_contacto import repository
from src.main import app

client = TestClient(app)
client.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))


def _reasignacion(**overrides):
    base = {
        "idReasignacion": 1,
        "origen": "Galicia",
        "idOrigen": 2712,
        "idContactoAnterior": 605,
        "idContactoNuevo": 1652,
        "contactoAnterior": "Carbajo, Juan Manuel",
        "contactoNuevo": "Encode S.A.",
        "motivo": "El texto de la transferencia dice Encode S.A.",
        "usuario": "sgiamberardini",
        "fecha": "2026-09-25T21:00:00",
    }
    base.update(overrides)
    return base


def test_reasignar_devuelve_201(monkeypatch):
    monkeypatch.setattr(
        repository, "reasignar", lambda origen, idOrigen, idContactoNuevo, usuario, motivo: _reasignacion()
    )
    response = client.post(
        "/api/reasignacion-contacto/reasignar",
        json={"origen": "Galicia", "idOrigen": 2712, "idContactoNuevo": 1652, "motivo": "x"},
    )
    assert response.status_code == 201
    assert response.json()["idReasignacion"] == 1


def test_reasignar_mismo_contacto_devuelve_409(monkeypatch):
    def _raise(*a, **k):
        raise ValueError("El movimiento ya está asignado a ese contacto.")

    monkeypatch.setattr(repository, "reasignar", _raise)
    response = client.post(
        "/api/reasignacion-contacto/reasignar",
        json={"origen": "Galicia", "idOrigen": 2712, "idContactoNuevo": 1652},
    )
    assert response.status_code == 409


def test_reasignar_origen_no_soportado_devuelve_400(monkeypatch):
    def _raise(*a, **k):
        raise ValueError("El origen 'Impuestos' todavía no admite reasignación.")

    monkeypatch.setattr(repository, "reasignar", _raise)
    response = client.post(
        "/api/reasignacion-contacto/reasignar",
        json={"origen": "Impuestos", "idOrigen": 1, "idContactoNuevo": 119},
    )
    assert response.status_code == 400


def test_reasignar_contacto_inexistente_devuelve_404(monkeypatch):
    def _raise(*a, **k):
        raise ValueError("El contacto 999999 no existe.")

    monkeypatch.setattr(repository, "reasignar", _raise)
    response = client.post(
        "/api/reasignacion-contacto/reasignar",
        json={"origen": "Galicia", "idOrigen": 2712, "idContactoNuevo": 999999},
    )
    assert response.status_code == 404


def test_historial_sin_filtro(monkeypatch):
    monkeypatch.setattr(repository, "listar_historial", lambda origen, idOrigen: [_reasignacion()])
    response = client.get("/api/reasignacion-contacto/historial")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_historial_con_filtro(monkeypatch):
    capturado = {}

    def _fake(origen, idOrigen):
        capturado["origen"] = origen
        capturado["idOrigen"] = idOrigen
        return [_reasignacion()]

    monkeypatch.setattr(repository, "listar_historial", _fake)
    response = client.get("/api/reasignacion-contacto/historial?origen=Galicia&idOrigen=2712")
    assert response.status_code == 200
    assert capturado == {"origen": "Galicia", "idOrigen": 2712}


def test_candidatos(monkeypatch):
    monkeypatch.setattr(
        repository,
        "detectar_candidatos",
        lambda: [
            {
                "origen": "Galicia",
                "idOrigen": 2712,
                "fecha": "2025-08-01",
                "descripcion": "TRF INMED PROVEED Encode S.A. ...",
                "importe": 159720.0,
                "idContactoActual": 605,
                "contactoActual": "Carbajo, Juan Manuel",
                "idContactoSugerido": 1652,
                "contactoSugerido": "Encode S.A.",
            }
        ],
    )
    response = client.get("/api/reasignacion-contacto/candidatos")
    assert response.status_code == 200
    assert response.json()["candidatos"][0]["contactoSugerido"] == "Encode S.A."


def test_descartar_candidato(monkeypatch):
    llamado = {}
    monkeypatch.setattr(
        repository,
        "descartar_candidato",
        lambda origen, idOrigen, idContactoSugerido, usuario: llamado.update(
            origen=origen, idOrigen=idOrigen, idContactoSugerido=idContactoSugerido
        ),
    )
    response = client.post(
        "/api/reasignacion-contacto/candidatos/descartar",
        json={"origen": "Galicia", "idOrigen": 2633, "idContactoSugerido": 575},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert llamado == {"origen": "Galicia", "idOrigen": 2633, "idContactoSugerido": 575}
