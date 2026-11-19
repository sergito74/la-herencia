from datetime import date

from src.features.tesoreria import excel_import as e


def test_encabezado_bna_acepta_monto_o_importe():
    assert e._es_encabezado_bna(["Fecha", "Comprobante", "Concepto", "Monto", "Saldo"])
    assert e._es_encabezado_bna(["Fecha", "Comprobante", "Concepto", "Importe", "Saldo"])
    assert not e._es_encabezado_bna(["Fecha", "Descripción", "Débitos", "Créditos", "Saldo"])


def test_fecha_como_texto():
    assert e._xldate_to_date("11/11/2026", 0) == date(2026, 11, 11)
