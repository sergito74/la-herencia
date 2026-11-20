"""20/11/2026 (Sergio): grano cosechado y no liquidado sin ventas propias en la campaña (p. ej. todo consumido por la
hacienda) se valoriza a PRECIO DE MERCADO MENOS GASTOS DE COMERCIALIZACIÓN.

- Precio de mercado: pizarra de la Cámara Arbitral de Cereales de Rosario (BCR), pública, $/tn del día (si no hubo
  pizarra, el estimativo). Se guarda en dbo.PreciosPizarraRosario; lo que falta se baja solo de cac.bcr.com.ar.
- A dólares: BNA comprador divisa del día hábil anterior (misma regla que las liquidaciones de granos).
- Gastos de comercialización: % histórico de deducciones/gastos sobre ventas de ese grano en las liquidaciones propias
  (todas las campañas); sin historia del grano, el de todos los granos.
"""

from __future__ import annotations

import html
import logging
import re
import urllib.request
from datetime import date, timedelta

from src.db.connection import execute_write, fetch_all, fetch_one

log = logging.getLogger(__name__)

# Cultivo del sistema -> producto de la CAC Rosario
PRODUCTO_CAC = {"Trigo": 8, "Maiz": 3, "Maiz diferido": 3, "Girasol": 9, "Soja primera": 13, "Soja segunda": 13, "Sorgo": 6}
# Cultivos que comparten grano para el % de gastos de comercialización
_GRUPO = {"Maiz diferido": "Maiz", "Soja segunda": "Soja primera"}
_URL = "https://www.cac.bcr.com.ar/es/precios-de-pizarra/consultas?product={p}&type=any&date_start={d}&date_end={h}"
_VENTANA = 10  # días hacia atrás para encontrar la última pizarra


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def _bajar(producto: int, desde: date, hasta: date) -> int:
    req = urllib.request.Request(_URL.format(p=producto, d=desde.isoformat(), h=hasta.isoformat()),
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        texto = html.unescape(re.sub(r"<[^>]+>", " ", r.read().decode("utf-8", "ignore")))
    n = 0
    for dd, mm, aa, precio in re.findall(r"(\d{2})/(\d{2})/(\d{4})\s+(?:\(E\)\s*)?\$\s*([\d.]+,\d{2})", texto):
        valor = float(precio.replace(".", "").replace(",", "."))
        fecha = date(int(aa), int(mm), int(dd))
        if valor > 0 and not fetch_one("SELECT 1 AS x FROM dbo.PreciosPizarraRosario WHERE Producto = ? AND Fecha = ?", (producto, fecha)):
            execute_write("INSERT INTO dbo.PreciosPizarraRosario (Producto, Fecha, PrecioPesosTn) VALUES (?, ?, ?)", (producto, fecha, valor))
            n += 1
    return n


def pizarra(producto: int, fecha: date) -> dict | None:
    """Última pizarra Rosario en los 10 días anteriores o iguales a `fecha`; si falta, la baja de la CAC."""
    sql = ("SELECT TOP 1 Fecha AS fecha, PrecioPesosTn AS pesos FROM dbo.PreciosPizarraRosario "
           "WHERE Producto = ? AND Fecha BETWEEN ? AND ? ORDER BY Fecha DESC")
    desde = fecha - timedelta(days=_VENTANA)
    fila = fetch_one(sql, (producto, desde, fecha))
    if fila is None:
        try:
            _bajar(producto, desde, fecha)
        except Exception as exc:  # sin internet / CAC caída: se avisa en pantalla, no se inventa precio
            log.warning("No se pudo bajar la pizarra Rosario %s %s: %s", producto, fecha, exc)
            return None
        fila = fetch_one(sql, (producto, desde, fecha))
    return {"fecha": fila["fecha"], "pesos": _f(fila["pesos"])} if fila else None


def _bna_dia_habil_anterior(fecha: date) -> float | None:
    f = fetch_one("SELECT TOP 1 Comp_Divisa AS tc FROM dbo.[Dolar BNA] WHERE Fecha < ? AND Comp_Divisa > 0 ORDER BY Fecha DESC", (fecha,))
    return _f(f["tc"]) if f else None


def porcentaje_gastos_comercializacion(cultivo: str) -> dict:
    """Deducciones de las liquidaciones propias / ventas, en dólares, de todas las campañas del grano."""
    base = _GRUPO.get(cultivo, cultivo)
    nombres = [c for c, g in [(k, _GRUPO.get(k, k)) for k in PRODUCTO_CAC] if g == base] or [cultivo]
    marcas = ",".join("?" * len(nombres))
    v = fetch_one(f"SELECT SUM(v.VentaDolares) AS v FROM dbo.vw_ResultadosCultivo_Ventas v JOIN dbo.Cultivos c ON c.IdCultivo = v.IdCultivo "
                  f"WHERE c.Cultivo IN ({marcas})", tuple(nombres)) or {}
    d = fetch_one(f"SELECT SUM(x.Dolares) AS d FROM dbo.vw_ResultadosCultivo_Deducciones x JOIN dbo.Cultivos c ON c.IdCultivo = x.IdCultivo "
                  f"WHERE c.Cultivo IN ({marcas})", tuple(nombres)) or {}
    if _f(v.get("v")) > 0 and _f(d.get("d")) > 0:  # sin deducciones registradas no es una historia representativa
        return {"porcentaje": round(_f(d.get("d")) / _f(v["v"]), 4), "base": base}
    v = fetch_one("SELECT SUM(VentaDolares) AS v FROM dbo.vw_ResultadosCultivo_Ventas") or {}
    d = fetch_one("SELECT SUM(Dolares) AS d FROM dbo.vw_ResultadosCultivo_Deducciones") or {}
    return {"porcentaje": round(_f(d.get("d")) / _f(v.get("v")), 4) if _f(v.get("v")) else 0.0, "base": "todos los granos"}


def precio_neto_mercado(cultivo: str, fecha: date) -> dict | None:
    """Precio neto por tn (pesos y dólares) = pizarra Rosario × (1 − % gastos de comercialización)."""
    producto = PRODUCTO_CAC.get(cultivo)
    if producto is None:
        return None
    p = pizarra(producto, fecha)
    if p is None:
        return None
    tc = _bna_dia_habil_anterior(p["fecha"])
    if not tc:
        return None
    g = porcentaje_gastos_comercializacion(cultivo)
    neto = 1 - g["porcentaje"]
    return {
        "fechaPizarra": p["fecha"], "pizarraPesosTn": p["pesos"], "tc": tc,
        "pizarraDolaresTn": round(p["pesos"] / tc, 2),
        "gastosComercializacion": g["porcentaje"], "gastosBase": g["base"],
        "netoPesosTn": round(p["pesos"] * neto, 2), "netoDolaresTn": round(p["pesos"] / tc * neto, 2),
    }
