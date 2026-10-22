"""039: "Liquidación de Pastaje" en PDF (A4), mismo contenido y orden que la liquidación
de referencia de septiembre 2026 (Documents/La Herencia/Ganaderia/Pastaje - La Herencia):
1. Parámetros del Acuerdo, 2. Proporción Temporal, 3. Valorización (Índice INMAG), total + IVA.
La variante de ajuste agrega la comparación original / recalculado / diferencia."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.features.pastaje.calculo import MESES

AZUL = colors.HexColor("#1F3B57")
GRIS = colors.HexColor("#6B6B6B")
FONDO = colors.HexColor("#EEF1F4")
LINEA = colors.HexColor("#D9D6CF")
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

_base = ParagraphStyle("base", fontName="Helvetica", fontSize=10, leading=13)
_titulo = ParagraphStyle("titulo", parent=_base, fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=AZUL)
_sub = ParagraphStyle("sub", parent=_base, fontSize=11, textColor=GRIS)
_seccion = ParagraphStyle("seccion", parent=_base, fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=AZUL)
_nota = ParagraphStyle("nota", parent=_base, fontSize=9.5, leading=12)
_pie = ParagraphStyle("pie", parent=_base, fontSize=8, textColor=GRIS)


def num(v, dec: int = 2) -> str:
    """Formato global: miles con punto, decimales con coma; sin decimales si son cero y dec=None."""
    d = Decimal(str(v))
    if dec is None:
        dec = 0 if d == d.to_integral() else 2
    texto = f"{d:,.{dec}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def pesos(v) -> str:
    return f"$ {num(v)}"


def _d(iso: str) -> date:
    return date.fromisoformat(iso[:10])


def _mes(p: date) -> str:
    return MESES[p.month - 1].capitalize()


def _tabla(filas, anchos, cabecera=True, negrita_ultima=False):
    t = Table(filas, colWidths=anchos)
    estilo = [("FONT", (0, 0), (-1, -1), "Helvetica", 10), ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINEA),
              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]
    if cabecera:
        estilo += [("BACKGROUND", (0, 0), (-1, 0), FONDO), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10)]
    if negrita_ultima:
        estilo += [("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 10)]
    t.setStyle(TableStyle(estilo))
    return t


def _parametros(liq: dict, contrato: dict, tarifas: list[dict]) -> list:
    periodo = _d(liq["periodo"])
    tramos = liq["tramos"]
    desde, hasta = min(_d(t["desde"]) for t in tramos), max(_d(t["hasta"]) for t in tramos)
    dias = (hasta - desde).days + 1
    filas = [["Concepto", "Detalle"], ["Cliente", contrato["cliente"]]]
    for cat in dict.fromkeys(t["categoria"] for t in tramos):
        trs = [t for t in tramos if t["categoria"] == cat]
        cab = sorted({t["cabezas"] for t in trs})
        filas.append(["Categoría / Hacienda", cat])
        filas.append(["Cantidad de Cabezas", " / ".join(str(c) for c in cab) + " cabezas"])
        t0 = trs[0]
        if t0["tipoTarifa"] == "kg_novillo":
            filas.append(["Tarifa Acordada", f"{num(t0['valorMes'], None)} kg de novillo / mes / cabeza"])
        else:
            mon = "US$" if t0["tipoTarifa"] == "fijo_usd" else "$"
            filas.append(["Tarifa Acordada", f"{mon} {num(t0['valorMes'])} / mes / cabeza"])
    ingreso = _d(contrato["fechaInicio"])
    if ingreso.year == periodo.year and ingreso.month == periodo.month:
        filas.append(["Fecha de Ingreso", f"{ingreso.day} de {_mes(ingreso)}"])
    filas.append(["Período Facturado", f"Del {desde.day} al {hasta.day} de {_mes(periodo)} ({dias} días)"])
    return [_tabla(filas, [70 * mm, 105 * mm])]


def _proporcion(liq: dict) -> list:
    periodo = _d(liq["periodo"])
    dias_mes = (date(periodo.year + periodo.month // 12, periodo.month % 12 + 1, 1) - periodo).days
    kg = any(t["tipoTarifa"] == "kg_novillo" for t in liq["tramos"])
    filas = [["Tramo", "Cabezas", "Días computados", "Kilos Totales Proporcionales" if kg else "Importe proporcional"]]
    for t in liq["tramos"]:
        filas.append([f"{t['categoria']} del {_d(t['desde']).day} al {_d(t['hasta']).day}", str(t["cabezas"]),
                      f"{t['dias']} de {dias_mes} días",
                      f"{num(t['kg'], None)} kg de novillo" if t["tipoTarifa"] == "kg_novillo" else pesos(t["importe"])])
    if len(liq["tramos"]) > 1 and kg:
        filas.append(["Total", "", "", f"{num(liq['kg'], None)} kg de novillo"])
    out = [_tabla(filas, [62 * mm, 22 * mm, 38 * mm, 53 * mm], negrita_ultima=len(liq["tramos"]) > 1 and kg)]
    if kg and len(liq["tramos"]) == 1:
        t = liq["tramos"][0]
        mensual = Decimal(t["valorMes"]) * t["cabezas"]
        pct = Decimal(t["dias"]) * 100 / dias_mes
        out += [Spacer(1, 4 * mm), Paragraph(
            f"<b>Cálculo:</b> {t['cabezas']} cabezas × {num(t['valorMes'], None)} kg mensuales = {num(mensual, None)} kg/mes. "
            f"Aplicando la proporción de {t['dias']} días sobre un mes de {dias_mes} días ({num(pct, None)}%), "
            f"resultan {num(t['kg'], None)} kg de novillo totales para el período.", _nota)]
    return out


def _valorizacion(liq: dict) -> list:
    tramos = liq["tramos"]
    desde, hasta = min(_d(t["desde"]) for t in tramos), max(_d(t["hasta"]) for t in tramos)
    rango = f"del {desde.day} al {hasta.day} de {MESES[desde.month - 1]}"
    out = [Paragraph(f"<b>Criterio:</b> Se toma el promedio de cotización del período de facturación ({rango}).", _nota),
           Spacer(1, 3 * mm)]
    filas = [["Referencia de Mercado (INMAG Cañuelas)", "Valor por kg vivo"]]
    for i in liq["indices"]:
        f = _d(i["fecha"])
        filas.append([f"{DIAS[f.weekday()]} {f:%d/%m}", pesos(i["indice"])])
    filas.append([f"Valor Promedio Aplicado ({desde.day} al {hasta:%d/%m})", pesos(liq["precioPromedio"])])
    out.append(_tabla(filas, [120 * mm, 55 * mm], negrita_ultima=True))
    return out


def _total(liq: dict, etiqueta: str) -> Table:
    alic = liq.get("alicuotaIva", "21")
    mon = "US$" if liq.get("moneda") == "USD" else "$"
    t = Table([[etiqueta, f"{mon} {num(liq['neto'])}"], [f"+ IVA ({num(alic, None)}%)", f"{mon} {num(liq['iva'])}"],
               ["TOTAL CON IVA", f"{mon} {num(liq['total'])}"]], colWidths=[120 * mm, 55 * mm])
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 10), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 12),
                           ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 10), ("BACKGROUND", (0, 0), (-1, 0), FONDO),
                           ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINEA),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


def generar(liq: dict, contrato: dict, tarifas: list[dict], original: dict | None = None) -> bytes:
    """`liq` como lo devuelve repository.liquidacion (más alicuotaIva); `original` solo para ajustes."""
    periodo = _d(liq["periodo"])
    mes = f"{_mes(periodo)} {periodo.year}"
    titulo = "Liquidación de Ajuste de Pastaje" if original else "Liquidación Proporcional de Pastaje"
    buf = BytesIO()

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRIS)
        canvas.drawString(18 * mm, 12 * mm, f"Liquidación de Pastaje – {mes} · Giamigli de Bolívar S.A.")
        canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=22 * mm,
                            title=f"{titulo} – {mes}")
    h = [Paragraph(titulo, _titulo), Spacer(1, 2 * mm),
         Paragraph(f"Resumen de cuenta y parámetros de facturación – {mes}", _sub), Spacer(1, 8 * mm),
         Paragraph("1. Parámetros del Acuerdo", _seccion), Spacer(1, 3 * mm), *_parametros(liq, contrato, tarifas),
         Spacer(1, 7 * mm), Paragraph(f"2. Proporción Temporal ({_mes(periodo)})", _seccion), Spacer(1, 3 * mm),
         *_proporcion(liq)]
    if liq.get("precioPromedio"):
        h += [Spacer(1, 7 * mm), Paragraph("3. Valorización (Índice INMAG)", _seccion), Spacer(1, 3 * mm), *_valorizacion(liq)]
    h.append(Spacer(1, 8 * mm))
    if original:
        h += [Paragraph("4. Ajuste respecto de la liquidación original", _seccion), Spacer(1, 3 * mm),
              _tabla([["Concepto", "Original", "Recalculado", "Diferencia"],
                      ["Neto", pesos(original["neto"]), pesos(Decimal(original["neto"]) + Decimal(liq["neto"])), pesos(liq["neto"])]],
                     [55 * mm, 40 * mm, 40 * mm, 40 * mm]),
              Spacer(1, 6 * mm), _total(liq, "DIFERENCIA A FACTURAR" if Decimal(liq["neto"]) > 0 else "DIFERENCIA A ACREDITAR")]
    else:
        h.append(_total(liq, f"TOTAL A FACTURAR ({_mes(periodo)})"))
    doc.build(h, onFirstPage=pie, onLaterPages=pie)
    return buf.getvalue()


def nombre_archivo(liq: dict, cliente: str) -> str:
    p = _d(liq["periodo"])
    pref = "Liquidación de Ajuste de Pastaje" if liq.get("tipo") == "ajuste" else "Liquidación de Pastaje"
    limpio = "".join(c for c in cliente if c not in '\\/:*?"<>|').strip()
    return f"{pref} - {_mes(p)} {p.year} - {limpio}.pdf"
