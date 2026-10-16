"""Formulario de Retiro en PDF (A4 apaisado), mismo diseño que la página imprimible del
frontend (FormularioRetiroDocumento.tsx) y que la planilla del campo (Retiro_151):
membrete, datos de la orden, Ing. Activo · Marca Comercial · Cantidad · Unidad ordenado
por principio activo, columna de control y firmas."""

from __future__ import annotations

from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.features.ordenes import repository

VERDE = colors.HexColor("#2F5233")
GRIS = colors.HexColor("#6B6B6B")
LINEA = colors.HexColor("#D9D6CF")

_base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=12)
_chico = ParagraphStyle("chico", parent=_base, fontSize=7.5, leading=9, textColor=GRIS)
_rotulo = ParagraphStyle("rotulo", parent=_chico, fontName="Helvetica-Bold")


def _num(v: float, min_dec: int = 1) -> str:
    """Formato local: miles con punto, decimales con coma (mínimo `min_dec`, máximo 3)."""
    texto = f"{v:,.3f}".rstrip("0")
    entero, _, dec = texto.partition(".")
    dec = dec.ljust(min_dec, "0")
    texto = f"{entero}.{dec}" if dec else entero
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def _fecha(v) -> str:
    if not v:
        return "—"
    d = date.fromisoformat(str(v)[:10])
    return d.strftime("%d/%m/%Y")


def _p(texto: str, estilo: ParagraphStyle = _base) -> Paragraph:
    return Paragraph(texto.replace("&", "&amp;").replace("<", "&lt;"), estilo)


def _casilla() -> Table:
    """Casilla vacía para tildar al preparar el producto (las fuentes base del PDF no traen ☐)."""
    t = Table([[""]], colWidths=[3.5 * mm], rowHeights=[3.5 * mm])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, GRIS)]))
    return t


