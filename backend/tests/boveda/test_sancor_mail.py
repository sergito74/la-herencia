from decimal import Decimal

from src.features.boveda.conectores import DocumentoPortal
from src.features.boveda.conectores import sancor

FACTURA = """ORIGINAL
B FACTURA N°: {pv} - {nro}
Sancor Cooperativa de Seguros Limitada 16/10/2026
Ramo/Producto Póliza N° Referencia N° Endoso N° Vigencia
{ramo}/21 {poliza} 2409457 396 02/11/2026 02/12/2026
Conceptos Gravados Conceptos no Gravados Conceptos exentos IVA (Alicuota 21,00%) IVA sujeto no cat. Impuestos y Tasas
35.780,26 0,00 0,00 7.513,86 0,00 393,58
IVA Percepción IIBB Percepción Sellado Provincial Percepción Tasa Premio Aum. de Capital
0,00 0,00 0,00 0,00 43.687,70 3.559,53
Total $47.247,23
"""


def test_pdf_con_una_factura_por_poliza_y_factura_b_iva_incluido(monkeypatch):
    texto = FACTURA.format(pv="00038", nro="00229895", ramo="600", poliza="13500137") + \
        FACTURA.format(pv="00041", nro="00206614", ramo="2500", poliza="2315661")
    assert len(sancor.facturas_del_pdf(texto)) == 2
    monkeypatch.setattr("src.features.boveda.conectores.chrome_comun._texto", lambda pdf: texto)
    leido = sancor.ConectorSancor().leer_comprobante(
        DocumentoPortal(clave="mail:x#1", fecha=None, tipo="factura", proveedor="Sancor", bajar=None), b"")
    assert leido.numero == "00041-00206614"
    assert [(l["productoServicio"], l["precioUnitario"], l["iva"]) for l in leido.lineas] == [
        ("Salud pol. 2315661 - B IVA incluido", 43294.12, 0.0), ("Aumento de capital", 3559.53, 0.0)]
    assert float(leido.cabecera["conceptosNoGravados"]) == 393.58 and leido.total_impreso == Decimal("47247.23")
