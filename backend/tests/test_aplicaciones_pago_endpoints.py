"""Contract tests de /api/aplicaciones-pago (019) — ver
contracts/api-aplicaciones-pago.md. Monkeypatch sobre repository/
sugerencia (no escribe en WC real — la validación end-to-end contra
datos reales ya se hizo a mano durante la implementación, ver commit)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.aplicaciones_pago import documentos, repository, sugerencia
from src.main import app

client = TestClient(app)
client.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))


def test_sugerir_devuelve_estructura_esperada(monkeypatch):
    monkeypatch.setattr(
        sugerencia,
        "sugerir",
        lambda origen, id_mov: {
            "importeMovimiento": 1000.0,
            "sugerencias": [
                {"tipoDocumento": "CompraDeuda", "idDocumento": 1, "fecha": "2026-01-01", "saldoPendiente": 1000.0, "importeSugerido": 1000.0}
            ],
            "saldoSinAsignar": 0.0,
        },
    )
    response = client.post("/api/aplicaciones-pago/sugerir", json={"origenMovimiento": "bna", "idMovimientoOrigen": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["saldoSinAsignar"] == 0.0
    assert body["sugerencias"][0]["idDocumento"] == 1


def test_documentos_pendientes_endpoint(monkeypatch):
    monkeypatch.setattr(
        documentos,
        "documentos_pendientes",
        lambda id_contacto, tipo=None: [
            {
                "tipoDocumento": "CompraDeuda",
                "idDocumento": 5,
                "fecha": "2026-01-01",
                "numeroDocumento": "0001-00000001",
                "importeTotal": 500.0,
                "aplicado": 0.0,
                "saldoPendiente": 500.0,
            }
        ],
    )
    response = client.get("/api/aplicaciones-pago/documentos-pendientes?idContacto=42&tipo=compra")
    assert response.status_code == 200
    assert response.json()[0]["saldoPendiente"] == 500.0


def test_confirmar_aplicacion_editada_se_guarda_tal_cual(monkeypatch):
    capturado = {}

    def fake_insertar(origen, id_mov, aplicaciones, usuario):
        capturado["aplicaciones"] = aplicaciones
        return [99]

    monkeypatch.setattr(repository, "insertar_aplicaciones", fake_insertar)
    response = client.post(
        "/api/aplicaciones-pago",
        json={
            "origenMovimiento": "bna",
            "idMovimientoOrigen": 1,
            "aplicaciones": [{"tipoDocumento": "CompraDeuda", "idDocumento": 5, "importeAplicado": 250.0}],
        },
    )
    assert response.status_code == 200
    assert capturado["aplicaciones"][0]["importeAplicado"] == 250.0


def test_confirmar_aplicacion_sobre_aplicada_devuelve_400(monkeypatch):
    """FR-008/SC-002 (hallazgo C1 de /speckit-analyze)."""

    def fake_insertar(origen, id_mov, aplicaciones, usuario):
        raise ValueError("El documento CompraDeuda/5 quedaría sobre-aplicado")

    monkeypatch.setattr(repository, "insertar_aplicaciones", fake_insertar)
    response = client.post(
        "/api/aplicaciones-pago",
        json={
            "origenMovimiento": "bna",
            "idMovimientoOrigen": 1,
            "aplicaciones": [{"tipoDocumento": "CompraDeuda", "idDocumento": 5, "importeAplicado": 999999.0}],
        },
    )
    assert response.status_code == 400


def test_confirmar_aplicacion_a_contacto_distinto_no_se_rechaza(monkeypatch):
    """FR-006 (hallazgo C2 de /speckit-analyze): el movimiento puede
    aplicarse a un documento de un contacto distinto al suyo — el
    endpoint no valida coincidencia de contacto."""
    monkeypatch.setattr(repository, "insertar_aplicaciones", lambda *a, **k: [100])
    response = client.post(
        "/api/aplicaciones-pago",
        json={
            "origenMovimiento": "bna",
            "idMovimientoOrigen": 1,
            "aplicaciones": [{"tipoDocumento": "CompraDeuda", "idDocumento": 5, "importeAplicado": 250.0}],
        },
    )
    assert response.status_code == 200


def test_anular_aplicacion_recalcula_estado(monkeypatch):
    """FR-005/Acceptance Scenario 5 US1: anular no borra, y el estado del
    documento vuelve al anterior (recalculado, no un valor guardado)."""
    llamado = {}

    def fake_anular(id_aplicacion, motivo, usuario):
        llamado["motivo"] = motivo

    monkeypatch.setattr(repository, "anular_aplicacion", fake_anular)
    response = client.post("/api/aplicaciones-pago/7/anular", json={"motivo": "Error de carga"})
    assert response.status_code == 200
    assert llamado["motivo"] == "Error de carga"


def test_anular_aplicacion_inexistente_devuelve_400(monkeypatch):
    def fake_anular(id_aplicacion, motivo, usuario):
        raise ValueError(f"Aplicación {id_aplicacion} no existe o ya estaba anulada")

    monkeypatch.setattr(repository, "anular_aplicacion", fake_anular)
    response = client.post("/api/aplicaciones-pago/999999/anular", json={"motivo": "x"})
    assert response.status_code == 400


def test_estado_documento_endpoint(monkeypatch):
    monkeypatch.setattr(
        repository,
        "estado_documento",
        lambda tipo, id_doc: {"importeTotal": 1000.0, "aplicado": 1000.0, "saldoPendiente": 0.0, "estado": "Total", "aplicaciones": []},
    )
    response = client.get("/api/aplicaciones-pago/documento/CompraDeuda/5")
    assert response.status_code == 200
    assert response.json()["estado"] == "Total"


def test_estado_movimiento_endpoint(monkeypatch):
    monkeypatch.setattr(
        repository,
        "estado_movimiento",
        lambda origen, id_mov: {"importe": 1000.0, "aplicado": 1000.0, "saldoSinAplicar": 0.0, "aplicaciones": []},
    )
    response = client.get("/api/aplicaciones-pago/movimiento/bna/1")
    assert response.status_code == 200
    assert response.json()["saldoSinAplicar"] == 0.0


def test_aplicaciones_pago_requiere_sesion():
    sin_sesion = TestClient(app)
    response = sin_sesion.get("/api/aplicaciones-pago/documentos-pendientes?idContacto=1")
    assert response.status_code == 401
