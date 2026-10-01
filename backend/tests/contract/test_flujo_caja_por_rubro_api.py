"""Contrato de `/api/flujo-caja/por-rubro` (030): estructura, internos fuera
del neto operativo, saldos y FR-006 (el detalle de cada celda suma lo mismo
que la celda). Movimientos simulados; no toca WC."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.auth.tokens import crear_token
from src.features.vinculos import cadenas, fuente
from src.features.flujo_caja import atribucion, repository
from src.main import app

client = TestClient(app)
client.cookies.set("la_herencia_session", crear_token(id_usuario=0, rol="Administrador"))

RANGO = {"fechaDesde": "2026-01-01", "fechaHasta": "2026-02-28"}


def mov(banco, dia, importe, id_mov, concepto="", interno=False, tipo=None, contacto=None):
    return {"fecha": datetime(2026, *dia), "banco": banco, "origenMovimiento": banco.lower() if banco == "Galicia" else "bna",
            "idMovimientoOrigen": id_mov, "numeroCuentaBancaria": "x", "importe": importe, "concepto": concepto,
            "idContacto": contacto, "contacto": None, "esInterno": interno, "tipoInterno": tipo}


@pytest.fixture(autouse=True)
def datos(monkeypatch):
    movimientos = [
        mov("Galicia", (1, 10), 1000.0, 1, contacto=5),
        mov("Galicia", (1, 20), -300.0, 2, contacto=6),
        mov("BNA", (2, 3), -123.45, 3, concepto="IMPUESTO LEY 25413"),
        mov("Galicia", (2, 5), -200.0, 4, interno=True, tipo="Colocación FIMA"),
        mov("BNA", (2, 7), -50.0, 5, concepto="TRANSF MIS TIT 30712114602", interno=True, tipo="Traspaso entre bancos"),
        mov("Galicia", (2, 8), 50.0, 6),
    ]
    monkeypatch.setattr(repository, "get_movimientos_normalizados", lambda d, h: [dict(m) for m in movimientos])
    monkeypatch.setattr(atribucion, "construir_indice_ingresos", lambda d, h: {})
    monkeypatch.setattr(atribucion, "_rubro_de_venta", lambda t, i: "Venta Soja")
    monkeypatch.setattr(atribucion, "atribuir_egreso", lambda *a: {"rubro": atribucion.SIN_RUBRO, "centroCosto": None})
    monkeypatch.setattr(fuente, "cargar", lambda: {"vinculos": []})
    monkeypatch.setattr(cadenas, "documentos_de_movimiento",
                        lambda v: {("galicia", 1): [{"tipoDocumento": "VentaGranos", "idDocumentoAplicado": 1, "importeAplicado": 600.0}]})
    monkeypatch.setattr(repository, "saldos_por_cuenta_al",
                        lambda f: {"Nación": 100.0, "Galicia CC": 1000.0, "Galicia Fondo FIMA": 0.0})


def test_estructura_y_reparto():
    r = client.get("/api/flujo-caja/por-rubro", params=RANGO)
    assert r.status_code == 200
    d = r.json()
    assert d["periodos"] == ["2026-01", "2026-02"]
    ingresos = {f["rubro"]: f["total"] for f in d["ingresos"]["rubros"]}
    assert ingresos == {"Venta Soja": 600.0, "Pendiente de aplicar": 400.0}
    assert [c["cuenta"] for c in d["saldoInicial"]["cuentas"]] == ["Nación", "Galicia CC", "Galicia Fondo FIMA"]
    assert d["saldoInicial"]["cuentas"][2]["aclaracion"]


def test_internos_fuera_del_neto_y_traspaso_emparejado():
    d = client.get("/api/flujo-caja/por-rubro", params=RANGO).json()
    internos = {f["rubro"]: f["total"] for f in d["internos"]["rubros"]}
    assert internos == {"Colocación FIMA": -200.0, "Rescate FIMA": 0.0, "Traspaso entre bancos": 0.0}
    assert d["netoOperativoPorPeriodo"] == {"2026-01": 700.0, "2026-02": -123.45}
    assert d["traspasosSinContraparte"] == []


def test_saldo_final_por_cuenta_y_total():
    d = client.get("/api/flujo-caja/por-rubro", params=RANGO).json()
    assert d["saldoFinalPorCuenta"]["Galicia Fondo FIMA"]["2026-02"] == 200.0
    assert d["saldoFinalPorPeriodo"]["2026-02"] == round(1100.0 + 700.0 - 123.45, 2)


def test_cada_celda_suma_igual_que_su_detalle():
    d = client.get("/api/flujo-caja/por-rubro", params=RANGO).json()
    celdas = [("ingresos", None, f) for f in d["ingresos"]["rubros"]]
    celdas += [("egresos", g["centroCosto"], f) for g in d["egresos"]["centrosCosto"] for f in g["rubros"]]
    celdas += [("internos", None, f) for f in d["internos"]["rubros"]]
    for seccion, centro, fila in celdas:
        for periodo, valor in fila["valores"].items():
            if not valor:
                continue
            params = {**RANGO, "periodo": periodo, "seccion": seccion, "rubro": fila["rubro"]}
            if centro:
                params["centroCosto"] = centro
            det = client.get("/api/flujo-caja/por-rubro/detalle", params=params).json()
            assert det["total"] == valor, (seccion, fila["rubro"], periodo)


def test_periodo_invalido_devuelve_422():
    r = client.get("/api/flujo-caja/por-rubro/detalle", params={**RANGO, "periodo": "2027-01", "seccion": "ingresos", "rubro": "x"})
    assert r.status_code == 422


def test_exportar_devuelve_xlsx():
    r = client.get("/api/flujo-caja/por-rubro/exportar", params=RANGO)
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/vnd.openxmlformats")