def formulario_retiro_pdf(id_orden: int) -> bytes:
    orden = repository.obtener_orden(id_orden)
    if orden is None or orden["formularioRetiro"] is None:
        raise ValueError([f"La orden {id_orden} no tiene Formulario de Retiro."])
    form = orden["formularioRetiro"]
    ancho = landscape(A4)[0] - 20 * mm

    # Membrete · título · recuadro con el N° de formulario
    logo = Table([[_p("LH", ParagraphStyle("lh", parent=_base, fontName="Helvetica-Bold", fontSize=14, textColor=colors.white, alignment=1))]],
                 colWidths=[11 * mm], rowHeights=[11 * mm])
    logo.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), VERDE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    membrete = Table([[logo, [_p("La Herencia", ParagraphStyle("t", parent=_base, fontName="Helvetica-Bold", fontSize=13, leading=15)),
                              _p("Producción agrícola · Depósito de insumos", _chico)]]],
                     colWidths=[13 * mm, 65 * mm])
    membrete.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    titulo = [_p("RETIRO DE AGROQUÍMICOS", ParagraphStyle("h", parent=_base, fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=1)),
              _p("Formulario de retiro de insumos para aplicación", ParagraphStyle("s", parent=_chico, alignment=1))]
    numero = Table([[_p("FORMULARIO N°", ParagraphStyle("r", parent=_rotulo, alignment=2))],
                    [_p(str(form["idFormularioRetiro"]), ParagraphStyle("n", parent=_base, fontName="Helvetica-Bold", fontSize=18, leading=20, alignment=2))],
                    [_p(f"Emitido {_fecha(form['fechaEmision'])}", ParagraphStyle("e", parent=_base, fontSize=8, alignment=2))]],
                   colWidths=[38 * mm])
    numero.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, colors.black), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    encabezado = Table([[membrete, titulo, numero]], colWidths=[80 * mm, ancho - 120 * mm, 40 * mm])
    encabezado.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.black), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (0, 0), 0),
    ]))

    # Datos de la orden
    destinos: dict[str, dict[str, float]] = {}
    for r in orden["insumos"]:
        for d in r["distribuciones"]:
            if d["aplicar"] and d["cantidadAsignada"] > 0:
                destinos.setdefault(" ".join(x for x in (d["cultivo"], d["campania"]) if x), {})[d["lote"] or str(d["idLote"])] = d["superficie"]
    lotes = "&nbsp;&nbsp;&nbsp;".join(
        f"<b>{c}:</b> {', '.join(l)} ({_num(sum(l.values()), 0)} ha)" for c, l in destinos.items()
    ) or "—"
    datos = Table([
        [_p("ORDEN DE TRABAJO", _rotulo), _p("FECHA", _rotulo), _p("LABOR", _rotulo), _p("CONTRATISTA", _rotulo)],
        [Paragraph(f"<b>N° {orden['idOrden']}</b>", _base), _p(_fecha(orden["fechaPedido"])), _p(orden.get("tipoLabor") or "—"),
         _p(orden.get("contratista") or "Maquinaria propia")],
        [_p("CULTIVOS Y LOTES", _rotulo), "", "", ""],
        [Paragraph(lotes, _base), "", "", ""],
    ], colWidths=[ancho / 4] * 4)
    datos.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, LINEA), ("SPAN", (0, 2), (-1, 2)), ("SPAN", (0, 3), (-1, 3)),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("TOPPADDING", (0, 2), (-1, 2), 5),
    ]))

    # Detalle
    renglones = sorted(orden["insumos"], key=lambda r: ((r.get("ingredienteActivo") or "").strip(), r["producto"] or ""))
    filas = [["#", "Ing. Activo", "Marca Comercial", "Cantidad", "Unidad", "Control"]]
    for n, r in enumerate(renglones, start=1):
        filas.append([str(n), _p((r.get("ingredienteActivo") or "").strip() or "—"),
                      Paragraph(f"<b>{(r['producto'] or str(r['idProducto'])).replace('&', '&amp;')}</b>", _base),
                      _num(r["cantidadTotal"]), r["unidad"], _casilla()])
    detalle = Table(filas, colWidths=[8 * mm, ancho - ancho * 0.28 - 68 * mm, ancho * 0.28, 24 * mm, 18 * mm, 18 * mm], repeatRows=1)
    detalle.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("LINEABOVE", (0, 0), (-1, 0), 1, colors.black), ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINEA), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"), ("ALIGN", (3, 0), (3, -1), "RIGHT"), ("ALIGN", (5, 0), (5, -1), "CENTER"),
        ("TEXTCOLOR", (0, 1), (0, -1), GRIS),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))

    # Tres firmas con separación entre líneas (columnas vacías intermedias).
    hueco = 15 * mm
    firma = (ancho - 2 * hueco) / 3
    firmas = Table([["", "", "", "", ""],
                    ["Entregó (encargado de depósito)", "", "Retiró (contratista / operario)", "", "Fecha y hora de retiro"]],
                   colWidths=[firma, hueco, firma, hueco, firma], rowHeights=[16 * mm, None])
    firmas.setStyle(TableStyle([
        *[("LINEBELOW", (c, 0), (c, 0), 0.8, colors.black) for c in (0, 2, 4)],
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 1), (-1, 1), 8),
    ]))

    historia = [encabezado, Spacer(1, 4 * mm), datos, Spacer(1, 4 * mm), detalle]
    if orden.get("observaciones"):
        historia += [Spacer(1, 3 * mm), Paragraph(f"<b>Observaciones:</b> {orden['observaciones'].replace('&', '&amp;')}", _base)]
    historia += [Spacer(1, 6 * mm), firmas]

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRIS)
        canvas.drawRightString(landscape(A4)[0] - 10 * mm, 6 * mm,
                               f"La Herencia · Orden N° {orden['idOrden']} · Formulario N° {form['idFormularioRetiro']} · Página {doc.page}")
        canvas.restoreState()

    salida = BytesIO()
    SimpleDocTemplate(salida, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=12 * mm,
                      title=f"Formulario de Retiro N° {form['idFormularioRetiro']} - Orden {orden['idOrden']}", author="La Herencia").build(
        historia, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()
