"""Carga del recuento físico de stock desde la planilla (exportacion.recuento_xlsx).

Lee la planilla completada en el campo, compara lo contado contra la existencia del
sistema a la fecha del recuento y, al confirmar, graba un ajuste por cada diferencia
(faltante o sobrante) en una sola transacción.

Los productos se identifican por la columna oculta "Id producto"; las planillas
anteriores, sin esa columna, se resuelven por el nombre exacto del producto.
"""

from __future__ import annotations

import io
import re
from datetime import date

from openpyxl import load_workbook

from src.db.connection import execute_write_transaction, fetch_all
from src.db.params import as_sql_datetime
from src.features.remitos import stock_repo

TOLERANCIA = 0.005


def _texto(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip().upper()


def _numero(v) -> float | None:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(".", "").replace(",", ".") if "," in str(v) else str(v).strip()
    try:
        return float(s)
    except ValueError:
        raise ValueError([f"«{v}» no es una cantidad válida."]) from None


def leer_planilla(contenido: bytes) -> dict:
    """Filas contadas de la planilla y, si se completó, la fecha del recuento."""
    try:
        ws = load_workbook(io.BytesIO(contenido), data_only=True).active
    except Exception as exc:  # archivo que no es un .xlsx
        raise ValueError(["No se pudo leer el archivo: tiene que ser la planilla de recuento en Excel (.xlsx)."]) from exc
    encabezado, columnas, fecha = None, {}, None
    for fila in ws.iter_rows(min_row=1, max_row=15):
        for celda in fila:
            m = re.search(r"Fecha del recuento:\s*(\d{1,2})/(\d{1,2})/(\d{4})", str(celda.value or ""))
            if m:
                fecha = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        nombres = {_texto(c.value): c.column for c in fila if c.value}
        if "PRODUCTO" in nombres and "CANTIDAD CONTADA" in nombres:
            encabezado, columnas = fila[0].row, nombres
            break
    if encabezado is None:
        raise ValueError(["La planilla no tiene las columnas «Producto» y «Cantidad contada»."])
    filas = []
    for fila in ws.iter_rows(min_row=encabezado + 1):
        valores = {c.column: c.value for c in fila}
        nombre = valores.get(columnas["PRODUCTO"])
        n = valores.get(columnas.get("N°", 1))
        if not nombre or not isinstance(n, (int, float)):
            continue  # títulos de grupo, firma, filas vacías
        id_col = columnas.get("ID PRODUCTO")
        filas.append({
            "fila": fila[0].row,
            "idProducto": int(valores[id_col]) if id_col and valores.get(id_col) else None,
            "producto": str(nombre).strip(),
            "contada": _numero(valores.get(columnas["CANTIDAD CONTADA"])),
            "observaciones": (str(valores.get(columnas.get("OBSERVACIONES"))) if valores.get(columnas.get("OBSERVACIONES")) else None),
        })
    return {"fecha": fecha, "filas": filas}


def _existencia_a_fecha(id_producto: int, fecha: date) -> float:
    k = stock_repo.kardex(id_producto) or {"movimientos": []}
    saldo = 0.0
    for m in k["movimientos"]:  # vienen en orden cronológico, con saldo acumulado
        if str(m["fecha"])[:10] <= fecha.isoformat():
            saldo = m["saldo"]
    return round(saldo, 4)


def previsualizar(contenido: bytes, fecha: date | None) -> dict:
    planilla = leer_planilla(contenido)
    fecha = fecha or planilla["fecha"]
    if fecha is None:
        raise ValueError(["Indicá la fecha del recuento."])
    items = {i["idProducto"]: i for i in stock_repo.existencias(estado="todos")["items"]}
    por_nombre: dict[str, list[int]] = {}
    for i in items.values():
        por_nombre.setdefault(_texto(i["producto"]), []).append(i["idProducto"])

    renglones, sin_contar = [], 0
    for f in planilla["filas"]:
        if f["contada"] is None:
            sin_contar += 1
            continue
        pid = f["idProducto"]
        if pid is None:
            candidatos = por_nombre.get(_texto(f["producto"]), [])
            if not candidatos:
                candidatos = [int(r["id"]) for r in fetch_all(
                    "SELECT CAST(IdProducto AS int) AS id FROM dbo.vw_ProductosBase WHERE UPPER(LTRIM(RTRIM(Producto))) = ?", (_texto(f["producto"]),))]
            if len(candidatos) != 1:
                renglones.append({**f, "estado": "noEncontrado" if not candidatos else "ambiguo", "sistema": None, "diferencia": None, "unidadBase": None})
                continue
            pid = candidatos[0]
        info = items.get(pid, {})
        sistema = _existencia_a_fecha(pid, fecha)
        diferencia = round(f["contada"] - sistema, 4)
        estado = "sinDiferencia" if abs(diferencia) < TOLERANCIA else ("faltante" if diferencia < 0 else "sobrante")
        renglones.append({
            **f, "idProducto": pid, "producto": info.get("producto") or f["producto"], "unidadBase": info.get("unidadBase"),
            "sistema": sistema, "diferencia": diferencia, "estado": estado, "costoPromedio": info.get("costoPromedio"),
        })
    return {
        "fecha": fecha.isoformat(),
        "renglones": renglones,
        "sinContar": sin_contar,
        "resumen": {e: sum(1 for r in renglones if r["estado"] == e) for e in ("faltante", "sobrante", "sinDiferencia", "noEncontrado", "ambiguo")},
    }


def aplicar(contenido: bytes, fecha: date | None, motivo: str) -> dict:
    """Recalcula la vista previa (no confía en lo que mande el navegador) y graba un ajuste
    por cada faltante o sobrante, todos en una sola transacción."""
    if not motivo.strip():
        raise ValueError(["Indicá el motivo de los ajustes."])
    prev = previsualizar(contenido, fecha)
    problemas = [f"Fila {r['fila']}: «{r['producto']}» no se encontró en el catálogo." if r["estado"] == "noEncontrado"
                 else f"Fila {r['fila']}: «{r['producto']}» coincide con más de un producto." for r in prev["renglones"] if r["estado"] in ("noEncontrado", "ambiguo")]
    if problemas:
        raise ValueError(problemas)
    stmts = [(
        "INSERT INTO dbo.Stock_Ajustes (Fecha, IdProducto, Cantidad, CostoUnitario, Motivo) VALUES (?, ?, ?, ?, ?)",
        (as_sql_datetime(date.fromisoformat(prev["fecha"])), r["idProducto"], r["diferencia"],
         r["costoPromedio"] if r["estado"] == "sobrante" else None,
         f"{motivo.strip()}{' — ' + r['observaciones'] if r.get('observaciones') else ''}"[:255]),
    ) for r in prev["renglones"] if r["estado"] in ("faltante", "sobrante")]
    if stmts:
        execute_write_transaction(stmts)
    return {"ajustes": len(stmts), **prev["resumen"]}
