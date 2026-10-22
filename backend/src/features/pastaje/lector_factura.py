"""039: lectura de comprobantes emitidos en ARCA (factura / ND / NC, PDF "Comprobante Autorizado").

Devuelve los datos para confirmar; nunca guarda. Los acentos pueden llegar dañados por la
fuente del PDF, por eso los patrones usan '.' en esas letras.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from src.features.descarga_peajes.lectores import texto_pdf

CODIGOS = {"01": ("factura", "A"), "02": ("nota_debito", "A"), "03": ("nota_credito", "A"),
           "06": ("factura", "B"), "07": ("nota_debito", "B"), "08": ("nota_credito", "B")}


class NoReconocido(ValueError):
    pass


def _importe(v: str) -> Decimal:
    return Decimal(v.strip().replace(".", "").replace(",", "."))


def _fecha(v: str) -> str:
    return datetime.strptime(v, "%d/%m/%Y").date().isoformat()


def _m(patron: str, texto: str, que: str, obligatorio: bool = True):
    m = re.search(patron, texto, re.M | re.S)
    if not m and obligatorio:
        raise NoReconocido(f"No se encontró {que} en el PDF.")
    return m


def _detalle(bloque: str) -> str:
    """Quita código de producto y columnas numéricas que pdfplumber intercala en la descripción."""
    t = re.sub(r"\s+", " ", bloque)
    t = re.sub(r"\s[\d.,]+ (?:unidades|otras unidades) [\d.,]+ [\d.,]+ [\d.,]+ [\d.,]+% [\d.,]+", "", t)
    return re.sub(r"^\d{1,6}\s+", "", t).strip()


def leer_texto(texto: str) -> dict:
    cod = _m(r"COD\.\s*(\d\d)", texto, "el código de comprobante").group(1)
    if cod not in CODIGOS:
        raise NoReconocido(f"Código de comprobante {cod} no admitido (solo facturas, ND y NC A/B).")
    tipo, letra = CODIGOS[cod]
    pv = _m(r"Punto de Venta:\s*(\d+)\s*Comp\. Nro:\s*(\d+)", texto, "punto de venta y número")
    cuits = re.findall(r"CUIT:\s*(\d{11})", texto)
    if len(cuits) < 2:
        raise NoReconocido("No se encontraron los CUIT de emisor y cliente.")
    periodo = _m(r"Desde:\s*(\d\d/\d\d/\d{4})\s*Hasta:\s*(\d\d/\d\d/\d{4})", texto, "el período", False)
    vto = _m(r"Vto\. para el pago:\s*(\d\d/\d\d/\d{4})", texto, "el vencimiento", False)
    cliente = _m(r"Raz.n Social:\s*([^\n]+?)\s*\n", texto[texto.find(cuits[1]):], "el cliente", False)
    detalle = _m(r"Subtotal c/IVA\s*\n(?:IVA\s*\n)?(.*?)\nImporte Otros Tributos", texto, "el detalle", False)
    otros = _m(r"Importe Otros Tributos:\s*\$\s*([\d.,]+)", texto, "otros tributos", False)
    iva = _m(r"IVA 21%:\s*\$\s*([\d.,]+)", texto, "el IVA 21%", False)
    return {
        "tipo": tipo, "letra": letra, "codigo": cod,
        "puntoVenta": int(pv.group(1)), "numero": int(pv.group(2)),
        "fecha": _fecha(_m(r"Fecha de Emisi.n:\s*(\d\d/\d\d/\d{4})", texto, "la fecha de emisión").group(1)),
        "vtoPago": _fecha(vto.group(1)) if vto else None,
        "cuitEmisor": cuits[0], "cuitCliente": cuits[1],
        "cliente": cliente.group(1).strip() if cliente else None,
        "periodoDesde": _fecha(periodo.group(1)) if periodo else None,
        "periodoHasta": _fecha(periodo.group(2)) if periodo else None,
        "detalle": _detalle(detalle.group(1)) if detalle else None,
        "neto": _importe(_m(r"Importe Neto Gravado:\s*\$\s*([\d.,]+)", texto, "el neto gravado").group(1)),
        "iva": _importe(iva.group(1)) if iva else Decimal(0),
        "otrosTributos": _importe(otros.group(1)) if otros else Decimal(0),
        "total": _importe(_m(r"Importe Total:\s*\$\s*([\d.,]+)", texto, "el total").group(1)),
        "cae": _m(r"CAE N.:\s*(\d+)", texto, "el CAE").group(1),
        "vtoCae": _fecha(_m(r"Vto\. de CAE:\s*(\d\d/\d\d/\d{4})", texto, "el vencimiento del CAE").group(1)),
    }


def leer_pdf(contenido: bytes) -> dict:
    return leer_texto(texto_pdf(contenido))
