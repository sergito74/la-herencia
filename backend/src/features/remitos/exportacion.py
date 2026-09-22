"""Exportaciones a planilla (.xlsx) de remitos, existencias valorizadas y bajas de stock.

Los importes van como números con formato de celda (`$` / miles y decimales según la
configuración regional de quien abre el archivo) y las fechas como fechas reales.
"""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.features.remitos import repository, stock_repo

_PESOS = '"$" #,##0.00;[Red]-"$" #,##0.00'
_CANT = "#,##0.###"
_FECHA = "dd/mm/yyyy"
_ESTADO_FACTURA = {"SinFactura": "Sin factura", "Facturado": "Facturado"}
_ESTADO_RENGLONES = {"SinVincular": "Sin vincular", "Parcial": "Parcial", "Completo": "Completo", "ConDiferencia": "Con diferencia"}


def _hoja(wb: Workbook, titulo: str, columnas: list[tuple[str, float]], primera: bool = False):
    ws = wb.active if primera else wb.create_sheet(titulo)
    ws.title = titulo
    ws.append([c for c, _ in columnas])
    for i, (_, ancho) in enumerate(columnas, start=1):
        celda = ws.cell(row=1, column=i)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F3D2B")
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = ancho
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"
    return ws


def _cerrar(ws, formatos: dict[int, str]) -> None:
    for fila in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for col, fmt in formatos.items():
            fila[col].number_format = fmt
    if ws.max_row >= 2:
        ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"


def _bytes(wb: Workbook) -> bytes:
    b = BytesIO()
    wb.save(b)
    return b.getvalue()


def remitos_xlsx(**filtros) -> bytes:
    lista = repository.listar_remitos(page=1, page_size=100000, **filtros)["items"]
    wb = Workbook()
    ws = _hoja(wb, "Remitos", [("Fecha", 12), ("Proveedor", 34), ("N° de remito", 18), ("Productos", 46), ("Renglones", 10),
                               ("Facturas", 30), ("Factura", 13), ("Renglones vinculados", 16), ("Días sin factura", 12), ("Anulado", 9), ("A revisar", 9)], primera=True)
    for r in lista:
        ws.append([r["fecha"], r["proveedor"], r["nroRemito"], r["productos"], r["renglones"], ", ".join(r["facturas"]) or None,
                   _ESTADO_FACTURA[r["estadoFactura"]], _ESTADO_RENGLONES[r["estadoRenglones"]], r["diasSinFactura"],
                   "Sí" if r["anulado"] else None, "Sí" if r["revisarDuplicado"] else None])
    _cerrar(ws, {0: _FECHA})
    # detalle por renglón
    wd = _hoja(wb, "Renglones", [("Fecha", 12), ("Proveedor", 32), ("N° de remito", 18), ("Producto", 40), ("Tipo", 14), ("Cantidad", 12), ("Unidad", 9),
                                 ("Vencimiento", 12), ("Vinculado", 12), ("Estado", 14), ("Costo unitario", 15), ("Consumido", 12), ("Anulado", 9)])
    for r in lista:
        det = repository.get_remito(r["idRemito"])
        for l in det["renglones"]:
            wd.append([det["fecha"], det["proveedor"], det["nroRemito"], l["producto"], l["tipo"], l["cantidad"], l["unidad"], l["vencimiento"],
                       l["cantidadVinculada"], _ESTADO_RENGLONES[l["estadoVinculo"]], l["costoUnitario"], l["consumido"], "Sí" if det["anulado"] else None])
    _cerrar(wd, {0: _FECHA, 5: _CANT, 7: _FECHA, 8: _CANT, 10: _PESOS, 11: _CANT})
    return _bytes(wb)


def existencias_xlsx(q=None, tipo=None, estado=None) -> bytes:
    datos = stock_repo.existencias(q, tipo, estado)
    wb = Workbook()
    ws = _hoja(wb, "Existencias", [("Producto", 42), ("Tipo", 16), ("Unidad", 9), ("Existencia", 13), ("Valor (FIFO)", 16), ("Costo promedio", 15),
                                   ("Cantidad sin costo", 15), ("Observaciones", 40)], primera=True)
    for i in datos["items"]:
        obs = []
        if i["negativo"]:
            obs.append("Stock negativo")
        if i["cantidadCostoPendiente"] > 0.005:
            obs.append("Parte del stock sin costo (remito sin factura vinculada)")
        if i["equivalenciaPendiente"]:
            obs.append("Falta equivalencia de una presentación")
        ws.append([i["producto"], i["tipo"], i["unidadBase"], i["existencia"], i["valor"], i["costoPromedio"], i["cantidadCostoPendiente"] or None, "; ".join(obs) or None])
    if datos["items"]:
        n = ws.max_row
        ws.append(["Total", None, None, None, f"=SUM(E2:E{n})"])
        for c in range(1, 6):
            ws.cell(row=ws.max_row, column=c).font = Font(bold=True)
        ws.cell(row=ws.max_row, column=5).number_format = _PESOS
    for fila in ws.iter_rows(min_row=2, max_row=ws.max_row - (1 if datos["items"] else 0)):
        fila[3].number_format = _CANT
        fila[4].number_format = _PESOS
        fila[5].number_format = _PESOS
        fila[6].number_format = _CANT
    if datos["items"]:
        ws.auto_filter.ref = f"A1:H{ws.max_row - 1}"
    return _bytes(wb)


def bajas_xlsx(**filtros) -> bytes:
    lista = stock_repo.listar_bajas(page=1, page_size=100000, **filtros)["items"]
    wb = Workbook()
    ws = _hoja(wb, "Bajas de stock", [("Fecha", 12), ("Motivo", 24), ("Detalle", 30), ("Rubro", 28), ("Centro de costos", 18), ("Producto", 40), ("Cantidad", 12),
                                      ("Unidad", 9), ("Gasto (FIFO)", 15), ("Costo pendiente", 14), ("Anulada", 9)], primera=True)
    for b in lista:
        for l in b["renglones"]:
            ws.append([b["fecha"], b["motivoLabel"], b["detalle"], b["rubro"], b["centro"], l["producto"], l["cantidad"], l["unidadBase"], l["costo"],
                       "Sí" if l["costoPendiente"] else None, "Sí" if b["anulada"] else None])
    _cerrar(ws, {0: _FECHA, 6: _CANT, 8: _PESOS})
    return _bytes(wb)
