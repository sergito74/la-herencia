"""Contrato 038: nunca conecta a WC. Permisos, exactitud, avisos y atomicidad."""

from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.db import connection
from src.features.cajas_efectivo import operaciones as db, router, service
from src.features.cajas_efectivo.schemas import OperacionCaja


@pytest.fixture
def caja(monkeypatch):
    # Fail closed if a test accidentally reaches production.
    def forbidden(*args, **kwargs):
        raise AssertionError("Ninguna prueba 038 puede conectar a WC")

    monkeypatch.setattr(connection.pyodbc, "connect", forbidden)
    state = {"ops": {}, "effects": [], "balance": Decimal("100.00"), "arqueos": []}

    @contextmanager
    def transaction():
        before = deepcopy(state)
        try:
            yield
        except Exception:
            state.clear()
            state.update(before)
            raise

    monkeypatch.setattr(connection, "reconciliation_transaction", transaction)

    def locks(sql, params=()):
        assert "WITH (UPDLOCK,HOLDLOCK)" in sql
        return []

    monkeypatch.setattr(db, "read", locks)
    monkeypatch.setattr(service, "_references", lambda op: {})
    monkeypatch.setattr(
        db,
        "caja_context",
        lambda *a: {
            "saldoActual": state["balance"],
            "saldoFecha": state["balance"],
            "minimoPosterior": state["balance"],
            "arqueos": state["arqueos"],
        },
    )
    monkeypatch.setattr(db, "find_key", lambda key: state["ops"].get(str(key)))

    def create(key, fingerprint, op, context, user):
        row = {
            "IdOperacion": len(state["ops"]) + 1,
            "HuellaSolicitud": fingerprint,
            "Estado": "Vigente",
            "Version": 0,
        }
        state["ops"][str(key)] = row
        return row["IdOperacion"]

    monkeypatch.setattr(db, "create_operation", create)
    monkeypatch.setattr(
        db,
        "detail",
        lambda id: {"idOperacion": id, "estado": "Vigente", "efectos": list(state["effects"])},
    )
    monkeypatch.setattr(service, "_aplicar", lambda *a: state["effects"].append("cash"))
    monkeypatch.setattr(router, "fetch_one", lambda *a: {"nombre": "usuario_prueba"})
    app = FastAPI()

    @app.middleware("http")
    async def session(request: Request, call_next):
        role = request.headers.get("X-Test-Role", "Escritura")
        if role != "Anonimo":
            request.state.usuario = {"idUsuario": 1, "rol": role}
        return await call_next(request)

    app.include_router(router.router)
    return TestClient(app), state


def operation(**overrides):
    return {
        "tipo": "traspaso_cajas",
        "caja": "giamigli-sa",
        "cajaDestino": "campo-chica",
        "fecha": "2026-10-22",
        "importe": "10.01",
        "concepto": "Reposición",
        "cuenta": "A",
        **overrides,
    }


def confirm(client, op, key=None, warnings=None):
    preview = client.post("/api/cajas-efectivo/operaciones/previsualizar", json=op)
    assert preview.status_code == 200, preview.text
    return client.post(
        "/api/cajas-efectivo/operaciones",
        headers={"Idempotency-Key": str(key or uuid4())},
        json={
            "operacion": op,
            "previewVersion": preview.json()["previewVersion"],
            "advertenciasAceptadas": warnings or [],
        },
    )


def test_preview_decimal_no_escribe(caja):
    client, state = caja
    response = client.post("/api/cajas-efectivo/operaciones/previsualizar", json=operation())
    assert response.status_code == 200
    legs = response.json()["efectosPrevistos"]
    assert [x["importe"] for x in legs] == ["-10.01", "10.01"]
    assert legs[0]["saldoResultante"] == "89.99"
    assert state["ops"] == {} and state["effects"] == []


@pytest.mark.parametrize("role,expected", [("Lectura", 403), ("Anonimo", 401)])
def test_permiso_antes_de_escribir(caja, role, expected):
    client, state = caja
    r = client.post(
        "/api/cajas-efectivo/operaciones/previsualizar",
        json=operation(),
        headers={"X-Test-Role": role},
    )
    assert r.status_code == expected
    assert not state["ops"]


def test_reintento_idempotente(caja):
    client, state = caja
    op, key = operation(), uuid4()
    first = confirm(client, op, key)
    assert first.status_code == 201
    state["balance"] += 5  # Context changed after success: retry still returns original.
    second = client.post(
        "/api/cajas-efectivo/operaciones",
        headers={"Idempotency-Key": str(key)},
        json={"operacion": op, "previewVersion": "0" * 64},
    )
    assert second.status_code == 200 and second.json() == first.json()
    assert len(state["ops"]) == 1 and state["effects"] == ["cash"]
    third = confirm(client, operation(importe="11.00"), key)
    assert third.status_code == 409
    assert state["effects"] == ["cash"]


def test_preview_obsoleta_y_avisos(caja):
    client, state = caja
    op = operation(importe="200.00")
    preview = client.post("/api/cajas-efectivo/operaciones/previsualizar", json=op).json()
    assert preview["advertencias"] == ["SALDO_NEGATIVO"]
    body = {"operacion": op, "previewVersion": preview["previewVersion"]}
    assert (
        client.post(
            "/api/cajas-efectivo/operaciones", json=body, headers={"Idempotency-Key": str(uuid4())}
        ).status_code
        == 409
    )
    state["balance"] = Decimal("101")
    body["advertenciasAceptadas"] = ["SALDO_NEGATIVO"]
    assert (
        client.post(
            "/api/cajas-efectivo/operaciones", json=body, headers={"Idempotency-Key": str(uuid4())}
        ).status_code
        == 409
    )
    state["arqueos"] = [{"id": 1}]
    assert confirm(client, op, warnings=["SALDO_NEGATIVO", "PERIODO_ARQUEADO"]).status_code == 201


def test_fallo_adaptador_revierte_y_no_expone_sql(caja, monkeypatch):
    client, state = caja

    def fail(*args):
        state["effects"].append("partial")
        raise RuntimeError("SQL secret internal")

    monkeypatch.setattr(service, "_aplicar", fail)
    response = confirm(client, operation())
    assert response.status_code == 500 and "secret" not in response.text
    assert not state["ops"] and not state["effects"]


@pytest.mark.parametrize(
    "changes",
    [
        {"importe": "0"},
        {"importe": "1.001"},
        {"cuenta": "X"},
        {"concepto": ""},
        {"cajaDestino": "giamigli-sa"},
        {"cajaDestino": "condominio-lsc"},
        {"idSocio": 1},
        {"idContacto": 375},
        {"campoLibre": "SQL"},
    ],
)
def test_combinaciones_invalidas(caja, changes):
    client, state = caja
    assert (
        client.post(
            "/api/cajas-efectivo/operaciones/previsualizar", json=operation(**changes)
        ).status_code
        == 422
    )
    assert not state["ops"]


def test_condominio_dos_piernas_un_aporte():
    op = OperacionCaja.model_validate(
        operation(
            tipo="aporte",
            cajaDestino=None,
            cajaContraparte="condominio-lsc",
            idSocio=3,
            motivoRelacionGiamigli="Aporte de socio",
        )
    )
    assert service.piernas(op) == {
        "giamigli-sa": Decimal("10.01"),
        "condominio-lsc": Decimal("-10.01"),
    }
