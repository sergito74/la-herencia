"""Tests de /api/cuentas-socios (021) — ver contracts/api.md. Monkeypatch
sobre repository (no escribe/lee WC real, mismo criterio que
test_aplicaciones_pago_endpoints.py)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.cuentas_socios import repository
from src.main import app

client = TestClient(app)
client.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))


def test_listar_socios_devuelve_los_4_con_saldo(monkeypatch):
    monkeypatch.setattr(
        repository,
        "listar_socios_con_saldo",
        lambda: [
            {"idSocio": 1, "nombre": "Sergio", "saldo": 29699.10},
            {"idSocio": 2, "nombre": "Lucy", "saldo": 0.0},
            {"idSocio": 3, "nombre": "Cond LSC", "saldo": -5000.0},
            {"idSocio": 4, "nombre": "Ceci", "saldo": 0.0},
        ],
    )
    response = client.get("/api/cuentas-socios")
    assert response.status_code == 200
    body = response.json()
    assert len(body["socios"]) == 4
    assert body["socios"][1]["saldo"] == 0.0


def test_compras_particulares_candidatas(monkeypatch):
    monkeypatch.setattr(
        repository,
        "listar_compras_particulares_candidatas",
        lambda proveedor: [
            {"idCompra": 2143515240, "fecha": "2025-11-14", "proveedor": "Cumo Store", "numeroDocumento": "0004-1", "importePersonal": 29699.10}
        ],
    )
    response = client.get("/api/cuentas-socios/compras-particulares-candidatas?proveedor=Cumo")
    assert response.status_code == 200
    assert response.json()["compras"][0]["proveedor"] == "Cumo Store"


def test_asignar_gasto_devuelve_201(monkeypatch):
    monkeypatch.setattr(
        repository,
        "asignar_gasto",
        lambda id_socio, id_compra, usuario, motivo: {
            "idMovimiento": 42,
            "idSocio": id_socio,
            "tipo": "AsignacionGasto",
            "importe": 29699.10,
            "fecha": "2025-11-14T00:00:00",
            "origen": "CompraParticular",
            "idOrigen": id_compra,
            "medio": None,
            "motivo": motivo,
            "usuario": usuario,
            "anulada": False,
            "motivoAnulacion": None,
        },
    )
    response = client.post("/api/cuentas-socios/1/asignar-gasto", json={"idCompra": 2143515240, "motivo": None})
    assert response.status_code == 201
    assert response.json()["idMovimiento"] == 42


def test_asignar_gasto_ya_vigente_devuelve_409(monkeypatch):
    def _raise(*a, **k):
        raise ValueError("La compra 2143515240 ya tiene una asignación vigente a un socio.")

    monkeypatch.setattr(repository, "asignar_gasto", _raise)
    response = client.post("/api/cuentas-socios/1/asignar-gasto", json={"idCompra": 2143515240})
    assert response.status_code == 409


def test_anular_movimiento(monkeypatch):
    monkeypatch.setattr(
        repository,
        "anular_movimiento",
        lambda id_movimiento, motivo, usuario: {
            "idMovimiento": id_movimiento,
            "idSocio": 1,
            "tipo": "AsignacionGasto",
            "importe": 100.0,
            "fecha": "2025-11-14T00:00:00",
            "origen": "CompraParticular",
            "idOrigen": 1,
            "medio": None,
            "motivo": None,
            "usuario": "sgiamberardini",
            "anulada": True,
            "motivoAnulacion": motivo,
        },
    )
    response = client.post("/api/cuentas-socios/movimientos/42/anular", json={"motivo": "Error"})
    assert response.status_code == 200
    assert response.json()["anulada"] is True


def test_detalle_socio_incluye_saldo_y_movimientos(monkeypatch):
    monkeypatch.setattr(repository, "listar_movimientos", lambda id_socio: [])
    monkeypatch.setattr(repository, "calcular_saldo", lambda id_socio: 0.0)
    monkeypatch.setattr("src.features.cuentas_socios.router.fetch_one", lambda sql, params=(): {"nombre": "Sergio"})
    response = client.get("/api/cuentas-socios/1/movimientos")
    assert response.status_code == 200
    body = response.json()
    assert body["nombre"] == "Sergio"
    assert body["saldo"] == 0.0


def test_detalle_socio_inexistente_devuelve_404(monkeypatch):
    monkeypatch.setattr("src.features.cuentas_socios.router.fetch_one", lambda sql, params=(): None)
    response = client.get("/api/cuentas-socios/999/movimientos")
    assert response.status_code == 404


def test_registrar_devolucion(monkeypatch):
    monkeypatch.setattr(
        repository,
        "registrar_devolucion",
        lambda id_socio, importe, fecha, medio, motivo, usuario: {
            "idMovimiento": 43,
            "idSocio": id_socio,
            "tipo": "Devolucion",
            "importe": importe,
            "fecha": "2025-11-20T00:00:00",
            "origen": None,
            "idOrigen": None,
            "medio": medio,
            "motivo": motivo,
            "usuario": usuario,
            "anulada": False,
            "motivoAnulacion": None,
        },
    )
    response = client.post(
        "/api/cuentas-socios/1/devolucion",
        json={"importe": 15000.0, "fecha": "2025-11-20", "medio": "Transferencia", "motivo": "Devolución parcial"},
    )
    assert response.status_code == 201
    assert response.json()["tipo"] == "Devolucion"
