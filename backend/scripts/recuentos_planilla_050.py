"""Lectura (solo lectura) de los recuentos de Sergio en Dropbox/La Herencia/Stocks/Stock Insumos.xlsx (050, 15/11/2026).

Una hoja por recuento ("May 25", "Sep 25", ...). Fila con la fecha, encabezado TIPO / MARCA COMERCIAL / EMPRESA /
TIPO INSUMO / Existencia / Unidad / ... y una fila por marca. Hay meses sin hoja porque ese mes no se contó.
También define las familias de fertilizantes que Sergio nombra genéricamente con un producto del catálogo:
  · ARRANCADOR = la mezcla con más fósforo (Arrancador 1515K, NP 326, Proterra 740 = 7N-40P, MZCLA 7N-39P, Fert. Mezcla 7N-40P, ...).
  · UREA = la mezcla principalmente nitrogenada (Urea granulada Profertil, urea a granel, ...).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

from src.db.connection import fetch_all
from src.features.imputacion.tamiz import normalizar

PLANILLA = Path.home() / "Dropbox" / "La Herencia" / "Stocks" / "Stock Insumos.xlsx"
_MESES = {m: i + 1 for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                           "septiembre", "octubre", "noviembre", "diciembre"])}


def familia_fertilizante(texto: str | None) -> str | None:
    """'ARRANCADOR' (fosfatada), 'UREA' (nitrogenada) o None. Por nombre o por la fórmula N-P-K del texto."""
    t = normalizar(texto or "")
    if "UREA" in t:
        return "UREA"
    if "ARRANCADOR" in t or "PROTERRA 740" in t or re.search(r"\bNP\s*\d", t):
        return "ARRANCADOR"
    m = re.search(r"(\d+)\s*N\W*(\d+)\s*P", t)
    if m:
        n, p = int(m.group(1)), int(m.group(2))
        return "ARRANCADOR" if p > n else "UREA"
    return None


def _fecha(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)(?:\s+de\s+(\d{4}))?", v.lower())
        if m and m.group(2) in _MESES and m.group(3):
            return date(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))
    return None


def leer_recuentos(planilla: Path = PLANILLA) -> list[dict]:
    """[{hoja, fecha, renglones: [{marca, tipo, ia, q, unidad}]}] ordenados por fecha."""
    wb = load_workbook(planilla, read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        fecha, cols, renglones = None, None, []
        for fila in ws.iter_rows(values_only=True):
            if cols is None:
                for v in fila:
                    fecha = fecha or _fecha(v)
                if "MARCA COMERCIAL" in [str(v or "").strip().upper() for v in fila]:
                    cols = {str(v or "").strip().upper(): i for i, v in enumerate(fila)}
                continue
            def g(c):
                i = cols.get(c)
                return fila[i] if i is not None and i < len(fila) else None
            marca, q = g("MARCA COMERCIAL"), g("EXISTENCIA")
            if not marca or not isinstance(q, (int, float)):
                continue
            renglones.append({"marca": str(marca).strip(), "tipo": g("TIPO"), "ia": g("TIPO INSUMO"), "q": float(q),
                              "unidad": g("UNIDAD")})
        if fecha and renglones:
            out.append({"hoja": ws.title, "fecha": fecha, "renglones": renglones})
    return sorted(out, key=lambda r: r["fecha"])


class Catalogo:
    """Marca del recuento → IdProducto de vw_ProductosBase (prefiere los usados en órdenes o recuentos del sistema)."""

    def __init__(self):
        usados = {int(f["p"]) for f in fetch_all(
            """SELECT IdProducto p FROM dbo.Ordenes_Trabajo_Insumos UNION SELECT IdFormulado FROM dbo.Ordenes_Detalles
               UNION SELECT IdProducto FROM dbo.Stock_Recuentos_Detalle UNION SELECT IdFormulado FROM dbo.Det_Compras""") if f["p"]}
        self.por_nombre: dict[str, int] = {}
        for f in fetch_all("SELECT CAST(IdProducto AS bigint) i, Producto n FROM dbo.vw_ProductosBase WHERE IdProducto IS NOT NULL"):
            k = normalizar(f["n"] or "")
            if k and (k not in self.por_nombre or int(f["i"]) in usados):
                self.por_nombre[k] = int(f["i"])

    def producto(self, marca: str, sug=None) -> int | None:
        k = normalizar(marca)
        if k in self.por_nombre:
            return self.por_nombre[k]
        return sug.sugerir(marca)[0] if sug else None
