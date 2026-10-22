from contextlib import contextmanager
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

import openpyxl
import pytest

from src.db import connection
from src.features.cajas_efectivo import importacion as imp, operaciones as db, service


def xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Caja Efectivo Pesos"
    ws.append(["Fecha", "Concepto", "Cuenta", "Proveedor", "PC", "Documento", "Importe", "Saldo"])
    for row in rows:
        ws.append(row)
    stream = BytesIO()
    wb.save(stream)
    wb.close()
    return stream.getvalue()


def test_parser_signo_fila_y_duplicados_legitimos():
    content = xlsx(
        [
            [datetime(2026, 10, 22), "Pago", "White", None, None, None, -100, 100],
            [datetime(2026, 10, 22), "Pago", "White", None, None, None, -100, 0],
        ]
    )
    rows = imp.parse(content, "CajasGiamigli", date(2026, 10, 22))
    assert len(rows) == 2 and rows[0]["huella"] == rows[1]["huella"]
    assert [x["fila"] for x in rows] == [2, 3]
    assert (
        rows[0]["normalizada"]["importe"] == "-100.00" and rows[0]["normalizada"]["cuenta"] == "A"
    )


def test_formula_sin_cache_y_limites():
    content = xlsx([[datetime(2026, 10, 22), "Pago", "White", None, None, None, "=1+1", None]])
    assert imp.parse(content, "CajasGiamigli", date(2026, 10, 22))[0]["estado"] == "Ambigua"
    for payload in (b"invalid", b"x" * (10 * 1024 * 1024 + 1)):
        with pytest.raises(ValueError):
            imp.parse(payload, "CajasGiamigli", date(2026, 10, 22))


@pytest.fixture
def lot(monkeypatch):
    monkeypatch.setattr(connection.pyodbc, "connect", lambda *a, **k: pytest.fail("WC prohibida"))
    state = {"lot": None, "rows": [], "movs": [], "creadas": 0}

    @contextmanager
    def tx():
        before = deepcopy(state)
        try:
            yield
        except Exception:
            state.clear()
            state.update(before)
            raise

    monkeypatch.setattr(connection, "reconciliation_transaction", tx)

    def one(sql, params=()):
        if "SELECT TOP 1 f.Huella" in sql:
            return state.get("priorSource")
        if "HuellaArchivo=?" in sql:
            return {"IdLote": 1} if state["lot"] else None
        if "FROM dbo.ImportacionesCaja" in sql:
            return state["lot"]
        if "SUM(Importe)" in sql:
            return {"saldo": Decimal(-100 * state["creadas"])}
        if "COUNT(*) n FROM dbo.Filas" in sql:
            return {
                "n": sum(x["Estado"] in ("Nueva", "Ambigua", "Modificada") for x in state["rows"])
            }
        if "FilaPlanilla=?" in sql:
            return next(
                (
                    {"IdMovimiento": x["idMovimiento"]}
                    for x in state["movs"]
                    if x["filaPlanilla"] == params[1]
                ),
                None,
            )
        if "IdOperacionCaja=? AND Caja=?" in sql:
            return {"IdMovimiento": 100 + params[0]}
        if "IdMovimiento=? AND IdFila<>" in sql:
            return next(
                (
                    x
                    for x in state["rows"]
                    if x["IdMovimiento"] == params[1] and x["IdFila"] != params[2]
                ),
                None,
            )
        raise AssertionError(sql)

    def read(sql, params=()):
        if "FROM dbo.FilasOrigenCaja" in sql:
            return state["rows"]
        if "TOP 20 IdMovimiento" in sql:
            return [x for x in state["movs"] if Decimal(str(x.get("importe", -100))) == params[2]]
        if "TOP 20001 IdMovimiento" in sql:
            return [{"id": x["idMovimiento"]} for x in state["movs"]]
        raise AssertionError(sql)

    def insert(sql, params):
        if "INSERT INTO dbo.ImportacionesCaja" in sql:
            state["lot"] = {
                "IdLote": 1,
                "Libro": params[0],
                "FechaCorte": params[2],
                "Estado": "Preview",
                "Resoluciones": None,
            }
            return 1
        assert "INSERT INTO dbo.FilasOrigenCaja" in sql
        id = len(state["rows"]) + 1
        names = (
            "IdLote",
            "Hoja",
            "NumeroFila",
            "Huella",
            "DatosOriginales",
            "Estado",
            "IdMovimiento",
            "IdOperacion",
            "Motivo",
        )
        state["rows"].append({"IdFila": id, **dict(zip(names, params, strict=True))})
        return id

    def write(sql, params=()):
        if "UPDATE dbo.FilasOrigenCaja" in sql:
            row = next(x for x in state["rows"] if x["IdFila"] == params[-1])
            row.update(
                Estado=params[0], IdMovimiento=params[1], IdOperacion=params[2], Motivo=params[3]
            )
        elif "UPDATE dbo.ImportacionesCaja" in sql:
            state["lot"].update(Estado=params[0], Resoluciones=params[1])
        else:
            raise AssertionError(sql)
        return 1

    def create(body, key, user):
        state["creadas"] += 1
        id = state["creadas"]
        state["movs"].append(
            {
                "idMovimiento": 100 + id,
                "idOperacion": id,
                "filaPlanilla": None,
                "concepto": "Pago",
                "anulada": False,
            }
        )
        return {"idOperacion": id}, True

    for name, fn in [("one", one), ("read", read), ("insert", insert), ("write", write)]:
        monkeypatch.setattr(db, name, fn)
    monkeypatch.setattr(service, "crear", create)
    monkeypatch.setattr(service, "_bloquear", lambda op: None)
    monkeypatch.setattr(
        service, "previsualizar", lambda op: {"previewVersion": "0" * 64, "advertencias": []}
    )
    return state


