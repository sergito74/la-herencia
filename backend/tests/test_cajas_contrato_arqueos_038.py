from contextlib import nullcontext
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.db import connection
from src.features.cajas_efectivo import operaciones as db, router


@pytest.fixture
def count(monkeypatch):
    monkeypatch.setattr(
        connection.pyodbc, "connect", lambda *a, **k: pytest.fail("Conexión a WC prohibida")
    )
    monkeypatch.setattr(connection, "reconciliation_transaction", nullcontext)
    monkeypatch.setattr(router, "_usuario", lambda req: "prueba")
    state = {
        "saldo": Decimal("1000.90"),
        "secuencia": 1,
        "a": None,
        "denom": [],
        "ops": 0,
        "all": {},
    }

    def one(sql, params=()):
        if "SELECT * FROM dbo.Arqueos" in sql:
            return state["all"].get(params[1])
        if "MAX(IdMovimiento)" in sql:
            return {"secuencia": state["secuencia"]}
        if "SUM(Importe)" in sql:
            return {"saldo": state["saldo"]}
        raise AssertionError(sql)

    def insert(sql, params):
        if "INSERT INTO dbo.Arqueos" in sql:
            state["a"] = {
                "IdArqueo": len(state["all"]) + 1,
                "FechaCorte": params[0],
                "SecuenciaCorte": params[1],
                "SaldoSistema": params[2],
                "TotalContado": params[3],
                "Diferencia": params[4],
                "IdArqueoAnterior": params[5],
                "IdOperacionAjuste": None,
                "Estado": "Borrador",
                "Version": 0,
                "Usuario": "prueba",
                "UsuarioConfirmacion": None,
                "MotivoInvalidacion": None,
            }
            state["all"][state["a"]["IdArqueo"]] = state["a"]
            return state["a"]["IdArqueo"]
        if "INSERT INTO dbo.Operaciones" in sql:
            state["ops"] += 1
            state["operation"] = {
                "IdOperacion": state["ops"],
                "Version": 0,
                "Estado": "Vigente",
                "Solicitud": params[4],
            }
            return state["ops"]
        if "INSERT INTO dbo.MovimientosCaja" in sql:
            state["saldo"] += params[3]
            state["secuencia"] += 1
            return state["secuencia"]
        raise AssertionError(sql)

    def write(sql, params=()):
        if "INSERT INTO dbo.ArqueoDenominaciones" in sql:
            state["denom"].append(
                {"IdArqueo": params[0], "Denominacion": params[1], "Cantidad": params[2]}
            )
        elif "Estado='Confirmado',SaldoSistema" in sql:
            state["a"].update(
                Estado="Confirmado",
                SaldoSistema=params[0],
                Diferencia=params[1],
                IdOperacionAjuste=params[2],
                UsuarioConfirmacion=params[3],
                Version=1,
            )
        elif "Estado='Desactualizado'" in sql:
            for a in state["all"].values():
                if a["Estado"] == "Confirmado":
                    a.update(Estado="Desactualizado", Version=a["Version"] + 1)
        elif "UPDATE dbo.MovimientosCajaEfectivo SET Anulada=1" in sql:
            state["saldo"] -= state["a"]["Diferencia"]
        elif "UPDATE dbo.OperacionesCajaEfectivo" in sql:
            state["operation"].update(Estado="Anulada", Version=1)
        elif "Estado='Invalidado'" in sql:
            for a in state["all"].values():
                if a["IdOperacionAjuste"] == params[-1]:
                    a.update(Estado="Invalidado", Version=a["Version"] + 1)
        else:
            raise AssertionError(sql)
        return 1

    monkeypatch.setattr(db, "one", one)
    monkeypatch.setattr(db, "insert", insert)
    monkeypatch.setattr(db, "write", write)
    monkeypatch.setattr(
        db, "read", lambda sql, params=(): [x for x in state["denom"] if x["IdArqueo"] == params[0]]
    )
    monkeypatch.setattr(db, "get_operation", lambda id: state.get("operation"))
    monkeypatch.setattr(db, "effects", lambda id: [])
    monkeypatch.setattr(db, "detail", lambda id: state["operation"])
    monkeypatch.setattr(
        db, "caja_context", lambda *a, **k: {"minimoPosterior": Decimal("1000.90"), "saldoActual": state["saldo"], "arqueos": []}
    )
    app = FastAPI()
    app.include_router(router.router)
    return TestClient(app), state


def test_diferencia_24910_confirmada_una_vez(count):
    client, state = count
    r = client.post(
        "/api/cajas-efectivo/giamigli-sa/arqueos",
        json={
            "fechaCorte": "2026-10-22",
            "denominaciones": [
                {"valor": "1000", "cantidad": 1},
                {"valor": "100", "cantidad": 2},
                {"valor": "50", "cantidad": 1},
            ],
        },
    )
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["diferencia"] == "249.10" and state["ops"] == 0
    body = {
        "versionEsperada": a["version"],
        "previewVersion": a["previewVersion"],
        "aceptarDiferencia": True,
    }
    r = client.post("/api/cajas-efectivo/giamigli-sa/arqueos/1/confirmar", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "Confirmado" and r.json()["diferenciaVigenteDecimal"] == "0.00"
    assert state["saldo"] == 1250 and state["ops"] == 1
    assert (
        client.post("/api/cajas-efectivo/giamigli-sa/arqueos/1/confirmar", json=body).status_code
        == 200
    )
    assert state["ops"] == 1


def test_cero_no_ajusta_y_cambio_saldo_conflicto(count):
    client, state = count
    state["saldo"] = Decimal("1000")
    a = client.post(
        "/api/cajas-efectivo/giamigli-sa/arqueos",
        json={"fechaCorte": "2026-10-22", "denominaciones": [{"valor": "1000", "cantidad": 1}]},
    ).json()
    body = {"versionEsperada": 0, "previewVersion": a["previewVersion"]}
    state["saldo"] = Decimal("999")
    assert (
        client.post("/api/cajas-efectivo/giamigli-sa/arqueos/1/confirmar", json=body).status_code
        == 409
    )
    state["saldo"] = Decimal("1000")
    assert (
        client.post("/api/cajas-efectivo/giamigli-sa/arqueos/1/confirmar", json=body).status_code
        == 200
    )
    assert state["ops"] == 0


@pytest.mark.parametrize(
    "denom",
    [
        [{"valor": "0", "cantidad": 1}],
        [{"valor": "100", "cantidad": -1}],
        [{"valor": "100", "cantidad": 1}, {"valor": "100", "cantidad": 2}],
    ],
)
def test_denominaciones_invalidas(count, denom):
    client, state = count
    assert (
        client.post(
            "/api/cajas-efectivo/giamigli-sa/arqueos",
            json={"fechaCorte": "2026-10-22", "denominaciones": denom},
        ).status_code
        == 422
    )
    assert state["a"] is None
