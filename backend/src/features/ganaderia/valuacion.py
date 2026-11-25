"""Valuación estimada del stock de hacienda propia a una fecha (052 FR-008 / FR-020, etapa 1).

Valor neto de realización estimado = Σ cabezas × kg × precio $/kg de la categoría × (1 − % gastos de venta).
- Precio $/kg de la categoría = INMAG (Mercado Agroganadero, Cañuelas) del día × coeficiente de la categoría.
- Coeficiente = mediana, en nuestras propias ventas desde 2016 con kg reales, de ($/kg de la venta ÷ INMAG del día).
  Una categoría con menos de MIN_VENTAS ventas toma el de la categoría de la que evoluciona (mismo sexo, orden menor
  más cercano) o, si no hay, la siguiente con datos; sin ninguna, 1.
- Reglas de Sergio por categoría (GanValuacionRegla): toro usado = 500 kg de novillo (coeficiente 1).
- % gastos de venta = comercialización ÷ ventas brutas del ejercicio (sin ventas, el de todos los ejercicios).
Es "estimada" hasta que Sergio confirme la valuación de cierre (etapa 2).
"""

from __future__ import annotations

import bisect
import statistics
import time
from collections import defaultdict
from datetime import date

MIN_VENTAS = 5
_cache: dict = {}


def _inmag_serie():
    from src.db.connection import fetch_all

    c = _cache.get("inmag")
    if c and time.time() - c[0] < 3600:
        return c[1]
    filas = fetch_all("SELECT Fecha f, Indice i FROM dbo.IndiceINMAG WHERE Indice > 0 ORDER BY Fecha")
    serie = ([str(r["f"])[:10] for r in filas], [float(r["i"]) for r in filas])
    _cache["inmag"] = (time.time(), serie)
    return serie


def inmag(fecha) -> float | None:
    fs, vs = _inmag_serie()
    k = bisect.bisect_right(fs, str(fecha)[:10]) - 1
    return vs[k] if k >= 0 else None


def coeficientes_desde_ventas(ratios: dict[int, list[float]], cats: dict) -> dict[int, float]:
    """Función pura. ratios: {categoría: [$/kg ÷ INMAG]}; cats: {id: {sexo, orden}}."""
    base = {c: statistics.median(v) for c, v in ratios.items() if len(v) >= MIN_VENTAS}
    out = {}
    for i, c in cats.items():
        if i in base:
            out[i] = base[i]
            continue
        mismos = sorted((j for j in base if cats[j]["sexo"] == c["sexo"]),
                        key=lambda j: (cats[j]["orden"] > c["orden"], abs(cats[j]["orden"] - c["orden"])))
        out[i] = base[mismos[0]] if mismos else 1.0
    return out


def coeficientes() -> dict[int, float]:
    from src.db.connection import fetch_all
    from src.features.ganaderia import categorias, stock

    c = _cache.get("coef")
    if c and time.time() - c[0] < 3600:
        return c[1]
    ct = stock.categoria_de_tipo_hacienda()
    ratios = defaultdict(list)
    for r in fetch_all(
            "SELECT v.Fecha f, d.IdTipoProducto t, d.Cantidad c, d.[Unidad de medida] u, d.[Peso Total] p, "
            "ISNULL(d.[Precio unitario (A)],0) + ISNULL(d.[Precio unitario (B)],0) pr "
            "FROM dbo.[Det_Ventas Hacienda] d JOIN dbo.[Venta Hacienda] v ON v.IdVenta = d.IdVenta "
            "JOIN dbo.[Tipo Documento] td ON td.IdTipoDocumento = v.IdTipoDocumento "
            "WHERE td.[Tipo Documento] NOT LIKE 'Nota de%' AND v.Fecha >= '2016-01-01'"):
        x = categorias.cabezas_y_kg(r["c"], r["u"], r["p"], None)
        cat = ct.get(r["t"])
        if not cat or not x["esHacienda"] or x["kgEstimado"] or not x["kg"] or x["kg"] <= 0:
            continue
        imp, i = float(r["c"] or 0) * float(r["pr"] or 0), inmag(r["f"])
        if imp > 0 and i:
            ratios[cat].append(imp / x["kg"] / i)
    cats = {r["i"]: r for r in fetch_all("SELECT IdCategoria i, Sexo sexo, Orden orden FROM dbo.GanCategoria")}
    out = coeficientes_desde_ventas(ratios, cats)
    _cache["coef"] = (time.time(), out)
    return out


def reglas() -> dict[int, dict]:
    from src.db.connection import fetch_all

    return {r["c"]: r for r in fetch_all("SELECT IdCategoria c, KgValuacion kg, CoefFijo coef, Motivo motivo "
                                        "FROM dbo.GanValuacionRegla")}


def valuar(filas_stock: list[dict], indice: float, coef: dict, regla: dict, pct_gastos: float) -> dict:
    """Función pura. filas_stock: [{idCategoria, categoria, cabezas, kg, ev}] (kg de la existencia)."""
    items, total, kg_tot, ev_tot = [], 0.0, 0.0, 0.0
    for f in filas_stock:
        if f["cabezas"] <= 0:
            continue
        rg = regla.get(f["idCategoria"]) or {}
        kg_cab = float(rg["kg"]) if rg.get("kg") else (f["kg"] / f["cabezas"] if f["cabezas"] else 0)
        k = float(rg["coef"]) if rg.get("coef") else coef.get(f["idCategoria"], 1.0)
        precio = indice * k
        valor = f["cabezas"] * kg_cab * precio * (1 - pct_gastos)
        items.append({"categoria": f["categoria"], "cabezas": f["cabezas"], "kgCabeza": round(kg_cab, 1),
                      "precioKg": round(precio, 2), "coeficiente": round(k, 3), "valor": round(valor, 2),
                      "regla": rg.get("motivo")})
        total += valor
        kg_tot += f["kg"]
        ev_tot += f.get("ev") or 0
    return {"valor": round(total, 2), "kg": round(kg_tot, 1), "ev": round(ev_tot, 1), "items": items}


def valuacion_movimiento(m: dict, pct_gastos: float) -> dict | None:
    """Valúa las cabezas de un movimiento (traslado) igual que el inventario: kg de categoría × INMAG × coeficiente."""
    from src.features.ganaderia import stock

    i = inmag(m["fecha"])
    c = stock._catalogos()[0].get(m["categoria"])
    if not i or not c:
        return None
    kg = float(m["kg"]) if m.get("kg") else int(m["cabezas"]) * float(c["peso"] or 0)
    fila = {"idCategoria": m["categoria"], "categoria": c["nombre"], "cabezas": int(m["cabezas"]), "kg": kg}
    r = valuar([fila], i, coeficientes(), reglas(), pct_gastos)
    return {**r["items"][0], "kg": r["kg"]} if r["items"] else None


def valuacion(fecha: date, establecimiento: int | None, pct_gastos: float) -> dict | None:
    """None si no hay recuento base a esa fecha (stock desconocido)."""
    from src.features.ganaderia import stock

    st = stock.stock(fecha, establecimiento, "propia")
    if not st["bases"]:
        return None
    i = inmag(fecha)
    if not i:
        return None
    r = valuar(st["categorias"], i, coeficientes(), reglas(), pct_gastos)
    return {**r, "fecha": fecha.isoformat(), "inmag": i, "pctGastos": round(pct_gastos, 4)}
