"""Tests del informe de imputación por documento comercial (017, pedido del
usuario 2026-09-25)."""

from __future__ import annotations

from src.features.imputacion import exportacion, repository


def _linea(id_detalle, fracciones=None):
    return {
        "idDetalleCompra": id_detalle,
        "producto": "Producto de prueba",
        "cantidad": 10.0,
        "unidad": "LTS",
        "precioUnitario": 5.0,
        "campaniaManual": "2025/2026",
        "centroCostoManual": "Agricultura",
        "rubroManual": "Herbicidas",
        "fracciones": fracciones or [],
    }


def test_informe_documentos_xlsx_genera_filas_agrupadas(monkeypatch):
    documentos = [
        {
            "idCompra": 1,
            "fecha": "2026-01-01",
            "idContacto": 10,
            "proveedor": "Proveedor S.A.",
            "tipoDocumento": "Factura",
            "numeroDocumento": "0001-00000001",
            "moneda": "Pesos",
        }
    ]
    lineas = [
        _linea(
            100,
            fracciones=[
                {"cultivo": "Trigo", "campania": "2025/2026", "centroCosto": None, "esGanaderia": False, "importe": 123.45, "estado": "Aprobada"},
                {"cultivo": None, "campania": None, "centroCosto": None, "esGanaderia": None, "importe": 50.0, "estado": "Aprobada"},
            ],
        )
    ]
    monkeypatch.setattr(repository, "listar_documentos_con_imputacion", lambda *a, **k: (documentos, 1))
    monkeypatch.setattr(repository, "lineas_con_imputacion", lambda idc: lineas)

    contenido = exportacion.informe_documentos_xlsx(None, None, None)

    assert contenido[:2] == b"PK"  # firma de un .xlsx (zip) válido
    assert len(contenido) > 0


def test_etiqueta_destino_prioriza_cultivo_luego_centro_luego_stock():
    assert exportacion._etiqueta_destino({"cultivo": "Maiz", "campania": "2026/2027"}) == "Maiz / 2026/2027"
    assert exportacion._etiqueta_destino({"cultivo": None, "centroCosto": "Adm. General"}) == "Adm. General"
    assert exportacion._etiqueta_destino({"cultivo": None, "centroCosto": None, "esGanaderia": True}) == "Ganadería"
    assert exportacion._etiqueta_destino({"cultivo": None, "centroCosto": None, "esGanaderia": None}) == "En stock sin consumir"
