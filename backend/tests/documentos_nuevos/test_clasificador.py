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


def test_recibo_con_facturas_en_detalle_y_numero_espaciado():
    from src.features.documentos_nuevos import clasificador as c
    texto = "Recibo de Ingreso Casa Central\nNúmero: 0006 00074242\nFecha: 15/04/2026\nCUIT: 30-60741325-4\nGIAMIGLI CUIT 30-71211460-2\nFactura cancelada\nTotal Pesos Recibidos: 15.833.029,55\nTotal : 15.833.029,55"
    r=c.clasificar(texto,lambda _: (7,'Proveedor'))
    assert r.tipo=='recibo' and r.modulo=='pagos'
    assert r.numero=='0006-00074242' and str(r.total)=='15833029.55'
    carpeta,_=c.carpeta_y_nombre(r,'recibo.pdf')
    assert c.PAGOS in carpeta.parents


def test_cupon_de_pago_no_es_recibo():
    texto = ("I.V.A. RESPONSABLE INSCRIPTO CASA CENTRAL CUPÓN DE PAGO\nC.U.I.T. 30-50004946-0\nACCIDENTES PERSONALES\n"
             "TOTAL $ 52.075,92\nRECIBO 608099084\nTOMADOR\nMIRANDA IRMA DELIA")
    assert c.tipo_de(texto) is None


def test_comprobante_de_tesoreria_es_recibo():
    texto = ("Comprobante Tesoreria Casa C\nNúmero: 0006 00147232\nENRIQUE M. BAYA CASAL S.A. Tranferencia E/ Cuentas Ctes\n"
             "NC 0020 00135455 Nota de Crédito s/Fc. 451182 25/06/26 26/06/26 6.832.052,00")
    assert c.tipo_de(texto) == "recibo"


def test_cupon_con_leyenda_factura_no_es_comprobante():
    assert c.tipo_de("VIDA COLECTIVO CUPÓN PARA EL INTERMEDIARIO I.V.A. RESPONSABLE INSCRIPTO FACTURA\nRECIBO 1") is None


def test_numero_con_ceros_distintos_es_la_misma_compra():
    from src.features.boveda.repository import _clave_numero
    assert _clave_numero("2-02554911") == _clave_numero("00002-02554911") == (2, 2554911)
    assert _clave_numero("0020- 00136689") == (20, 136689) and _clave_numero("PENDIENTE 59111") is None


def test_boleta_de_arba_sin_cuit_se_asigna_a_arba():
    buscar = lambda cuit: (12, "ARBA") if cuit == c.ARBA else None
    patente = "Impuesto a los Automotores Arba Vencimiento: 15/07/2025 CUOTA 3/2025 Patente N° AG964SV A pagar: $ 540.413,20"
    inmobiliario = "Impuesto Inmobiliario Vencimiento 18/12/2025 Cuota 4 de 2025 A pagar Partida N° 011-007957-5 $1.437.586,60"
    assert c.clasificar(patente, buscar).id_contacto == 12
    assert c.clasificar(inmobiliario, buscar).id_contacto == 12
