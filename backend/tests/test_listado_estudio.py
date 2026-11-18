from src.features.tesoreria import listado_estudio as L


def test_impuestos_e_inversiones_se_reconocen():
    assert L._BANCARIO.search("Imp. Deb. Ley 25413 Gral.") and L._BANCARIO.search("GRAVAMEN LEY 25413 S/DEB")
    assert L._INVERSION.search("Rescate Fima") and L._INVERSION.search("DEB.P.FIJO CANAL ELECT.")
    assert not L._BANCARIO.search("Trf Inmed Proveed")


def test_texto_de_documento():
    docs = {5: {"td": "Factura", "nro": "0001-00000123", "prov": "Bayá Casal"}}
    assert L._texto_doc({"tipo": "CompraDeuda", "doc": 5, "imp": 10}, docs) == "Factura 0001-00000123 (Bayá Casal)"
    assert L._texto_doc({"tipo": "Sueldo", "doc": "Octubre 2026", "imp": 10}, {}) == "Sueldo Octubre 2026"
