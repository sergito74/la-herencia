"""Exportaciones a planilla (.xlsx) de Órdenes de Trabajo (FR-019)."""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.features.ordenes import repository, resultado

_PESOS = '"$" #,##0.00;[Red]-"$" #,##0.00'
_CANT = "#,##0.###"
_FECHA = "dd/mm/yyyy"


def _hoja(wb: Workbook, titulo: str, columnas: list[tuple[str, float]]):
    ws = wb.active
    ws.title = titulo
    ws.append([c for c, _ in columnas])
    for i, (_, ancho) in enumerate(columnas, start=1):
        celda = ws.cell(row=1, column=i)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F3D2B")
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = ancho
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


def ordenes_xlsx(**filtros) -> bytes:
    filtros.setdefault("page", 1)
    filtros.setdefault("page_size", 5000)
    items = repository.listar_ordenes(**filtros)["items"]
    wb = Workbook()
    ws = _hoja(wb, "Órdenes de trabajo", [("N°", 8), ("Fecha", 12), ("Labor", 22), ("Contratista", 26), ("Estado", 14)])
    for o in items:
        ws.append([o["idOrden"], o["fechaPedido"], o["tipoLabor"], o["contratista"], o["estado"]])
    _cerrar(ws, {1: _FECHA})
    return _bytes(wb)


def formulario_retiro_xlsx(id_orden: int) -> bytes:
    orden = repository.obtener_orden(id_orden)
    if orden is None or orden["formularioRetiro"] is None:
        raise ValueError([f"La orden {id_orden} no tiene Formulario de Retiro."])
    wb = Workbook()
    ws = _hoja(
        wb, f"Formulario {orden['formularioRetiro']['idFormularioRetiro']}",
        [("Producto", 30), ("Cantidad", 14), ("Unidad", 12)],
    )
    for r in orden["insumos"]:
        ws.append([r["producto"], r["cantidadTotal"], r["unidad"]])
    _cerrar(ws, {1: _CANT})
    return _bytes(wb)


def resultado_cultivo_xlsx(id_cultivo: int | None = None, id_campania: int | None = None, id_lote: int | None = None) -> bytes:
    items = resultado.costo_por_cultivo_campania(id_cultivo, id_campania, id_lote)
    wb = Workbook()
    ws = _hoja(
        wb, "Costo por cultivo-campaña",
        [("Cultivo", 20), ("Campaña", 14), ("Lote", 12), ("Insumos ($)", 16), ("Maquinaria ($)", 16), ("Contratista ($)", 16), ("Total ($)", 16)],
    )
    for r in items:
        ws.append([r["cultivo"], r["campania"], r["lote"], r["costoInsumos"], r["costoMaquinaria"], r["costoContratista"], r["costoTotalOrdenes"]])
    _cerrar(ws, {3: _PESOS, 4: _PESOS, 5: _PESOS, 6: _PESOS})
    return _bytes(wb)
