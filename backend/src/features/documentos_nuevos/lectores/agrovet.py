"""Lector de facturas de Agrovet Integral SRL (contacto 5), sistema Dragonfish (043).

Una línea por artículo con cantidad y precio unitario impresos (si hay descuento, el precio sale del monto).
La imputación de cada artículo es la última que se le dio a mano en Agrovet; si el artículo nunca se cargó,
va a Productos Veterinarios / Ganadería, como la mayoría de las compras a Agrovet (queda en la revisión).
Solo lee facturas con una única alícuota de IVA; percepciones de IVA o IIBB van a la cabecera.
"""

from __future__ import annotations

import io
import re
from datetime import date
from decimal import Decimal

from src.db.connection import fetch_one
from src.features.boveda.conectores import DatosCompra, DocumentoPortal
from src.features.boveda.conectores.chrome_comun import _cabecera

ID_CONTACTO = 5
RUBRO_DEFECTO = 2047893453  # Productos Veterinarios
CENTRO_DEFECTO = 2  # Ganadería
_NUMERO = re.compile(r"AGROVET INTEGRAL SRL\s+([ABC])\s+(FACTURA|NOTA DE CR[EÉ]DITO|NOTA DE D[EÉ]BITO)\s+N\S*\s*(\d{4})\s*-\s*(\d{8})")
_FECHA = re.compile(r"FECHA:\s*(\d{2})/(\d{2})/(\d{2})")
_RENGLON = re.compile(r"^(\d{4}) (.+?) (-?[\d,]+\.\d{2}) ([\d,]+\.\d{2})(?: [\d.,%\s]+?)? (-?[\d,]+\.\d{2})$", re.M)
# Columnas Impuesto / % / Base / Monto, impresas con espacios entre dígitos: se juntan y se separan por miles.
_IMPUESTO = re.compile(r"(I\.V\.A\.|PERC[^\d\n]*|I\.?I\.?B\.?B[^\d\n]*)([\d ,.]+)$", re.M)
_COLUMNAS = re.compile(r"^(\d{1,2}\.\d{2})(\d{1,3}(?:,\d{3})*\.\d{2})(\d{1,3}(?:,\d{3})*\.\d{2})$")


def _num(t: str) -> Decimal:
    return Decimal(t.replace(" ", "").replace(",", ""))


def _texto(pdf: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf)) as d:
        return "\n".join(p.extract_text() or "" for p in d.pages)


def _imputacion(producto: str) -> tuple[int, int, int, str]:
    fila = fetch_one(
        "SELECT TOP 1 dc.IdRubro AS r, dc.IdCentroCostos AS c, dc.IdDestino AS d, dc.Campaña AS k "
        "FROM dbo.Det_Compras dc JOIN dbo.Compras c ON c.IdDeuda = dc.IdCompra "
        "WHERE c.IdContacto = ? AND dc.[Producto/Servicio] = ? AND dc.IdRubro IS NOT NULL "
        "ORDER BY c.Fecha DESC, dc.IdDetalleCompra DESC", (ID_CONTACTO, producto[:50]))
    if fila:
        return fila["r"], fila["c"] or CENTRO_DEFECTO, fila["d"] or 1, fila["k"] or "No Aplica"
    return RUBRO_DEFECTO, CENTRO_DEFECTO, 1, "No Aplica"


class LectorAgrovet:
    codigo = "agrovet"
    nombre = "Agrovet"
    tiene_estado_cuenta = False
    tiene_carga_compras = True
    mapeo_proveedores: dict = {}

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes) -> DatosCompra | None:
        t = _texto(pdf)
        m, f = _NUMERO.search(t), _FECHA.search(t)
        total = re.search(r"^TOTAL \$\s*([\d, ]+\.[\d ]+)$", t, re.M)
        if not (m and f and total) or not m.group(2).startswith("FACTURA"):
            return None
        numero = f"{m.group(3)}-{m.group(4)}"
        fecha = date(2000 + int(f.group(3)), int(f.group(2)), int(f.group(1)))
        ivas, percepcion_iva, iibb = set(), Decimal(0), Decimal(0)
        for imp in _IMPUESTO.finditer(t):
            cols = _COLUMNAS.match(imp.group(2).replace(" ", ""))
            if cols is None:
                return None
            nombre, alicuota, monto = imp.group(1), _num(cols.group(1)), _num(cols.group(3))
            if nombre.startswith("I.V.A."):
                ivas.add(alicuota)
            elif "IVA" in nombre or "I.V.A" in nombre:
                percepcion_iva += monto
            else:
                iibb += monto
        if len(ivas) != 1:
            return None  # varias alícuotas: no se sabe cuál va en cada renglón
        iva = float(ivas.pop())
        lineas = []
        for r in _RENGLON.finditer(t):
            producto, cantidad, monto = r.group(2).strip(), _num(r.group(3)), _num(r.group(5))
            if not cantidad:
                return None
            rubro, centro, destino, campania = _imputacion(producto)
            lineas.append({"productoServicio": producto[:50], "cantidad": float(cantidad),
                           "precioUnitario": float((monto / cantidad).quantize(Decimal("0.0001"))), "iva": iva,
                           "unidad": "UNIDAD", "idCentroCosto": centro, "idDestino": destino, "idRubro": rubro,
                           "campaña": campania, "ajusteFinanciero": False})
        cabecera = _cabecera(ID_CONTACTO, fecha, numero, percepcionIva=percepcion_iva, ingresosBrutos=iibb)
        return DatosCompra(cabecera=cabecera, lineas=lineas, numero=numero, total_impreso=_num(total.group(1)))
