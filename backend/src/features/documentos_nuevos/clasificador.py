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
        return "\n".join((p.extract_text() or "") for p in doc.pages[:paginas])


def cuits(texto: str) -> list[str]:
    vistos: list[str] = []
    for a, b, c in _CUIT.findall(texto):
        cuit = f"{a}{b}{c}"
        if a in ("20", "23", "24", "27", "30", "33", "34") and cuit not in vistos:
            vistos.append(cuit)
    return vistos


def _importe(s: str) -> Decimal:
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
    # El detalle de un recibo nombra facturas/NC canceladas: no cambia su encabezado.
    if re.search(r"^\s*(?:ORIGINAL\s+)?RECIBO(?:\s+DE\s+(?:INGRESO|PAGO|COBRANZA)|\s+(?:N[ÚU]MERO|N[°º]))", t, re.M):
        return "recibo"
    if re.search(r"\bPRESUPUESTO\b|\bCOTIZACI[OÓ]N\b|\bCAT[AÁ]LOGO\b|\bLISTA DE PRECIOS\b", t) and \
            not re.search(r"\bFACTURA\b|\bCAE\b", t):
        return None
    if re.search(r"CONTRATO DE (COMPRA ?VENTA|COMPRAVENTA)|CARTA DE FIJACI[OÓ]N|\bFIJACI[OÓ]N\b.*\bCONTRATO\b", t):
        return "contrato"
    if re.search(r"CERTIFICADO DE RETENCI[OÓ]N|CONSTANCIA DE RETENCI[OÓ]N", t):
        return "retencion"
    if re.search(r"LIQUIDACI[OÓ]N PRIMARIA DE GRANOS|LIQUIDACI[OÓ]N (DE )?HACIENDA|LIQUIDACI[OÓ]N DE VENTA|"
                 r"CUENTA DE VENTA Y L[IÍ]QUIDO PRODUCTO|\bLPG\b", t):
        return "liquidacion"
    # Una factura numerada con CAE es factura aunque traiga "saldo anterior" o "estado de cuenta" (Movistar, AUSOL).
    numerada = re.search(r"\bCAE\b|C\.A\.E\.", t) and numero_de(texto)
    if numerada and re.search(r"NOTA DE CR[EÉ]DITO", t):
        return "nota_credito"
    if numerada and re.search(r"NOTA DE D[EÉ]BITO", t):
        return "nota_debito"
    if numerada and re.search(r"\bFACTURA\b", t):
        return "factura"
    if re.search(r"RESUMEN DE (CUENTA )?TARJETA|RESUMEN (VISA|MASTERCARD|AMERICAN EXPRESS)|\bAGRONACI[OÓ]N\b.*RESUMEN", t):
        return "resumen_tarjeta"
    if re.search(r"EXTRACTO (DE CUENTA|BANCARIO)|RESUMEN DE CUENTA CORRIENTE|RESUMEN DE CAJA DE AHORRO|"
                 r"SALDO ANTERIOR.*SALDO (ACTUAL|FINAL)", t, re.S) and re.search(r"\bBANCO\b|GALICIA", t):
        return "resumen_banco"
    if re.search(r"RESUMEN DE CUENTA|ESTADO DE CUENTA|COMPOSICI[OÓ]N DE SALDO", t):
        return "resumen_proveedor"
    if re.search(r"NOTA DE CR[EÉ]DITO", t):
        return "nota_credito"
    if re.search(r"NOTA DE D[EÉ]BITO", t):
        return "nota_debito"
    if re.search(r"\bBOLETA\b|VOLANTE ELECTR[OÓ]NICO DE PAGO|\bVEP\b|FORMULARIO DE PAGO", t) or \
            (re.search(r"\bIMPUESTO\b|\bTASA\b|\bPATENTE\b", t) and re.search(r"\bVENCIMIENTO\b", t)
             and re.search(r"A PAGAR", t)):
        return "boleta"
    # Cupón de pago (Sancor): aviso de vencimiento, no comprobante; la deuda llega en las facturas mensuales (046, 30/10).
    if re.search(r"CUP[OÓ]N (DE PAGO|PARA EL)", t) and not re.search(r"\bCAE\b|C\.A\.E\.", t):
        return None
    if re.search(r"\bRECIBO\b", t) and not re.search(r"\bFACTURA\b", t):
        return "recibo"
    # Liquidación mensual del banco (comisiones) y tickets de estaciones de servicio se cargan como facturas.
    if re.search(r"\bFACTURA\b|LIQUIDACI[OÓ]N ELECTR[OÓ]NICA|\bTICKET\b", t):
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
    return SAN_JUSTO in cuits(texto) or "SAN JUSTO" in texto.upper()


def receptor(texto: str, cuit_emisor: str | None) -> str:
    """`giamigli` (Giamigli, la Sucesión —etapa previa de Giamigli— o sin receptor visible), `persona` (a nombre
    de otra persona: se avisa para confirmar) u `otra` (otra sociedad, ej. Ganadera San Justo: no se registra ni
    se guarda). Lo que está a nombre de Sergio es gasto de Giamigli y se carga normalmente."""
    t = texto.upper()
    if es_de_san_justo(texto):
        return "otra"
    otros = [c for c in cuits(texto) if c != cuit_emisor]
    if GIAMIGLI in otros or SERGIO in otros or "GIAMIGLI" in t or "SUCESI" in t or not otros:
        return "giamigli"
    return "persona" if any(c[:2] in ("20", "23", "24", "27") for c in otros) else "otra"


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


def numero_de(texto: str) -> str | None:
    m = re.search(r"\b(\d{4,5})\s*-\s*(\d{8})\b", texto)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"Punto de Venta:?\s*(\d{1,5}).{0,20}?(?:Comp\.?|Comprobante)\s*N[rº°o]*\.?:?\s*(\d{8})", texto, re.I)
    return f"{int(m.group(1)):05d}-{m.group(2)}" if m else None


_MONTO = r"\$?\s*(\d[\d.]*,\d{2})(?!\s*%)"


def total_de(texto: str) -> Decimal | None:
    """Total impreso: primero las leyendas explícitas; si no, el último renglón que empieza con TOTAL
    (nunca SUBTOTAL ni una alícuota)."""
    for patron in (r"TOTAL A PAGAR", r"IMPORTE TOTAL", r"TOTAL FACTURA(?: ACTUAL)?"):
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
    emisores = [c for c in cuits(texto) if c != GIAMIGLI]
    cuit = emisores[0] if emisores else None
    c = Clasificacion(comprobante=True, tipo=tipo, modulo=MODULO[tipo], cuit_emisor=cuit, fecha=fecha_de(texto),
                      numero=numero_de(texto), total=total_de(texto))
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
        encontrado = por_nombre(texto)
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
