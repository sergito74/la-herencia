"""Pruebas unitarias de la subrutina de verificación de carpetas locales (043)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.features.documentos_nuevos import carpetas


def test_ejercicios_a_revisar():
    ejs = carpetas.ejercicios_a_revisar()
    assert len(ejs) == 2
    assert "04 2026 - 03 2027" in ejs
    assert "04 2025 - 03 2026" in ejs


def test_archivo_ya_conocido_se_ignora(tmp_path):
    f = tmp_path / "factura.pdf"
    f.write_bytes(b"%PDF-1.4...")
    conocidos = {"factura.pdf"}
    assert carpetas.procesar_archivo_carpeta(1, f, conocidos) is None


def test_archivo_sin_ser_comprobante_se_ignora(tmp_path, monkeypatch):
    f = tmp_path / "lista_precios.pdf"
    f.write_bytes(b"%PDF-1.4...")
    monkeypatch.setattr(carpetas.repository, "existente", lambda sha: None)
    monkeypatch.setattr(carpetas.clasificador, "texto_pdf", lambda contenido: "Lista de Precios 2026")
    assert carpetas.procesar_archivo_carpeta(1, f, set()) is None
