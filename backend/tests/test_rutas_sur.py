from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.features.contactos import repository as contactos
from src.features.descarga_peajes import lectores
from src.features.descarga_peajes.carga import armar_compra
from src.features.compras.repository import calcular_totales
from src.features.documentos_nuevos.lectores import lector_para
from src.features.boveda.conectores import DocumentoPortal


@pytest.mark.parametrize("archivo,numero,fecha,total", [
    ("20261028_Corresur.pdf", "0002-01210978", date(2026, 10, 28), 1548.82),
    ("20261028_Corresur 001.pdf", "0002-01348415", date(2026, 10, 29), 1787.10),
])
def test_facturas_reales_por_ambas_vias(archivo, numero, fecha, total):
    ruta = Path.home() / "Dropbox/Giamigli de Bolivar SA/Compras/04 2026 - 03 2027" / archivo
    if not ruta.exists():
        pytest.skip("PDF local no disponible")
    pdf = ruta.read_bytes()
    texto = lectores.texto_pdf(pdf)
    for nombre in ("Corresur", "Rutas Sur Atlantico S.A."):
        leido = lectores.leer(nombre, texto)
        assert (leido.numero, leido.fecha, leido.total_impreso) == (numero, fecha, total)
        cab, lineas = armar_compra(leido, 2657, str(ruta))
        assert round(calcular_totales(lineas, cab)["importeTotal"], 2) == total
    lector = lector_para("factura", 2657)
    doc = DocumentoPortal("prueba", fecha, "factura", "Rutas Sur Atlantico S.A.", lambda: pdf, id_contacto=2657)
    resultado = lector.leer_comprobante(doc, pdf)
    assert resultado.total_impreso == Decimal(str(total))
    assert resultado.cabecera["idContacto"] == 2657
    for adulterado in (texto.replace("30-71945419-0", "30-11111111-1"),
                       texto.replace("$268.80", "$268.81").replace("$310.16", "$310.17"),
                       texto.replace("$1,548.82", "$1,548.83").replace("$1,787.10", "$1,787.11")):
        with pytest.raises(lectores.NoReconocido):
            lectores.leer("Rutas Sur Atlantico S.A.", adulterado)


@pytest.mark.parametrize("nombre,cuit", [("Corresur", None), ("Rutas Sur Atlántico S. A.", None),
                                         ("Otro nombre", "30-71945419-0")])
def test_no_permite_alta_duplicada(monkeypatch, nombre, cuit):
    monkeypatch.setattr(contactos, "fetch_all", lambda *a: [
        {"id": 2657, "nombre": "Rutas Sur Atlantico S.A.", "cuit": "30719454190"}])
    monkeypatch.setattr(contactos, "execute_insert_returning_id", lambda *a: pytest.fail("No debe insertar"))
    with pytest.raises(ValueError, match="Ya existe"):
        contactos.create_contacto.__wrapped__(nombre, "Proveedor", cuit, False)


def test_edicion_propia_y_cuit_vacio(monkeypatch):
    monkeypatch.setattr(contactos, "fetch_all", lambda *a: [
        {"id": 2657, "nombre": "Rutas Sur Atlantico S.A.", "cuit": "30719454190"},
        {"id": 1, "nombre": "Sin CUIT", "cuit": None}])
    contactos._exigir_identidad_unica("Rutas Sur Atlantico S.A.", "30719454190", 2657)
    contactos._exigir_identidad_unica("Proveedor diferente", None)
    with pytest.raises(ValueError):
        contactos._exigir_identidad_unica("Otro", "30 71945419 0", 1)
