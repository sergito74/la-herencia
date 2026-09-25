"""Tests de /api/conciliacion-historico (020, US2) — ver contracts/api.md.
Monkeypatch sobre repository (no escribe/lee WC real, mismo criterio que
test_aplicaciones_pago_endpoints.py)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.conciliacion_historico import repository
from src.main import app

client = TestClient(app)
client.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))


def test_resumen_endpoint_devuelve_conteos_por_contacto(monkeypatch):
    monkeypatch.setattr(
        repository,
        "resumen_por_contacto",
        lambda solo_con_dudas: [
            {
                "idContacto": 123,
                "razonSocial": "Cargill",
                "aplicadosExactos": 240,
                "aplicadosMejorEsfuerzo": 2,
                "revisionManual": 5,
                "fueraDeAlcance": 0,
            }
        ],
    )
    response = client.get("/api/conciliacion-historico/resumen")
    assert response.status_code == 200
    body = response.json()
    assert body["contactos"][0]["idContacto"] == 123
    assert body["contactos"][0]["revisionManual"] == 5


def test_resumen_endpoint_pasa_el_filtro_solo_con_dudas(monkeypatch):
    llamadas = []
    monkeypatch.setattr(repository, "resumen_por_contacto", lambda solo_con_dudas: llamadas.append(solo_con_dudas) or [])
    client.get("/api/conciliacion-historico/resumen?soloConDudas=true")
    assert llamadas == [True]


def test_detalle_endpoint_devuelve_aplicaciones_y_excepciones(monkeypatch):
    monkeypatch.setattr(
        repository,
        "detalle_contacto",
        lambda id_contacto: {
            "idContacto": id_contacto,
            "aplicaciones": [
                {
                    "idAplicacion": 1,
                    "origen": "automatica-mejor-esfuerzo",
                    "origenMovimiento": "bna",
                    "idMovimientoOrigen": 10,
                    "tipoDocumento": "CompraDeuda",
                    "idDocumentoAplicado": 5,
                    "importeAplicado": 900.0,
                    "notaConciliacion": "Diferencia de $15.00 (1.5%)",
                }
            ],
            "excepciones": [
                {
                    "origenMovimiento": "efectivo",
                    "idMovimientoOrigen": 20,
                    "subcategoria": "con-documento-sin-pendiente",
                    "motivo": "sin documentos candidatos",
                }
            ],
        },
    )
    response = client.get("/api/conciliacion-historico/123/detalle")
    assert response.status_code == 200
    body = response.json()
    assert body["aplicaciones"][0]["origen"] == "automatica-mejor-esfuerzo"
    assert body["excepciones"][0]["subcategoria"] == "con-documento-sin-pendiente"
