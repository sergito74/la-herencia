"""Pruebas de `archivos.py` — 036 (T043). Carpetas temporales: nunca la real de Dropbox."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from src.features.revision_cuentas import archivos

TEXTO_FACTURA = "Asiento 0 A 0009-00077393\n23/09/2025\nFACTURA\nGIAMIGLI DE BOLIVAR S.A.\nTOTAL 30017,03"
PDF_SANO = b"\r\n%PDF-1.4\n1 0 obj\n<<>>\nendobj\n"


@pytest.fixture
def carpetas(tmp_path):
    """Un período con un `.crdownload` legible, uno ilegible, un archivo vacío, un PDF sano, un PDF dañado, una imagen y un archivo ajeno."""
    p = tmp_path / "04 2025 - 03 2026"
    p.mkdir()
    (p / "20250923_JaureguiYMorales.crdownload").write_bytes(b"%PDF-contenido-legible")
    (p / "20251113_JaureguiYMorales.crdownload").write_bytes(b"basura")
    (p / "20251212_JaureguiYMorales.crdownload").write_bytes(b"")
    (p / "20251229_JaureguiYMorales.pdf").write_bytes(PDF_SANO)
    (p / "20260105_Proveedor.pdf").write_bytes(b"no soy un pdf")
    (p / "20250103_JaureguiYMorales.jpg").write_bytes(b"\xff\xd8\xff")
    (p / "planilla.xlsx").write_bytes(b"x")
    (tmp_path / "otros").mkdir()
    return tmp_path


def _texto(ruta: Path):
    return TEXTO_FACTURA if ruta.name.startswith("20250923") else None


def _sin_cargar():
    return {}, []


def _estados(base: Path, **kw) -> dict[str, str]:
    r = archivos.revisar(base=base, cargadas=kw.pop("cargadas", _sin_cargar), texto_pdf=_texto, **kw)
    return {Path(a["ruta"]).name: a["estado"] for a in r["archivos"]}


def test_cada_archivo_se_clasifica_por_su_estado(carpetas):
    assert _estados(carpetas) == {
        "20250923_JaureguiYMorales.crdownload": "comprobante-legible-extension-incorrecta",
        "20251113_JaureguiYMorales.crdownload": "no-legible",
        "20251212_JaureguiYMorales.crdownload": "vacio",
        "20260105_Proveedor.pdf": "no-legible",
        "20250103_JaureguiYMorales.jpg": "imagen-revisar",
    }          # el PDF sano y el archivo ajeno no se informan


def test_el_comprobante_legible_trae_numero_importe_proveedor_y_fecha(carpetas):
    r = archivos.revisar(base=carpetas, cargadas=_sin_cargar, texto_pdf=_texto, estado="comprobante-legible-extension-incorrecta")
    (a,) = r["archivos"]
    assert a["numero"] == "0009-00077393" and a["importe"] == 30017.03
    assert a["proveedor"] == "JaureguiYMorales" and a["fecha"] == date(2025, 9, 23) and a["periodo"] == "04 2025 - 03 2026"


def test_cargado_es_verdadero_si_el_numero_existe_en_compras_sin_importar_los_ceros(carpetas):
    # la compra se cargó con el punto de venta de 5 dígitos
    r = archivos.revisar(base=carpetas, texto_pdf=_texto, estado="comprobante-legible-extension-incorrecta", cargadas=lambda: ({"900077393": 2143522625}, []))
    (a,) = r["archivos"]
    assert a["cargado"] is True and a["idCompra"] == 2143522625
    sin = archivos.revisar(base=carpetas, texto_pdf=_texto, estado="comprobante-legible-extension-incorrecta", cargadas=_sin_cargar)["archivos"][0]
    assert sin["cargado"] is False and sin["idCompra"] is None


def test_cargado_tambien_se_reconoce_por_el_nombre_del_archivo_en_el_documento_original(carpetas):
    documentos = [("..\\compras\\04 2025 - 03 2026\\20251212_jaureguiymorales.crdownload#", 77)]
    r = archivos.revisar(base=carpetas, texto_pdf=_texto, estado="vacio", cargadas=lambda: ({}, documentos))
    (a,) = r["archivos"]
    assert a["cargado"] is True and a["idCompra"] == 77


def test_la_revision_no_modifica_renombra_ni_borra_ningun_archivo(carpetas):
    def foto():
        return {str(p.relative_to(carpetas)): (p.stat().st_size, p.stat().st_mtime_ns) for p in carpetas.rglob("*")}

    antes = foto()
    archivos.revisar(base=carpetas, cargadas=_sin_cargar, texto_pdf=_texto)
    archivos.revisar(base=carpetas, periodo="04 2025 - 03 2026", cargadas=_sin_cargar, texto_pdf=_texto)
    assert foto() == antes


def test_el_periodo_elige_una_carpeta_y_solo_acepta_el_formato_fiscal(carpetas):
    assert len(archivos.revisar(base=carpetas, periodo="04 2025 - 03 2026", cargadas=_sin_cargar, texto_pdf=_texto)["archivos"]) == 5
    assert archivos.revisar(base=carpetas, periodo="04 2024 - 03 2025", cargadas=_sin_cargar, texto_pdf=_texto)["archivos"] == []
    for malo in ("..", "../otros", "04 2025 - 03 2027", "2025", "04 2025 - 03 2026/../x"):
        with pytest.raises(ValueError):
            archivos.revisar(base=carpetas, periodo=malo, cargadas=_sin_cargar, texto_pdf=_texto)


def test_un_estado_desconocido_se_rechaza(carpetas):
    with pytest.raises(ValueError):
        archivos.revisar(base=carpetas, estado="inventado", cargadas=_sin_cargar, texto_pdf=_texto)


def test_la_lista_se_pagina(carpetas):
    p1 = archivos.revisar(base=carpetas, cargadas=_sin_cargar, texto_pdf=_texto, pagina=1, tamano=2)
    p2 = archivos.revisar(base=carpetas, cargadas=_sin_cargar, texto_pdf=_texto, pagina=2, tamano=2)
    assert p1["total"] == 5 and len(p1["archivos"]) == 2 and len(p2["archivos"]) == 2
    assert not {a["ruta"] for a in p1["archivos"]} & {a["ruta"] for a in p2["archivos"]}


def test_una_raiz_que_no_existe_devuelve_una_lista_vacia(tmp_path):
    r = archivos.revisar(base=tmp_path / "no-existe", cargadas=_sin_cargar)
    assert r["total"] == 0 and r["archivos"] == []


def test_datos_del_nombre_y_numero_normalizado():
    assert archivos.datos_del_nombre("20260726_JaureguiYMorales 002.pdf") == (date(2026, 7, 26), "JaureguiYMorales")
    assert archivos.datos_del_nombre("20250923_Proveedor.pdf.crdownload") == (date(2025, 9, 23), "Proveedor")
    assert archivos.datos_del_nombre("sin-fecha.pdf")[0] is None
    assert archivos.normalizar_numero("0009-00077393") == archivos.normalizar_numero("00009-00077393") == "900077393"
    assert archivos.normalizar_numero(None) is None


def test_la_raiz_sale_del_backend_no_del_cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("COMPRAS_RAIZ", str(tmp_path))
    assert archivos.raiz() == tmp_path
    monkeypatch.delenv("COMPRAS_RAIZ")
    assert archivos.raiz().name == "Compras"
