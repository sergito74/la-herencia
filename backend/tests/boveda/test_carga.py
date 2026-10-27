"""Carga automática en Compras: cierre al centavo, sin tolerancia (042, FR-020)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.features.boveda import carga, repository
from src.features.boveda.conectores import DatosCompra, DocumentoPortal
from src.features.compras import repository as compras

LINEA = {"idRubro": 1, "idCentroCosto": 3}


class Lector:
    tiene_carga_compras = True

    def __init__(self, impreso, lineas=(LINEA,)):
        self.impreso, self.lineas = impreso, list(lineas)

    def leer_comprobante(self, doc, pdf):
        return DatosCompra(cabecera={"idContacto": 9}, lineas=self.lineas, numero="0001-1",
                           total_impreso=Decimal(self.impreso))


DOC = DocumentoPortal(clave="k", fecha=date(2026, 10, 1), tipo="factura", proveedor="P", bajar=lambda: b"")


@pytest.fixture
def entorno(monkeypatch):
    creadas = []
    monkeypatch.setattr(repository, "compra_existente", lambda c, n, r: None)
    monkeypatch.setattr(compras, "calcular_totales", lambda lineas, cab: {"importeTotal": 1000.00})
    monkeypatch.setattr(compras, "create_compra", lambda cab, lin, venc: creadas.append(cab) or 77)
    return creadas


def test_cierra_exacto_carga(entorno):
    r = carga.cargar(Lector("1000.00"), DOC, b"%PDF", "C:/x.pdf")
    assert r["estadoCarga"] == "cargado_auto" and r["idCompra"] == 77
    assert entorno[0]["documentoOriginal"] == "C:/x.pdf"


@pytest.mark.parametrize("impreso", ["1000.01", "999.99", "1000.05"])
def test_un_centavo_de_diferencia_queda_pendiente(entorno, impreso):
    r = carga.cargar(Lector(impreso), DOC, b"%PDF", "C:/x.pdf")
    assert r["estadoCarga"] == "pendiente" and "No cierra al centavo" in r["motivo"]
    assert entorno == []


def test_sin_rubro_queda_pendiente(entorno):
    r = carga.cargar(Lector("1000.00", [{"idRubro": None, "idCentroCosto": 3}]), DOC, b"%PDF", "C:/x.pdf")
    assert r["estadoCarga"] == "pendiente" and "rubro" in r["motivo"]


def test_no_comprobante_no_aplica(entorno):
    resumen = DocumentoPortal(clave="r", fecha=None, tipo="resumen", proveedor="P", bajar=lambda: b"")
    assert carga.cargar(Lector("1"), resumen, b"%PDF", "C:/r.pdf")["estadoCarga"] == "no_aplica"


def test_ya_cargado(entorno, monkeypatch):
    monkeypatch.setattr(repository, "compra_existente", lambda c, n, r: 55)
    r = carga.cargar(Lector("1000.00"), DOC, b"%PDF", "C:/x.pdf")
    assert r["estadoCarga"] == "ya_cargado" and r["idCompra"] == 55 and entorno == []