def decision(id, distinct=False):
    return {
        "idFila": id,
        "accion": "importar",
        "confirmarDistinto": distinct,
        "motivo": "Dos pagos reales" if distinct else None,
        "operacion": {
            "previewVersion": "0" * 64,
            "operacion": {
                "tipo": "pago",
                "caja": "giamigli-sa",
                "fecha": "2026-10-22",
                "importe": "100",
                "cuenta": "A",
                "concepto": "Pago",
                "idContacto": 17,
                "aplicaciones": [
                    {"tipoDocumento": "CompraDeuda", "idDocumento": 10, "importeAplicado": "100"}
                ],
            },
        },
    }


def test_repetir_archivo_no_duplica_y_pendientes_resolubles(lot):
    content = xlsx([[datetime(2026, 10, 22), "Pago", "White", None, None, None, -100, -100]])
    first = imp.previsualizar(content, "CajasGiamigli", date(2026, 10, 22), "prueba")
    assert first["estado"] == "Preview" and lot["creadas"] == 0
    pending = imp.ConfirmarImportacion(resoluciones=[{"idFila": 1, "accion": "pendiente"}])
    assert imp.confirmar(1, pending, "prueba")["estado"] == "Preview"
    resolved = imp.ConfirmarImportacion(resoluciones=[decision(1)])
    assert imp.confirmar(1, resolved, "prueba")["estado"] == "Confirmado"
    assert imp.confirmar(1, resolved, "prueba")["estado"] == "Confirmado"
    assert (
        imp.previsualizar(content, "CajasGiamigli", date(2026, 10, 22), "prueba")["estado"]
        == "Confirmado"
    )
    assert lot["creadas"] == 1 and len(lot["rows"]) == 1


def test_dos_filas_iguales_requieren_confirmacion_y_fallo_revierte_lote(lot):
    content = xlsx(
        [
            [datetime(2026, 10, 22), "Pago", "White", None, None, None, -100, -100],
            [datetime(2026, 10, 22), "Pago", "White", None, None, None, -100, -200],
        ]
    )
    imp.previsualizar(content, "CajasGiamigli", date(2026, 10, 22), "prueba")
    with pytest.raises(service.ConflictoCaja):
        imp.confirmar(
            1, imp.ConfirmarImportacion(resoluciones=[decision(1), decision(2)]), "prueba"
        )
    assert lot["creadas"] == 0 and not lot["movs"]
    result = imp.confirmar(
        1, imp.ConfirmarImportacion(resoluciones=[decision(1), decision(2, True)]), "prueba"
    )
    assert result["estado"] == "Confirmado" and lot["creadas"] == 2


def test_contrato_multipart_previsualiza_sin_libros(lot, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.features.cajas_efectivo import router

    monkeypatch.setattr(router, "_usuario", lambda request: "prueba")
    app = FastAPI()
    app.include_router(router.router)
    client = TestClient(app)
    content = xlsx([[datetime(2026, 10, 22), "Pago", "White", None, None, None, -100, -100]])
    response = client.post(
        "/api/cajas-efectivo/importaciones/previsualizar",
        data={"libro": "CajasGiamigli", "fechaCorte": "2026-10-22"},
        files={"archivo": ("caja.xlsx", content)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["comparacion"]["giamigli-sa"]["saldoPlanilla"] == "-100.00"
    assert lot["creadas"] == 0
