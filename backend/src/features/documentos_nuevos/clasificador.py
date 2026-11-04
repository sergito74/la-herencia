"""Clasificador de comprobantes que llegan por mail (043, research R3 y Clarifications).

Decide, por el texto del PDF: si es un comprobante (lo demás se ignora sin
guardarse), su tipo, el emisor (CUIT → `Contactos`, nunca se crean contactos),
si va dirigido a Giamigli (o a la Sucesión, etapa previa de Giamigli), el
módulo del aviso y la carpeta donde se guarda. Las funciones de decisión
reciben texto, así se prueban sin PDFs ni base.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from src.features.descarga_peajes.portales import COMPRAS, carpeta_ejercicio

GIAMIGLI = "30712114602"
# Comprobantes a nombre de Sergio que son gastos de Giamigli (ej. Starlink mensual): se cargan normalmente (27/10/2026).
SERGIO = "23238598109"
# Ganadera San Justo: no se registra ni se guarda nada suyo (Sergio, 27/10/2026), aunque nombre a Giamigli.
SAN_JUSTO = "30715943278"
DROPBOX = COMPRAS.parent
BANCOS = DROPBOX / "Bancos"
IMPUESTOS = DROPBOX / "Impuestos"
VENTAS = DROPBOX / "Ventas"
PAGOS = DROPBOX / "Pagos"
DOCUMENTOS = Path.home() / "Documents" / "La Herencia"
RESUMENES_PROVEEDORES = DOCUMENTOS / "Administracion y gestion" / "Resumenes de Cuenta"
CONTRATOS = DOCUMENTOS / "Agricultura" / "Contratos"

CAE_RE = r"\bCAEA?\b|C\.A\.E\.(?:A\.?)?"
_NC = r"NOTA\s+(?:DE\s+)?CR[EÉ]DITO|\bNC\s+(?:[ABC]\b|AUTOM[AÁ]TICA|ELECTR[OÓ]NICA)"
_ND = r"NOTA\s+(?:DE\s+)?D[EÉ]BITO|\bND\s+[ABC]\b"
_SUCESION = re.compile(r"\bSUCESI[OÓ]N\b")
_CUIT = re.compile(r"\b(\d{2})[- .]?(\d{8})[- .]?(\d)\b")
_FECHA = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")


@dataclass
class Clasificacion:
    comprobante: bool
    tipo: str | None = None
    modulo: str = "sin_clasificar"
    cuit_emisor: str | None = None
    id_contacto: int | None = None
    contacto: str | None = None
    para_giamigli: bool = True
    fecha: date | None = None
    numero: str | None = None
    total: Decimal | None = None
    motivo: str | None = None
    banco: str | None = None
    producto: str | None = None
    extras: dict = field(default_factory=dict)


def texto_pdf(pdf: bytes, paginas: int = 3) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        textos = [(p.extract_text() or "") for p in doc.pages]
    texto = "\n".join(textos[:paginas])
    # Pólizas (Allianz granizo, San Cristóbal): la factura viene en una hoja interior (la 2, la 9 o la 16) y las
    # primeras hojas son condiciones. Si el comienzo no es un comprobante, se usa la hoja con la factura (03/11/2026).
    if len(textos) > 1 and tipo_de(texto) in (None, "otro"):
        for t in textos:
            if re.search(r"\bFACTURA", t, re.I) and re.search(CAE_RE, t.upper()) and tipo_de(t) in ("factura", "nota_credito", "nota_debito"):
                return t
    return texto


def cuits(texto: str) -> list[str]:
    vistos: list[str] = []
    for a, b, c in _CUIT.findall(texto):
        cuit = f"{a}{b}{c}"
        if a in ("20", "23", "24", "27", "30", "33", "34") and cuit not in vistos:
            vistos.append(cuit)
    return vistos


def _importe(s: str) -> Decimal:
    """Acepta 1.234,56 y 1,234.56 (Cooperativa Eléctrica): el separador decimal es el último de los dos."""
    if "," in s and "." in s and s.rfind(".") > s.rfind(","):
        return Decimal(s.replace(",", ""))
    if "," not in s and re.search(r"\.\d{2}$", s):
        return Decimal(s)
    return Decimal(s.replace(".", "").replace(",", "."))


def tipo_de(texto: str) -> str | None:
    """Tipo de comprobante, o `None` si no es un comprobante (presupuesto, catálogo, informe, publicidad…)."""
    t = texto.upper()
    # Comprobante de tesorería del proveedor (Bayá Casal): aplica pagos, retenciones y NC en su cuenta corriente.
    # Nombra facturas y NC en el detalle pero no es deuda: va a Pagos como recibo (046, 30/10).
    if re.search(r"COMPROBANTE TESORER[IÍ]A", t) and \
            re.search(r"APLICACI[OÓ]N CUENTA CORRIENTE|TRANS?FERENCIA E/ ?CUENTAS", t):
        return "recibo"
    # Resumen de cuenta de Telepeaje S.A.: es su factura (se carga en Compras), no un resumen de banco (30/10/2026).
    if re.search(r"TELEPEAJE S\.?A", t) and re.search(r"RESUMEN DE CUENTA", t):
        return "factura"
    # Cupón de pago (Sancor): aviso de vencimiento, no comprobante (046). Va antes que "otro" y que el receptor.
    if re.search(r"CUP[OÓ]N (DE PAGO|PARA EL)", t) and not re.search(CAE_RE, t):
        return None
    # Expensas de consorcio: nunca boleta de impuesto (03/11/2026, docs 109/110); se avisa sin clasificar.
    if re.search(r"\bEXPENSAS\b|\bCONSORCIO\b", t) and not re.search(CAE_RE, t):
        return "otro"
    # Tasa municipal: "Comprobante de pago" o "TASA … VENCIMIENTO" (Municipalidad de Bolívar).
    if re.search(r"MUNICIPALIDAD DE", t) and re.search(r"\bTASA\b", t) and \
            re.search(r"COMPROBANTE DE PAGO|VENCIMIENTO", t) and not re.search(CAE_RE, t):
        return "boleta"
    # El detalle de un recibo nombra facturas/NC canceladas: no cambia su encabezado.
    if re.search(r"^\s*(?:ORIGINAL\s+)?RECIBO(?:\s+DE\s+(?:INGRESO|PAGO|COBRANZA)|\s+(?:N[ÚU]MERO|N[°º]))", t, re.M):
        return "recibo"
    if re.search(r"\bPRESUPUESTO\b|\bCOTIZACI[OÓ]N\b|\bCAT[AÁ]LOGO\b|\bLISTA DE PRECIOS\b", t) and \
            not re.search(r"\bFACTURA|\bCAEA?\b|C\.A\.E\.", t):
        return None
    if re.search(r"CONTRATO DE (COMPRA ?VENTA|COMPRAVENTA)|CARTA DE FIJACI[OÓ]N|\bFIJACI[OÓ]N\b.*\bCONTRATO\b", t):
        return "contrato"
    if re.search(r"CERTIFICADO DE RETENCI[OÓ]N|CONSTANCIA DE RETENCI[OÓ]N", t):
        return "retencion"
    if re.search(r"LIQUIDACI[OÓ]N PRIMARIA DE GRANOS|LIQUIDACI[OÓ]N (DE )?HACIENDA|LIQUIDACI[OÓ]N DE VENTA|"
                 r"CUENTA DE VENTA\b|SOBRE LIQ(UIDACI[OÓ]N)?\.? DE VENTA|\bLPG\b", t):
        return "liquidacion"
    # Ficha / resumen de cuenta corriente de un proveedor (ej. extranet de Lartirigoyen): su detalle nombra NC, ND,
    # facturas y recibos ajenos, pero no es un comprobante a cargar en Compras (03/11/2026).
    if re.search(r"FICHA DE CUENTA CORRIENTE", t) or (
            re.search(r"SALDO FINAL|SALDO VENCIDO|SALDO A VENCER", t) and not re.search(CAE_RE, t)):
        return "resumen_proveedor"
    # Una factura numerada con CAE es factura aunque traiga "saldo anterior" o "estado de cuenta" (Movistar, AUSOL).
    numerada = re.search(CAE_RE, t) and numero_de(texto)
    if numerada and re.search(_NC, t):
        return "nota_credito"
    if numerada and re.search(_ND, t):
        return "nota_debito"
    if numerada and re.search(r"\bFACTURA", t):
        return "factura"
    if re.search(r"RESUMEN DE (CUENTA )?TARJETA|RESUMEN (VISA|MASTERCARD|AMERICAN EXPRESS)|\bAGRONACI[OÓ]N\b.*RESUMEN", t):
        return "resumen_tarjeta"
    if re.search(r"EXTRACTO (DE CUENTA|BANCARIO)|RESUMEN DE CUENTA CORRIENTE|RESUMEN DE CAJA DE AHORRO|"
                 r"SALDO ANTERIOR.*SALDO (ACTUAL|FINAL)", t, re.S) and re.search(r"\bBANCO\b|GALICIA", t):
        return "resumen_banco"
    if re.search(r"RESUMEN DE CUENTA|ESTADO DE CUENTA|COMPOSICI[OÓ]N DE SALDO", t):
        return "resumen_proveedor"
    # Póliza / endoso de aseguradora (Allianz, San Cristóbal): sin CAE, la factura es el cuadro de Prima/Premio.
    # Se carga como factura (o NC si el premio es negativo) con número = póliza + endoso (03/11/2026).
    if re.search(r"P[OÓ]LIZA", t) and re.search(r"\bPREMIO\b", t) and re.search(r"\bPRIMA\b|PREMIO\s+USD", t):
        return "nota_credito" if re.search(r"PREMIO\s*\.*\s*-\s*\d", t) else "factura"
    # NC/ND sin CAE: la leyenda suele venir del detalle de otro documento (fichas, resúmenes); no se carga sola en
    # Compras, queda "sin clasificar" para revisar a mano (03/11/2026).
    if re.search(_NC + "|" + _ND, t):
        return "otro"
    if re.search(r"\bBOLETA\b|VOLANTE ELECTR[OÓ]NICO DE PAGO|\bVEP\b|FORMULARIO DE PAGO", t) or \
            (re.search(r"\bIMPUESTO\b|\bTASA\b|\bPATENTE\b", t) and re.search(r"\bVENCIMIENTO\b", t)
             and re.search(r"A PAGAR", t)):
        return "boleta"
    # Cupón de pago (Sancor): aviso de vencimiento, no comprobante; la deuda llega en las facturas mensuales (046, 30/10).
    if re.search(r"CUP[OÓ]N (DE PAGO|PARA EL)", t) and not re.search(CAE_RE, t):
        return None
    if re.search(r"\bRECIBO\b", t) and not re.search(r"\bFACTURA\b", t):
        return "recibo"
    # Liquidación mensual del banco (comisiones) y tickets de estaciones de servicio se cargan como facturas.
    if re.search(r"\bFACTURA\b|LIQUIDACI[OÓ]N ELECTR[OÓ]NICA|LIQUIDACI[OÓ]N DE SERVICIOS P[UÚ]BLICOS|\bTICKET\b", t):
        return "factura"
    # Numerado y con un CUIT de emisor, pero sin leyenda reconocible (ej. factura manual escaneada): se guarda
    # "sin clasificar" para que no se pierda.
    if numero_de(texto) and [c for c in cuits(texto) if c != GIAMIGLI]:
        return "otro"
    return None


MODULO = {
    "factura": "compras", "nota_credito": "compras", "nota_debito": "compras", "recibo": "pagos",
    "boleta": "impuestos", "retencion": "impuestos", "liquidacion": "ventas", "contrato": "ventas",
    "resumen_banco": "tesoreria", "resumen_tarjeta": "tesoreria", "resumen_proveedor": "cuentas_corrientes",
    "otro": "sin_clasificar",
}


def es_de_san_justo(texto: str) -> bool:
    return SAN_JUSTO in cuits(texto) or "GANADERA SAN JUSTO" in texto.upper()


def receptor(texto: str, cuit_emisor: str | None) -> str:
    """`giamigli` (Giamigli, la Sucesión —etapa previa de Giamigli— o sin receptor visible), `persona` (a nombre
    de otra persona: se avisa para confirmar) u `otra` (otra sociedad, ej. Ganadera San Justo: no se registra ni
    se guarda). Lo que está a nombre de Sergio es gasto de Giamigli y se carga normalmente."""
    t = texto.upper()
    if es_de_san_justo(texto):
        return "otra"
    otros = [c for c in cuits(texto) if c != cuit_emisor]
    if GIAMIGLI in otros or SERGIO in otros or "GIAMIGLI" in t or _SUCESION.search(t) or not otros:
        return "giamigli"
    return "persona" if any(c[:2] in ("20", "23", "24", "27") for c in otros) else "otra"


def dirigido_a_la_empresa(texto: str) -> bool:
    """Filtro de mails: el documento debe identificar a Giamigli, a la Sucesión o el CUIT de Sergio (sus gastos de
    Giamigli). Un mail personal sin esa identificación no entra, aunque parezca comprobante (Sergio, 02/11/2026)."""
    t = texto.upper()
    return "GIAMIGLI" in t or bool(_SUCESION.search(t)) or bool({GIAMIGLI, SERGIO} & set(cuits(texto)))


def banco_y_producto(texto: str) -> tuple[str | None, str | None]:
    t = texto.upper()
    banco = "Galicia" if "GALICIA" in t else "BNA" if re.search(r"BANCO DE LA NACI[OÓ]N|\bBNA\b|AGRONACI", t) \
        else "Mercado Libre" if "MERCADO" in t else None
    if banco == "Mercado Libre":
        return banco, "Resumenes"
    if "AGRONACI" in t:
        return banco, "AgroNacion"
    if "MASTERCARD" in t:
        return banco, "Mastercard" if banco == "BNA" else "Tarjetas\\Mastercard"
    if "VISA" in t:
        return banco, "Tarjetas\\Visa"
    if "PLAZO FIJO" in t:
        return banco, "Plazos Fijos"
    if re.search(r"FONDO COM[UÚ]N|INVERSI[OÓ]N", t):
        return banco, "Inversiones"
    if re.search(r"PR[EÉ]STAMO", t):
        return banco, "Prestamos"
    return banco, "Extractos"


def fecha_de(texto: str) -> date | None:
    """Fecha de emisión rotulada si está (no el vencimiento, 03/11/2026); si no, la primera fecha del texto."""
    r = re.search(r"Fecha(?: de)?(?: Emisi[oó]n)?\s*:?\s*(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})\b", texto, re.I)
    if r:
        anio = int(r.group(3)) + (2000 if len(r.group(3)) == 2 else 0)
        try:
            f = date(anio, int(r.group(2)), int(r.group(1)))
            if 2000 <= f.year <= date.today().year + 1:
                return f
        except ValueError:
            pass
    for d, m, a in _FECHA.findall(texto):
        try:
            f = date(int(a), int(m), int(d))
        except ValueError:
            continue
        if 2000 <= f.year <= date.today().year + 1:
            return f
    return None


def fecha_mas_reciente(texto: str) -> date | None:
    """En los resúmenes la fecha que manda es el cierre: la más reciente del texto (sin pasar el mes próximo)."""
    limite = date.today().replace(day=1) + timedelta(days=62)
    fechas = []
    for d, m, a in _FECHA.findall(texto):
        try:
            f = date(int(a), int(m), int(d))
        except ValueError:
            continue
        if 2000 <= f.year and f <= limite:
            fechas.append(f)
    for d, m, a in re.findall(r"\b(\d{2})-(Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)-(\d{2})\b", texto):
        f = date(2000 + int(a), _MESES.index(m) + 1, int(d))
        if f <= limite:
            fechas.append(f)
    return max(fechas) if fechas else None


_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def numero_poliza(texto: str) -> str | None:
    """Número con que se cargan las pólizas: 'póliza endoso' (endoso 0 se omite); San Cristóbal sin guiones."""
    m = re.search(r"N[uú]mero de P[oó]liza\s*:?\s*(\d{6,})", texto, re.I)
    if m:
        e = re.search(r"(?:Endoso N[uú]mero|N[uú]mero de Endoso)\s*:?\s*(\d+)", texto, re.I)
        return m.group(1) + (f" {int(e.group(1))}" if e and int(e.group(1)) else "")
    m = re.search(r"\b(\d{2}-\d{2}-\d{2}-\d{8})\b", texto)  # San Cristóbal: 01-05-14-30002027
    return m.group(1).replace("-", "") if m else None


def numero_de(texto: str) -> str | None:
    """Primero el número rotulado del encabezado (el detalle cita comprobantes ajenos, 03/11/2026); acepta 8 o 9
    dígitos (Telepeaje 0002-381237292)."""
    m = re.search(r"(?:Comprobante|N[°º]|N[uú]mero|Nro\.?)\s*:?\s*(?:[A-C]\s*-?\s*)?(\d{4,5})\s*-\s*(\d{8,9})\b",
                  texto, re.I)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"(?:\b|(?<=[ABCM]))(\d{4,5})\s*-\s*(\d{8,9})\b", texto)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"Punto de Venta:?\s*(\d{1,5}).{0,20}?(?:Comp\.?|Comprobante)\s*N[rº°o]*\.?:?\s*(\d{8})", texto, re.I)
    return f"{int(m.group(1)):05d}-{m.group(2)}" if m else None


_MONTO = r"\$?\s*(\d{1,3}(?:\.\d{3})+,\d{2}|\d{1,3}(?:,\d{3})+\.\d{2}|\d+,\d{2})(?![\d%])(?!\s*%)"


def total_de(texto: str) -> Decimal | None:
    """Total impreso: primero las leyendas explícitas; si no, el último renglón que empieza con TOTAL
    (nunca SUBTOTAL ni una alícuota)."""
    for patron in (r"TOTAL A PAGAR", r"IMPORTE TOTAL", r"TOTAL FACTURA(?: ACTUAL)?", r"\bPREMIO\b\s*\.*"):
        m = re.search(patron + r":?\s*(?:\(\$\))?\s*" + _MONTO, texto, re.I)
        if m:
            return _importe(m.group(1))
    ultimos = re.findall(r"^\s*TOTAL:?\s*" + _MONTO, texto, re.I | re.M)
    return _importe(ultimos[-1]) if ultimos else None


ARBA = "30710404611"


def clasificar(texto: str, buscar_contacto=None) -> Clasificacion:
    """`buscar_contacto(cuit) -> (idContacto, razón social) | None` (inyectable para las pruebas)."""
    tipo = tipo_de(texto)
    if tipo is None:
        return Clasificacion(comprobante=False)
    emisores = [c for c in cuits(texto) if c not in (GIAMIGLI, SERGIO)]
    cuit = emisores[0] if emisores else None
    c = Clasificacion(comprobante=True, tipo=tipo, modulo=MODULO[tipo], cuit_emisor=cuit, fecha=fecha_de(texto),
                      numero=numero_de(texto), total=total_de(texto))
    if not c.numero and re.search(r"P[OÓ]LIZA", texto, re.I) and re.search(r"\bPREMIO\b", texto, re.I):
        c.numero = numero_poliza(texto)
    if tipo == 'recibo':
        n = re.search(r'(?:N[ÚU]MERO|RECIBO\s*N[°ºO.]*)\s*:?\s*(\d{4,5})[ -]+(\d{6,8})', texto, re.I)
        if n:
            c.numero = f'{n.group(1)}-{n.group(2)}'
        # Total cancelado puede incluir retenciones; no confundirlo con fondos recibidos.
        totales = re.findall(r'^\s*TOTAL\s*:\s*'+_MONTO, texto, re.I | re.M)
        if totales:
            c.total = _importe(totales[-1])
    destinatario = receptor(texto, cuit)
    c.para_giamigli = destinatario != "otra"
    if destinatario == "persona":
        c.motivo = "Está a nombre de una persona: confirmar si es un gasto de Giamigli"
    if tipo in ("resumen_banco", "resumen_tarjeta"):
        from src.features.documentos_nuevos.lectores import visa_galicia

        visa = visa_galicia.leer(texto) if visa_galicia.es_visa_galicia(texto) else None
        c.fecha = visa["cierre"].date() if visa else (fecha_mas_reciente(texto) or c.fecha)
        c.banco, c.producto = banco_y_producto(texto)
        if not c.banco:
            c.modulo, c.motivo = "sin_clasificar", "No se reconoce el banco del resumen"
        return c
    if buscar_contacto and cuit:
        encontrado = buscar_contacto(cuit)
        if encontrado:
            c.id_contacto, c.contacto = encontrado
    por_nombre = getattr(buscar_contacto, "por_nombre", None)
    if not c.id_contacto and por_nombre:  # contactos sin CUIT cargado
        # En resúmenes y documentos sin clasificar el detalle nombra a terceros (ficha de Lartirigoyen → "Tarjeta
        # Agronacion", 03/11/2026): el nombre se busca solo en el encabezado.
        encontrado = por_nombre(texto if tipo not in ("resumen_proveedor", "otro") else "\n".join(texto.splitlines()[:8]))
        if encontrado:
            c.id_contacto, c.contacto = encontrado
    # Boletas de ARBA (patentes, inmobiliario): el PDF no trae el CUIT de ARBA y "ARBA" es corto para buscar por nombre.
    if not c.id_contacto and buscar_contacto and tipo == "boleta" and re.search(r"\bARBA\b|IMPUESTO A LOS AUTOMOTORES|IMPUESTO INMOBILIARIO", texto, re.I):
        encontrado = buscar_contacto(ARBA)
        if encontrado:
            c.id_contacto, c.contacto = encontrado
    if tipo == "otro":
        c.motivo = "Documento pendiente de procesamiento: indicar a qué módulo va"
    elif not c.id_contacto:
        c.motivo = "Emisor nuevo: darlo de alta en Contactos y cargar a mano"
    return c


def _seguro(nombre: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", nombre).strip() or "Sin nombre"


def carpeta_y_nombre(c: Clasificacion, nombre_original: str) -> tuple[Path, str]:
    """Carpeta y nombre de archivo según el tipo (Clarifications de la spec)."""
    fecha = c.fecha or date.today()
    contacto = _seguro(c.contacto or Path(nombre_original).stem)
    if c.tipo in ("resumen_banco", "resumen_tarjeta") and c.banco:
        carpeta = BANCOS / c.banco / Path(c.producto.replace("\\", "/")) / str(fecha.year)
        descriptivo = re.search(r"\d{4}", Path(nombre_original).stem)
        nombre = nombre_original if descriptivo else (
            f"Extracto {fecha:%Y %m}.pdf" if c.producto == "Extractos" else f"{fecha:%Y %m}.pdf")
        return carpeta, nombre
    if c.tipo == "resumen_proveedor":
        return RESUMENES_PROVEEDORES / contacto, nombre_original
    if c.tipo == "contrato":
        if re.search(r"FIJACI", nombre_original, re.I) and c.numero:
            return CONTRATOS, f"Fijacion cto. {c.numero}.pdf"
        return CONTRATOS, f"Contrato {contacto}{' ' + c.numero if c.numero else ''}.pdf"
    ejercicio = carpeta_ejercicio(fecha).name
    if c.modulo == "pagos":
        return PAGOS / ejercicio, f"{fecha:%Y%m%d}_{contacto}_Recibo_{_seguro(c.numero or Path(nombre_original).stem)}.pdf"
    if c.modulo == "impuestos":
        return IMPUESTOS / ejercicio, f"{fecha:%Y%m%d}_{contacto}.pdf"
    if c.modulo == "ventas":
        return VENTAS / ejercicio, f"{fecha:%Y%m%d}_{contacto}.pdf"
    return COMPRAS / ejercicio, f"{fecha:%Y%m%d}_{contacto}.pdf"


def buscar_contacto_por_cuit(cuit: str) -> tuple[int, str] | None:
    from src.db.connection import fetch_one

    fila = fetch_one("SELECT TOP 1 IdContacto AS id, [Razon Social] AS nombre FROM dbo.Contactos "
                     "WHERE REPLACE(REPLACE([CUIT/CUIL], '-', ''), ' ', '') = ? ORDER BY IdContacto", (cuit,))
    return (fila["id"], fila["nombre"]) if fila else None


def _normalizar(s: str) -> str:
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", s.upper().replace(".", "")).split())


def _por_nombre(texto: str) -> tuple[int, str] | None:
    """Contactos sin CUIT cargado (ej. Allianz, CEAMSE): la razón social completa aparece en el comprobante.
    Gana la más larga; se descartan nombres de menos de 5 letras y Giamigli."""
    from src.db.connection import fetch_all

    t = f" {_normalizar(texto)} "
    candidatos = []
    for f in fetch_all("SELECT IdContacto AS id, [Razon Social] AS nombre FROM dbo.Contactos "
                       "WHERE LEN([Razon Social]) >= 5"):
        n = _normalizar(f["nombre"] or "")
        if len(n) >= 5 and "GIAMIGLI" not in n and f" {n} " in t:
            candidatos.append((len(n), f["id"], f["nombre"]))
    if not candidatos:
        return None
    _, id_, nombre = max(candidatos)
    return id_, nombre


buscar_contacto_por_cuit.por_nombre = _por_nombre

_SOCIETARIO = {"SA", "SRL", "SAS", "SACI", "SAIC", "SACIF", "SCA", "SH", "SC", "LTDA", "COOP"}


def _sin_societario(s: str) -> str:
    return " ".join(p for p in _normalizar(s).split() if p not in _SOCIETARIO)


def contacto_por_remitente(remitente: str | None, contactos: list[dict] | None = None) -> tuple[int, str] | None:
    """Emisor por el nombre del remitente del mail, cuando el PDF no lo identifica (ej. resumen de Agrovet Integral
    que solo dice "Cliente 1135 GIAMIGLI", 03/11/2026). Solo si coincide con UN contacto (sin forma societaria);
    direcciones de mail y nombres cortos no se usan."""
    nombre = _sin_societario(remitente or "")
    if not nombre or "@" in (remitente or "") or len(nombre) < 5 or "GIAMIGLI" in nombre:
        return None
    if contactos is None:
        from src.db.connection import fetch_all

        contactos = fetch_all("SELECT IdContacto AS id, [Razon Social] AS nombre FROM dbo.Contactos")
    hallados = [(f["id"], f["nombre"]) for f in contactos if _sin_societario(f["nombre"] or "") == nombre]
    return hallados[0] if len(hallados) == 1 else None
