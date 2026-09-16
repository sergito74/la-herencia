"""Validate and preview bank/tarjeta Excel summaries in memory (FR-007/008/009).

Never persists anything in SQL Server or on disk — parses the uploaded
bytes, validates the header shape against the two known real formats
(BNA `.xls`, Galicia `.xlsx`), and returns a preview. Confirmed against
real files on 2026-09-16 (see research.md/data-model.md): BNA has 5
metadata rows before the real header (row 6) and amounts as Argentine-
formatted text; Galicia has a plain header on row 1 of the `Movimientos`
sheet. Neither format carries a structured contact column, so no matching
against compras is attempted here (that only applies to movimientos
already in SQL Server).
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime

import openpyxl
import xlrd

BNA_HEADER = ("Fecha", "Comprobante", "Concepto", "Importe", "Saldo")
GALICIA_REQUIRED_HEADER = ("Fecha", "Descripción", "Débitos", "Créditos", "Saldo")
GALICIA_SHEET_NAME = "Movimientos"

_IMPORTE_RE = re.compile(r"[^0-9,.\-]")


def _parse_importe_arg(texto: str | float | int | None) -> float | None:
    """Parse `"$ 1.234,56"` / `"$ -9,00"` (Argentine format) into a float."""
    if texto is None:
        return None
    if isinstance(texto, (int, float)):
        return float(texto)
    cleaned = _IMPORTE_RE.sub("", str(texto)).strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _procesar_bna(contenido: bytes) -> dict:
    try:
        book = xlrd.open_workbook(file_contents=contenido)
        sheet = book.sheet_by_index(0)
    except Exception:
        return _invalido("No se pudo leer el archivo como .xls (BNA)")

    header_row_index = None
    for row_idx in range(min(10, sheet.nrows)):
        values = [str(sheet.cell_value(row_idx, col)).strip() for col in range(sheet.ncols)]
        if values[: len(BNA_HEADER)] == list(BNA_HEADER):
            header_row_index = row_idx
            break

    if header_row_index is None:
        return _invalido(
            "No se encontró la fila de encabezado esperada "
            "('Fecha, Comprobante, Concepto, Importe, Saldo' para BNA, "
            "o 'Fecha, Descripción, ...' para Galicia) en las primeras 10 filas"
        )

    movimientos = []
    for row_idx in range(header_row_index + 1, sheet.nrows):
        fecha_cell = sheet.cell(row_idx, 0)
        if fecha_cell.ctype == xlrd.XL_CELL_EMPTY:
            continue
        fecha = _xldate_to_date(fecha_cell.value, book.datemode)
        movimientos.append(
            {
                "fecha": fecha,
                "comprobante": str(sheet.cell_value(row_idx, 1)).strip() or None,
                "concepto": str(sheet.cell_value(row_idx, 2)).strip() or None,
                "importe": _parse_importe_arg(sheet.cell_value(row_idx, 3)),
                "saldo": _parse_importe_arg(sheet.cell_value(row_idx, 4)),
            }
        )

    return {
        "medioDetectado": "bna",
        "valido": True,
        "errores": [],
        "movimientosPrevisualizados": movimientos,
    }


def _xldate_to_date(value: float | str, datemode: int) -> date | None:
    if isinstance(value, str):
        return None
    try:
        return xlrd.xldate_as_datetime(value, datemode).date()
    except (ValueError, TypeError):
        return None


def _procesar_galicia(contenido: bytes) -> dict:
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True, read_only=True)
    except Exception:
        return _invalido("No se pudo leer el archivo como .xlsx (Galicia)")

    if GALICIA_SHEET_NAME not in workbook.sheetnames:
        return _invalido(
            f"No se encontró la hoja '{GALICIA_SHEET_NAME}' esperada para el formato Galicia"
        )
    sheet = workbook[GALICIA_SHEET_NAME]

    rows = sheet.iter_rows(values_only=True)
    try:
        header = [str(cell).strip() if cell is not None else "" for cell in next(rows)]
    except StopIteration:
        return _invalido("La hoja 'Movimientos' está vacía")

    if not all(col in header for col in GALICIA_REQUIRED_HEADER):
        return _invalido(
            "No se encontró la fila de encabezado esperada "
            "('Fecha, Comprobante, Concepto, Importe, Saldo' para BNA, "
            "o 'Fecha, Descripción, ...' para Galicia) en las primeras 10 filas"
        )

    index = {name: header.index(name) for name in header if name}
    leyenda_cols = [
        index[c]
        for c in (
            "Leyendas Adicionales 1",
            "Leyendas Adicionales 2",
            "Leyendas Adicionales 3",
            "Leyendas Adicionales 4",
        )
        if c in index
    ]

    movimientos = []
    for row in rows:
        if row[index["Fecha"]] is None:
            continue
        fecha_valor = row[index["Fecha"]]
        fecha = fecha_valor.date() if isinstance(fecha_valor, datetime) else fecha_valor
        comprobante_col = index.get("Número de Comprobante")
        comprobante_valor = row[comprobante_col] if comprobante_col is not None else None
        movimientos.append(
            {
                "fecha": fecha,
                "descripcion": row[index["Descripción"]],
                "debitos": row[index["Débitos"]],
                "creditos": row[index["Créditos"]],
                "numeroComprobante": (
                    str(comprobante_valor) if comprobante_valor is not None else None
                ),
                "leyendas": [row[i] for i in leyenda_cols],
                "saldo": row[index["Saldo"]],
            }
        )

    return {
        "medioDetectado": "galicia",
        "valido": True,
        "errores": [],
        "movimientosPrevisualizados": movimientos,
    }


def _invalido(mensaje: str) -> dict:
    return {
        "medioDetectado": None,
        "valido": False,
        "errores": [mensaje],
        "movimientosPrevisualizados": [],
    }


def validar_y_previsualizar(filename: str, contenido: bytes) -> dict:
    nombre = filename.lower()
    if nombre.endswith(".xls"):
        return _procesar_bna(contenido)
    if nombre.endswith(".xlsx"):
        return _procesar_galicia(contenido)
    return _invalido(
        "Formato de archivo no reconocido: se espera .xls (BNA) o .xlsx (Galicia)"
    )
