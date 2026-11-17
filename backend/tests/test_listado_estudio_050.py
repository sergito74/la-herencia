"""050 US8 (T042): listado de imputación para el Estudio contable."""

import os
from datetime import datetime

import openpyxl
import pytest

from src.features.imputacion import listado_estudio as L


def _base(**kw):
    b = {"fecha": datetime(2026, 9, 10), "razonSocial": "Proveedor", "tipoDocumento": "Factura", "nroDocumento": "0001-00000001",
         "moneda": "Pesos", "tc": 1, "ajustaTc": False, "cantidad": 200, "producto": "GLIFOSATO 66% X 20 L",
         "centro": "Agricultura", "rubro": "Herbicidas", "destino": "General", "campania": "No Aplica",
         "total": 1_000_000.0, "id": 1, "idCompra": 10, "parteRubro": "Agroquímicos", "parteTamiz": "Agroquímicos",
         "destinoTamiz": None, "esFlete": 0}
    b.update(kw)
    return b


def _fr(cultivo, destino, campania, importe, cantidad):
    return {"id": 1, "idCultivo": cultivo, "idCampania": 1 if cultivo else None, "ganaderia": None, "idCentro": None,
            "idOrden": 5 if cultivo else None, "importe": importe, "cantidad": cantidad, "parte": "Agroquímicos",
            "campania": campania, "destino": destino}


def test_columnas_en_el_orden_actual_mas_las_dos_nuevas():
    assert L.COLUMNAS[:14] == ["Fecha", "Razon Social", "Tipo documento", "Nro Documento", "Moneda", "Tipo de Cambio",
                               "Ajusta Tipo Cambio", "Cantidad", "Producto/Servicio", "Centro de costos", "Rubro",
                               "Destino", "Campaña", "Total"]
    assert L.COLUMNAS[14:] == ["Importe en pesos"]


def test_fuera_de_alcance_una_fila_como_hoy(monkeypatch):
    monkeypatch.setattr(L, "_renglones", lambda: [_base()])
    monkeypatch.setattr(L, "_fracciones", lambda: {})
    filas = L.armar_filas()
    assert len(filas) == 1 and filas[0][11] == "General" and filas[0][13] == 1_000_000.0


def test_glifosato_tres_filas_que_suman_el_total(monkeypatch):
    monkeypatch.setattr(L, "_renglones", lambda: [_base(destinoTamiz="CultivoStock", total=1_000_000.01)])
    monkeypatch.setattr(L, "_fracciones", lambda: {1: [
        _fr(3, "Soja primera", "2026/2027", 200_000, 40), _fr(3, "Soja primera", "2026/2027", 200_000, 40),
        _fr(1, "Maiz", "2026/2027", 350_000, 70), _fr(None, None, None, 250_000, 50)]})
    filas = L.armar_filas()
    assert [(f[11], f[7]) for f in filas] == [("Soja primera", 80), ("Maiz", 70), ("En stock", 50)]
    assert sum(f[13] for f in filas) == 1_000_000.01


def test_dolares_importe_en_pesos_al_tc_del_comprobante():
    fila = L._fila(_base(moneda="Dolares", tc=1000), 10.5, 1, "Agricultura", "Maiz", "2026/2027", "Semilla")
    assert fila[13] == 10.5 and fila[14] == 10500.0


def test_archivo_abierto_da_aviso_y_no_deja_temporales(monkeypatch, tmp_path):
    destino = tmp_path / "listado.xlsx"
    destino.write_bytes(b"anterior")

    def bloqueado(src, dst):
        raise PermissionError("en uso")

    monkeypatch.setattr(L.os, "replace", bloqueado)
    with pytest.raises(L.ListadoAbierto):
        L.escribir([L._fila(_base(), 1.0, 1, "x", "y", "z", "w")], destino)
    assert destino.read_bytes() == b"anterior"
    assert os.listdir(tmp_path) == ["listado.xlsx"]


def test_escribe_hoja_y_formatos(tmp_path):
    destino = tmp_path / "listado.xlsx"
    L.escribir([L._fila(_base(), 1.0, 1, "x", "y", "z", "w")], destino)
    ws = openpyxl.load_workbook(destino).worksheets[0]
    assert ws.title == "Cns_Imputacion_Compras" and ws.freeze_panes == "A2"
    assert ws["A2"].number_format == "d-mmm-yy" and [c.value for c in ws[1]] == L.COLUMNAS


def test_total_en_dolares_con_formato_us(tmp_path):
    destino = tmp_path / "listado.xlsx"
    L.escribir([L._fila(_base(moneda="Dolares", tc=1000), 10.0, 1, "x", "y", "z", "w"),
                L._fila(_base(), 5.0, 1, "x", "y", "z", "w")], destino)
    ws = openpyxl.load_workbook(destino).worksheets[0]
    assert "us$" in ws["N2"].number_format and "us$" not in ws["N3"].number_format and ws.max_column == 15
