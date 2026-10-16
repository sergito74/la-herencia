"""037 — Reglas de la carga automática en Compras (sin tocar WC: todo simulado)."""

from __future__ import annotations

from datetime import date

import pytest

from src.features.descarga_peajes import carga, lectores


def _leido(precio=1000.0, total=1210.0) -> lectores.Leido:
    return lectores.Leido("0840-00000001", date(2026, 10, 1),
                          [{"descripcion": "TIGRE PASADAS - CAT 2", "cantidad": 1, "precioUnitario": precio,
                            "iva": 21.0, "unidad": "PASADA"}], total)


@pytest.fixture
def entorno(monkeypatch):
    estado = {"creadas": [], "existente": None, "leido": _leido()}
    monkeypatch.setattr(carga.lectores, "texto_pdf", lambda b: "texto")
    monkeypatch.setattr(carga.lectores, "leer", lambda p, t: estado["leido"])
    monkeypatch.setattr(carga.repository, "compra_existente", lambda c, n, r: estado["existente"])

    def crear(cabecera, lineas, venc):
        estado["creadas"].append((cabecera, lineas))
        return 999
    monkeypatch.setattr(carga.compras, "create_compra", crear)
    return estado


def test_cierra_crea_compra_con_clasificacion_de_peajes(entorno):
    r = carga.cargar("AutopistasDelSol", 276, b"%PDF", r"C:\x\20261001_AutopistasDelSol.pdf")
    assert r["estadoCarga"] == "cargado_auto" and r["idCompra"] == 999
    cabecera, lineas = entorno["creadas"][0]
    assert cabecera["idContacto"] == 276 and cabecera["tipo"] == "A" and cabecera["moneda"] == "Pesos"
    assert cabecera["documentoOriginal"].endswith("20261001_AutopistasDelSol.pdf")
    assert lineas[0]["idRubro"] == 2047893477 and lineas[0]["idCentroCosto"] == 3
    assert lineas[0]["idDestino"] == 1 and lineas[0]["campaña"] == "No Aplica"


def test_duplicado_no_crea(entorno):
    entorno["existente"] = 555
    r = carga.cargar("AutopistasDelSol", 276, b"%PDF", "r.pdf")
    assert r["estadoCarga"] == "ya_cargado" and r["idCompra"] == 555 and not entorno["creadas"]


def test_no_cierra_queda_pendiente(entorno):
    entorno["leido"] = _leido(total=1300.0)
    r = carga.cargar("AutopistasDelSol", 276, b"%PDF", "r.pdf")
    assert r["estadoCarga"] == "pendiente" and "No cierra" in r["motivo"] and not entorno["creadas"]


def test_redondeo_del_proveedor_dentro_de_tolerancia(entorno):
    entorno["leido"] = _leido(total=1210.04)
    assert carga.cargar("AutopistasDelSol", 276, b"%PDF", "r.pdf")["estadoCarga"] == "cargado_auto"


def test_sin_proveedor_asignado_queda_pendiente(entorno):
    r = carga.cargar("Telepeaje", None, b"%PDF", "r.pdf")
    assert r["estadoCarga"] == "pendiente" and "proveedor" in r["motivo"] and not entorno["creadas"]


def test_formato_no_reconocido_queda_pendiente(entorno, monkeypatch):
    def falla(p, t):
        raise lectores.NoReconocido("sin total")
    monkeypatch.setattr(carga.lectores, "leer", falla)
    r = carga.cargar("AUSA", 380, b"%PDF", "r.pdf")
    assert r["estadoCarga"] == "pendiente" and r["motivo"].startswith("Formato no reconocido")


def test_simulacion_no_crea(entorno):
    r = carga.cargar("AutopistasDelSol", 276, b"%PDF", "r.pdf", simular=True)
    assert r["estadoCarga"] == "cargado_auto" and r["idCompra"] is None and not entorno["creadas"]
