"""Tests del endpoint `POST /api/remuneraciones` (028) — TestClient +
monkeypatch sobre repository, sin tocar WC real. Mismo patrón que el
resto de los tests de router de este proyecto (ej.
`test_cuentas_socios_endpoints.py`)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.main import app
from src.features.remuneraciones import repository

client = TestClient(app)
client.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))

_BODY = {
    "idContacto": 46,
    "fechaPago": "2026-09-30",
    "periodoLiquidado": "Septiembre 2026",
    "sueldoBasico": 85096.38,
    "jubilacion": 18631.02,
    "obraSocial": 5081.19,
    "aporteSindical": 3471.43,
}


def test_crear_liquidacion_devuelve_201_y_neto(monkeypatch):
    monkeypatch.setattr(repository, "existe_contacto_empleado", lambda id_contacto: True)
    monkeypatch.setattr(repository, "existe_liquidacion_periodo", lambda *a: None)
    monkeypatch.setattr(
        repository,
        "crear_liquidacion",
        lambda request: {"idSalario": 1829633233, "importeNeto": 57912.74},
    )

    response = client.post("/api/remuneraciones", json=_BODY)

    assert response.status_code == 201
    assert response.json() == {"idSalario": 1829633233, "importeNeto": 57912.74, "recibo": None}


def test_crear_liquidacion_rechaza_contacto_no_empleado(monkeypatch):
    monkeypatch.setattr(repository, "existe_contacto_empleado", lambda id_contacto: False)

    response = client.post("/api/remuneraciones", json=_BODY)

    assert response.status_code == 400


def test_crear_liquidacion_avisa_duplicado_sin_bloquear(monkeypatch):
    monkeypatch.setattr(repository, "existe_contacto_empleado", lambda id_contacto: True)
    monkeypatch.setattr(repository, "existe_liquidacion_periodo", lambda *a: 1829633180)

    response = client.post("/api/remuneraciones", json=_BODY)

    assert response.status_code == 409
    assert "1829633180" in response.json()["detail"]


def test_crear_liquidacion_confirmar_duplicado_crea_igual(monkeypatch):
    monkeypatch.setattr(repository, "existe_contacto_empleado", lambda id_contacto: True)
    monkeypatch.setattr(repository, "existe_liquidacion_periodo", lambda *a: 1829633180)
    monkeypatch.setattr(
        repository,
        "crear_liquidacion",
        lambda request: {"idSalario": 1829633235, "importeNeto": 57912.74},
    )

    response = client.post("/api/remuneraciones", json={**_BODY, "confirmarDuplicado": True})

    assert response.status_code == 201
    assert response.json()["idSalario"] == 1829633235


def _referencia_valida():
    from datetime import date

    return {"fechaPago": date(2026, 9, 30), "empleado": "Armando Oscar Mori"}


def test_adjuntar_recibo_ok(monkeypatch):
    monkeypatch.setattr(repository, "get_recibo_referencia", lambda id_salario: _referencia_valida())
    monkeypatch.setattr(
        repository,
        "guardar_recibo",
        lambda id_salario, fecha_pago, empleado, contenido: "Personal\\Recibos\\2026\\2026 09 Armando Oscar Mori.pdf",
    )

    response = client.post(
        "/api/remuneraciones/1829633233/recibo",
        files={"archivo": ("recibo.pdf", b"%PDF-1.4 contenido", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "idSalario": 1829633233,
        "recibo": "Personal\\Recibos\\2026\\2026 09 Armando Oscar Mori.pdf",
    }


def test_adjuntar_recibo_404_si_no_existe_liquidacion(monkeypatch):
    monkeypatch.setattr(repository, "get_recibo_referencia", lambda id_salario: None)

    response = client.post(
        "/api/remuneraciones/999/recibo",
        files={"archivo": ("recibo.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 404


def test_adjuntar_recibo_rechaza_no_pdf(monkeypatch):
    monkeypatch.setattr(repository, "get_recibo_referencia", lambda id_salario: _referencia_valida())

    def fake_guardar_recibo(*a, **kw):
        raise ValueError("El archivo no es un PDF válido.")

    monkeypatch.setattr(repository, "guardar_recibo", fake_guardar_recibo)

    response = client.post(
        "/api/remuneraciones/1829633233/recibo",
        files={"archivo": ("foto.jpg", b"no es un pdf", "image/jpeg")},
    )

    assert response.status_code == 400


def test_adjuntar_recibo_rechaza_archivo_grande(monkeypatch):
    monkeypatch.setattr(repository, "get_recibo_referencia", lambda id_salario: _referencia_valida())

    contenido_grande = b"%PDF-1.4" + b"0" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/api/remuneraciones/1829633233/recibo",
        files={"archivo": ("recibo.pdf", contenido_grande, "application/pdf")},
    )

    assert response.status_code == 400
