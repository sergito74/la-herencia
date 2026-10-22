"""039: lectura del comprobante ARCA emitido (texto del PDF real 20261006_Giamigli.pdf)."""

from decimal import Decimal as D
from pathlib import Path

import pytest

from src.features.pastaje import service
from src.features.pastaje.lector_factura import NoReconocido, leer_texto

TEXTO = (Path(__file__).parent / "fixtures" / "factura_arca_20261006.txt").read_text(encoding="utf-8")


def test_lee_la_factura_real_exacta():
    f = leer_texto(TEXTO)
    assert (f["tipo"], f["letra"], f["puntoVenta"], f["numero"]) == ("factura", "A", 2, 8)
    assert (f["fecha"], f["vtoPago"], f["vtoCae"]) == ("2026-10-06", "2026-10-06", "2026-10-16")
    assert (f["cuitEmisor"], f["cuitCliente"], f["cae"]) == ("30712114602", "30715943278", "86406417014230")
    assert (f["neto"], f["iva"], f["total"]) == (D("290851.40"), D("61078.79"), D("351930.19"))
    assert f["detalle"] == "Servicio de pastaje de 70 Vaquillonas del 25 al 30 de septiembre de 2026"


def test_nota_de_credito_por_codigo():
    f = leer_texto(TEXTO.replace("COD. 01", "COD. 03"))
    assert f["tipo"] == "nota_credito"


def test_emisor_ajeno_genera_advertencia(monkeypatch):
    from src.features.pastaje import lector_factura

    monkeypatch.setattr(lector_factura, "texto_pdf", lambda b: TEXTO.replace("CUIT: 30712114602", "CUIT: 20111111112"))
    assert service.leer_comprobante(b"")["advertencias"]


def test_pdf_no_reconocido():
    with pytest.raises(NoReconocido):
        leer_texto("un texto cualquiera")
