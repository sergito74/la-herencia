"""Contrato de /api/integridad-vinculos (031). Fuente y lotes simulados."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.vinculos import cadenas, fuente, lotes
from src.main import app

admin = TestClient(app)
admin.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))
operador = TestClient(app)
operador.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Operador"))


@pytest.fixture(autouse=True)
def datos(monkeypatch):
    raw = {"aplicaciones": [{"idAplicacion": 1, "origenMovimiento": "bna", "idMovimiento": 1, "tipoDocumento": "CompraDeuda",
                             "idDocumento": 10, "importe": 100, "origenCarga": "automatica-exacta"}],
           "lineasCompras": [{"idLinea": 5, "idCompra": 10, "importe": 150}], "lineas": {5: {"idResumen": 1}},
           "tesoreria": [], "backfill": [], "pagosResumen": [], "valores": [], "fechasOtros": {},
           "movimientos": {("bna", 1): {"fecha": date(2026, 1, 5), "importe": -100, "idContacto": 48, "concepto": "X"}},
           "documentos": {("CompraDeuda", 10): {"fecha": datetime(2026, 1, 1), "totalArs": 100, "idContacto": 48, "moneda": "Pesos"}}}
    raw["vinculos"] = cadenas.construir_vinculos(raw)
    monkeypatch.setattr(fuente, "cargar", lambda: raw)


def test_control_devuelve_totales_y_filtra_por_categoria():
    d = admin.get("/api/integridad-vinculos/control").json()
    assert d["totales"]["doble-imputacion"] == 1 and d["totales"]["documento-excedido"] == 1
    solo = admin.get("/api/integridad-vinculos/control", params={"categoria": "doble-imputacion"}).json()
    assert [h["categoria"] for h in solo["hallazgos"]] == ["doble-imputacion"]
    assert solo["hallazgos"][0]["fechaDocumento"] == "2026-01-01"


def test_categoria_invalida_422():
    assert admin.get("/api/integridad-vinculos/control", params={"categoria": "x"}).status_code == 422


def test_escritura_de_lotes_solo_administrador():
    assert operador.post("/api/integridad-vinculos/lotes/1/aplicar").status_code == 403


def test_conflicto_de_estado_409(monkeypatch):
    def conflicto(*a):
        raise lotes.LoteConflicto("Hay reemplazos ambiguos incluidos sin elegir")

    monkeypatch.setattr(lotes, "aplicar", conflicto)
    r = admin.post("/api/integridad-vinculos/lotes/1/aplicar")
    assert r.status_code == 409 and "ambiguos" in r.json()["detail"]
