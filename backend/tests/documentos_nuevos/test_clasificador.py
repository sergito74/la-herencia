"""Clasificador de comprobantes de mail (043, T019): tipo, emisor, receptor, módulo y carpeta."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.features.documentos_nuevos import clasificador as c

FACTURA = """FACTURA A  Nro 0003-00012345
Movistar  CUIT 30-67881435-7  Fecha de emisión 15/10/2026
Cliente: GIAMIGLI DE BOLIVAR SA  CUIT 30-71211460-2
Total a Pagar $12.345,67  CAE 7612345"""


def _contacto(cuit):
    return {"30678814357": (71, "Movistar")}.get(cuit)


def test_factura_de_proveedor_conocido():
    r = c.clasificar(FACTURA, _contacto)
    assert (r.comprobante, r.tipo, r.modulo) == (True, "factura", "compras")
    assert (r.id_contacto, r.numero, r.fecha) == (71, "0003-00012345", date(2026, 10, 15))
    assert r.total == Decimal("12345.67") and r.para_giamigli and r.motivo is None


def test_emisor_nuevo_queda_para_cargar_a_mano():
    r = c.clasificar(FACTURA, lambda cuit: None)
    assert r.id_contacto is None and r.motivo.startswith("Emisor nuevo")


@pytest.mark.parametrize("texto", ["PRESUPUESTO N° 45 válido 10 días", "Catálogo de productos 2026", "Newsletter"])
def test_no_comprobante_se_ignora(texto):
    assert not c.clasificar(texto, _contacto).comprobante


def test_sucesion_es_giamigli():
    texto = FACTURA.replace("GIAMIGLI DE BOLIVAR SA  CUIT 30-71211460-2", "SUCESION GIAMBERARDINI CUIT 20-12345678-3")
    assert c.clasificar(texto, _contacto).para_giamigli


def test_san_justo_se_ignora():
    texto = FACTURA.replace("GIAMIGLI DE BOLIVAR SA  CUIT 30-71211460-2", "GANADERA SAN JUSTO CUIT 30-71594327-8")
    assert not c.clasificar(texto, _contacto).para_giamigli


def test_modulos_por_tipo():
    assert c.clasificar("CERTIFICADO DE RETENCION Ganancias", None).modulo == "impuestos"
    assert c.clasificar("LIQUIDACION PRIMARIA DE GRANOS N 3301", None).modulo == "ventas"
    assert c.clasificar("CONTRATO DE COMPRAVENTA de soja", None).modulo == "ventas"
    assert c.clasificar("RESUMEN DE CUENTA al 30/09/2026 Agrovet", None).modulo == "cuentas_corrientes"


def test_resumen_tarjeta_galicia_por_contenido():
    r = c.clasificar("Banco Galicia RESUMEN VISA Business cierre 25/09/2026", None)
    assert (r.tipo, r.modulo, r.banco, r.producto) == ("resumen_tarjeta", "tesoreria", "Galicia", "Tarjetas\\Visa")
    carpeta, nombre = c.carpeta_y_nombre(r, "resumen.pdf")
    assert carpeta == c.BANCOS / "Galicia" / "Tarjetas" / "Visa" / "2026" and nombre == "2026 09.pdf"


def test_extracto_banco_nombre_no_descriptivo():
    r = c.clasificar("BANCO DE LA NACION ARGENTINA EXTRACTO DE CUENTA 01/09/2026 SALDO ANTERIOR SALDO ACTUAL", None)
    carpeta, nombre = c.carpeta_y_nombre(r, "doc.pdf")
    assert carpeta == c.BANCOS / "BNA" / "Extractos" / "2026" and nombre == "Extracto 2026 09.pdf"


def test_carpeta_de_compras_del_ejercicio():
    r = c.clasificar(FACTURA, _contacto)
    carpeta, nombre = c.carpeta_y_nombre(r, "fc.pdf")
    assert carpeta.parent == c.COMPRAS and nombre == "20261015_Movistar.pdf"


def test_boleta_de_patente_y_ticket():
    assert c.tipo_de("Impuesto a los Automotores Vencimiento 09/10/2026 A pagar Patente N AG964SV") == "boleta"
    assert c.tipo_de("Ticket - Jauregui y Morales N 00009-00113618") == "factura"


def test_numerado_sin_leyenda_queda_sin_clasificar():
    r = c.clasificar("N 0011 - 00000144 ERNESTO HERNANDEZ CUIT 20-08614788-3", None)
    assert (r.comprobante, r.tipo, r.modulo) == (True, "otro", "sin_clasificar")


def test_starlink_a_nombre_de_sergio_es_de_giamigli():
    texto = FACTURA.replace("GIAMIGLI DE BOLIVAR SA  CUIT 30-71211460-2", "GIAMBERARDINI SERGIO GABRIEL CUIT:23238598109")
    r = c.clasificar(texto, _contacto)
    assert r.para_giamigli and r.motivo is None


def test_sin_clasificar_avisa_pendiente_de_procesamiento():
    r = c.clasificar("N 0011 - 00000144 ERNESTO HERNANDEZ CUIT 20-08614788-3", None)
    assert r.motivo.startswith("Documento pendiente de procesamiento")


def test_lector_visa_galicia_lee_y_cierra():
    from src.features.documentos_nuevos.lectores import visa_galicia as v

    texto = """Banco Galicia GIAMIGLI DE BOLIVAR SA Resumen Nº VI00000000007822346
01-Sep-26 25-Sep-26 01-Oct-26 13-Oct-26
27-08-26 * MERPAGO*PINTESPANA 123456 404.306,00
02-09-26 K Starlink 07/12 654321 65.000,00
IMPUESTO DE SELLOS $ 1.000,00
TOTAL A PAGAR 470.306,00"""
    r = v.leer(texto)
    assert r["codigo"] == "VI00000000007822346" and len(r["lineas"]) == 2
    assert r["lineas"][1]["cuota"] == "07/12" and v.contacto_de(r["lineas"][1]["detalle"]) == 567
    assert v.total_calculado(r) == r["totalPagar"]


def test_san_justo_bloqueado_aunque_nombre_a_giamigli():
    texto = FACTURA.replace("Cliente: GIAMIGLI DE BOLIVAR SA  CUIT 30-71211460-2",
                            "Cliente: GANADERA SAN JUSTO CUIT 30-71594327-8 (adm. por Giamigli)")
    assert not c.clasificar(texto, _contacto).para_giamigli


def test_visa_personal_no_es_de_la_empresa():
    from src.features.documentos_nuevos.lectores import visa_galicia as v

    assert not v.es_visa_galicia("Banco Galicia Resumen Nº VI0000001 Titular PEREZ JUAN")
    assert v.es_visa_galicia("Banco Galicia Resumen Nº VI0000001 GIAMIGLI DE BOLIVAR SA")
