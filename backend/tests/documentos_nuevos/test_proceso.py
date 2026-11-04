"""Proceso común de documentos nuevos (03/11/2026): varias facturas en un PDF, escaneos sin texto."""

from __future__ import annotations

from pathlib import Path

from src.features.documentos_nuevos import carpetas, proceso
from src.features.documentos_nuevos.clasificador import Clasificacion


def test_numero_rotulado_de_factura_sancor():
    assert proceso._numero_rotulado("ORIGINAL\nB FACTURA N°: 00038 - 00229895\nCódigo") == "00038-00229895"
    assert proceso._numero_rotulado("RUTAS SUR FA 0002-01348415 28/10/2026") is None


def test_textos_de_un_archivo_no_pdf_es_un_bloque():
    bloques = proceso.textos_de("factura.xml", b"<xml>FACTURA</xml>")
    assert len(bloques) == 1 and bloques[0].indice == 0


def test_escaneo_queda_sin_clasificar_con_motivo():
    c = proceso.escaneo(None, None)
    assert c.comprobante and c.tipo == "otro" and c.modulo == "sin_clasificar"
    assert c.motivo == proceso.MOTIVO_ESCANEO


def test_carpeta_registra_un_escaneo_sin_texto(monkeypatch, tmp_path: Path):
    archivo = tmp_path / "20261031_Coto.pdf"
    archivo.write_bytes(b"%PDF-1.4 escaneo")
    docs = []
    monkeypatch.setattr(carpetas.repository, "existente", lambda *a: None)
    monkeypatch.setattr(proceso, "textos_de", lambda n, c: [proceso.Bloque("", "sha")])
    monkeypatch.setattr(proceso.repository, "registrar_documento", lambda d: docs.append(d))
    assert carpetas.procesar_archivo_carpeta(None, archivo, set()) == "para_cargar"
    assert docs[0]["modulo"] == "sin_clasificar" and docs[0]["motivo"] == proceso.MOTIVO_ESCANEO


def test_carpeta_registra_cada_factura_de_un_pdf_con_varias(monkeypatch, tmp_path: Path):
    archivo = tmp_path / "20261016_SancorSeguros.pdf"
    archivo.write_bytes(b"%PDF-1.4 tres facturas")
    docs = []
    monkeypatch.setattr(carpetas.repository, "existente", lambda *a: None)
    monkeypatch.setattr(carpetas.repository, "mismo_comprobante", lambda *a: False)
    monkeypatch.setattr(proceso, "textos_de", lambda n, c: [proceso.Bloque(f"F{i}", f"sha{i}", i) for i in range(3)])
    monkeypatch.setattr(proceso, "clasificar", lambda t, r: Clasificacion(True, tipo="factura", modulo="compras",
                                                                          id_contacto=171, numero=t))
    monkeypatch.setattr(proceso, "resolver", lambda c, t, b, r: ("ya_estaba", None, {"F0": 1, "F1": 2, "F2": 3}[t]))
    monkeypatch.setattr(proceso.repository, "registrar_documento", lambda d: docs.append(d))
    carpetas.procesar_archivo_carpeta(None, archivo, set())
    assert [(d["numero"], d["sha256"], d["idRegistro"]) for d in docs] == [("F0", "sha0", 1), ("F1", "sha1", 2),
                                                                          ("F2", "sha2", 3)]
