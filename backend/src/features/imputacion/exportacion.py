"""Exportación a Excel del informe de imputación por documento comercial
(pedido del usuario, 2026-09-25) — para la oficina del contador.

Cada línea de factura queda seguida de sus fracciones de imputación como
filas agrupadas (`outline_level`): Excel las muestra plegadas por defecto,
con el signo "+" para desplegarlas — el equivalente en planilla de las
"filas desplegables" pedidas para la pantalla.
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.features.imputacion import repository

_PESOS = '"$" #,##0.00;[Red]-"$" #,##0.00'
_FECHA = "dd/mm/yyyy"

_COLUMNAS = [
    ("Documento", 22),
    ("Fecha", 12),
    ("Proveedor", 30),
    ("Moneda", 10),
    ("Tipo de Cambio", 12),
    ("Producto/Servicio", 32),
    ("Cantidad", 12),
    ("Campaña manual", 16),
    ("Centro/Cultivo/Campaña (motor)", 30),
    ("Origen (lote/orden)", 20),
    ("Importe", 14),
    ("Estado", 18),
]

_COL_IMPORTE = 10  # índice 0-based dentro de la fila (columna "Importe")


def _etiqueta_destino(f: dict) -> str:
    if f.get("cultivo"):
        return f"{f['cultivo']} / {f.get('campania') or '—'}"
    if f.get("centroCosto"):
        return f["centroCosto"]
    if f.get("esGanaderia"):
        return "Ganadería"
    return "En stock sin consumir"


def _origen_trazable(f: dict) -> str:
    """Resumen de origen (sin la cadena FIFO completa, que exige recalcular
    por renglón — ver `motor.trazabilidad_insumo` para el detalle exacto
    desde la pantalla): Lote y Orden de Trabajo, cuando la fracción viene de
    consumo real (hallazgo de revisión financiera, 2026-09-25 — antes el
    Excel no daba ninguna pista de origen)."""
    partes = []
    if f.get("lote"):
        partes.append(f"Lote {f['lote']}")
    if f.get("idOrdenTrabajo"):
        partes.append(f"Orden {f['idOrdenTrabajo']}")
    return " · ".join(partes) if partes else "—"


def informe_documentos_xlsx(id_contacto: int | None, fecha_desde, fecha_hasta, estado: str | None = None) -> bytes:
    documentos, _total = repository.listar_documentos_con_imputacion(
        id_contacto, fecha_desde, fecha_hasta, estado, page=1, page_size=5000
    )
    total_general = 0.0

    wb = Workbook()
    ws = wb.active
    ws.title = "Imputación por documento"
    ws.append([c for c, _ in _COLUMNAS])
    for i, (_, ancho) in enumerate(_COLUMNAS, start=1):
        celda = ws.cell(row=1, column=i)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F3D2B")
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = ancho
    ws.freeze_panes = "A2"

    lineas_por_compra = repository.lineas_con_imputacion_batch(tuple(d["idCompra"] for d in documentos))

    fila = 2
    for doc in documentos:
        documento = f"{doc['tipoDocumento'] or ''} {doc['numeroDocumento'] or ''}".strip()
        lineas = lineas_por_compra.get(doc["idCompra"], [])
        total_documento = 0.0
        for linea in lineas:
            total_linea = round(sum(float(f["importe"]) for f in linea["fracciones"]), 2)
            total_documento += total_linea
            ws.append(
                [
                    documento,
                    doc["fecha"],
                    doc["proveedor"],
                    doc["moneda"],
                    float(doc["tipoDeCambio"]) if doc.get("tipoDeCambio") is not None else None,
                    linea["producto"],
                    linea["cantidad"],
                    linea.get("campaniaManual") or "—",
                    "",
                    "",
                    "",
                    "",
                ]
            )
            fila += 1
            for f in linea["fracciones"]:
                ws.append(
                    [
                        "", "", "", "", "", "",
                        "",
                        "",
                        _etiqueta_destino(f),
                        _origen_trazable(f),
                        f["importe"],
                        f["estado"],
                    ]
                )
                ws.row_dimensions[fila].outline_level = 1
                fila += 1
        total_general += total_documento
        ws.append(["", "", "", "", "", "", "", "", f"Total {documento}", "", round(total_documento, 2), ""])
        for c in ws[fila]:
            c.font = Font(bold=True)
        fila += 1

    ws.append(["", "", "", "", "", "", "", "", "TOTAL GENERAL", "", round(total_general, 2), ""])
    for c in ws[fila]:
        c.font = Font(bold=True, color="1F3D2B")

    ws.sheet_properties.outlinePr.summaryBelow = False
    for r in ws.iter_rows(min_row=2, max_row=ws.max_row):
        r[1].number_format = _FECHA
        r[_COL_IMPORTE].number_format = _PESOS
    if ws.max_row >= 2:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(_COLUMNAS))}{ws.max_row}"

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
