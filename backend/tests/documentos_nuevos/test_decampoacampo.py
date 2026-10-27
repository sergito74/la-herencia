"""De Campo a Campo (043, T029): solo operaciones de Giamigli; nada de Ganadera San Justo ni de terceros."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.features.boveda.conectores import decampoacampo as d

GIAMIGLI = {"cuit": "30712114602", "razon_social": "Giamigli De Bolivar Sa"}
SAN_JUSTO = {"cuit": "30715943278", "razon_social": "Ganadera San Justo Sociedad Si"}


def _op(id_, vendedora, compradora=None, **k):
    return {"id": id_, "sociedad_vendedora": vendedora, "sociedad_compradora": compradora or {"cuit": "30717335356"},
            "datos_liquidacion": {"numero_factura": "11-82156", "importe_total": 4594059.600000001},
            "condiciones_pactadas": {"fecha_vendida": "2026-05-29 13:15:10"},
            "liquidacion_vendedor": [{"url": f"https://s3/liq{id_}.pdf", "fecha_actualizacion": "2026-06-02 10:00:00"}],
            "nota_debito_vendedor": [{"url": f"https://s3/nd{id_}.pdf"}], **k}


def test_solo_ventas_de_giamigli():
    respuestas = [{"data": [_op(1, SAN_JUSTO), _op(2, GIAMIGLI), _op(3, {"cuit": "30-71594327-8"})]},
                  {"data": [_op(2, GIAMIGLI)]}]  # la misma operación en dos pestañas
    assert [o["id"] for o in d.operaciones_giamigli(respuestas, "venta")] == [2]


def test_compras_filtran_por_sociedad_compradora():
    respuestas = [{"data": [_op(4, SAN_JUSTO, compradora=GIAMIGLI), _op(5, GIAMIGLI, compradora=SAN_JUSTO)]}]
    assert [o["id"] for o in d.operaciones_giamigli(respuestas, "compra")] == [4]


def test_respuestas_sin_lista_no_fallan():
    assert d.operaciones_giamigli([{"data": {"venta": {}}}, {}], "venta") == []


def test_documentos_de_la_operacion():
    docs = d.documentos_de_operacion(_op(2, GIAMIGLI), "venta")
    liq, nd = docs
    assert (liq["tipo"], liq["numero"], liq["total"], liq["fecha"]) == (
        "liquidacion", "11-82156", Decimal("4594059.60"), date(2026, 6, 2))
    # La nota de débito es un ajuste de la liquidación: va a Ventas como liquidación.
    assert nd["tipo"] == "liquidacion" and nd["fecha"] == date(2026, 5, 29) and nd["numero"] is None
    assert nd["clave"] == "decampoacampo:venta:2:nota_debito:0"
    assert liq["clave"] == "decampoacampo:venta:2:liquidacion:0"


def test_nunca_usa_acciones_del_portal():
    import inspect

    fuente = inspect.getsource(d).lower()
    for accion in ("programar pago", "ofertar", "cotizar"):
        assert f"click(\"{accion}" not in fuente and f"name=\"{accion}" not in fuente
    assert "/san justo/" not in fuente and "/giamigli/i" in fuente  # el selector solo elige Giamigli


def test_pdf_de_san_justo_no_se_guarda(monkeypatch):
    import pytest

    from src.features.boveda.conectores import DocumentoPortal
    from src.features.documentos_nuevos import clasificador

    monkeypatch.setattr(clasificador, "texto_pdf", lambda pdf, paginas=1: "Sujeto Retenido GANADERA SAN JUSTO CUIT 30-71594327-8")
    doc = DocumentoPortal(clave="y", fecha=None, tipo="certificado", proveedor="D", bajar=lambda: b"")
    with pytest.raises(d.OtraSociedad):
        d._completar(doc, b"%PDF")


def test_completa_numero_y_fecha_desde_el_pdf():
    from src.features.boveda.conectores import DocumentoPortal

    nd = DocumentoPortal(clave="x", fecha=None, tipo="liquidacion", proveedor="D", bajar=lambda: b"")
    d.completar_desde_texto(nd, "A | 0011-00085270 | Ajuste Financiero Débito 22/07/2026")
    assert nd.numero == "0011-00085270"
    cert = DocumentoPortal(clave="y", fecha=None, tipo="certificado", proveedor="D", bajar=lambda: b"")
    d.completar_desde_texto(cert, "Fecha: 27/02/2023 Base Imponible: 2.068.900,77 | Número: 0000- 2023- 0000000000001928 Alí")
    assert cert.fecha == date(2023, 2, 27) and cert.numero == "0000-2023-0000000000001928"
