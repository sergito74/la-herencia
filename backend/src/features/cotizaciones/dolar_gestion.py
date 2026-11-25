"""Dólar de gestión único para todos los centros de costos (052 FR-016; Sergio, 25/11/2026).

Regla:
- Comprobante en US$: su propio tipo de cambio.
- Comprobante en pesos: BNA comprador divisa del **día hábil anterior** a la fecha del comprobante
  (última cotización con Comp_Divisa > 0 estrictamente anterior). Es la convención fiscal y la que ya usaban
  granos, caja y precios de mercado.
- Comprobante que solo ajusta el tipo de cambio: 0 US$ en el costo.

Todo módulo de costo o resultado usa esta función o el fragmento SQL; no se copia la fórmula.
Las cuentas corrientes en US$ (TC del comprobante), la proyección del flujo (vendedor) y la valuación de
socios (billete) tienen otra función y no usan esto (ver specs/052-modulo-ganadero/auditoria-dolar-20261125.md).
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import fetch_one

FUENTE = "BNA comprador divisa, día hábil anterior"


def sql_tc_pesos(fecha_sql: str) -> str:
    """Subconsulta SQL con el TC de gestión para una expresión de fecha (columna o parámetro)."""
    return (f"(SELECT TOP 1 _b.Comp_Divisa FROM dbo.[Dolar BNA] _b WHERE _b.Fecha < CAST({fecha_sql} AS date) "
            "AND _b.Comp_Divisa > 0 ORDER BY _b.Fecha DESC)")


def tc_pesos(fecha: date | datetime | None) -> float | None:
    if fecha is None:
        return None
    f = fetch_one("SELECT TOP 1 Comp_Divisa AS tc FROM dbo.[Dolar BNA] WHERE Fecha < CAST(? AS date) AND Comp_Divisa > 0 "
                  "ORDER BY Fecha DESC", (fecha,))
    return float(f["tc"]) if f and f["tc"] else None


def fecha_tc(fecha: date | datetime | None):
    """Fecha de la cotización usada (para mostrar la fuente)."""
    if fecha is None:
        return None
    f = fetch_one("SELECT TOP 1 CONVERT(date, Fecha) AS f FROM dbo.[Dolar BNA] WHERE Fecha < CAST(? AS date) "
                  "AND Comp_Divisa > 0 ORDER BY Fecha DESC", (fecha,))
    return f["f"] if f else None


def usd(importe_pesos: float | None, fecha, moneda: str | None = None, tc_comprobante: float | None = None,
        ajusta_tc: bool = False, tc_pesos_fn=tc_pesos) -> float | None:
    """US$ de gestión de un importe en pesos. `tc_pesos_fn` es inyectable para las pruebas."""
    if importe_pesos is None:
        return None
    if ajusta_tc:
        return 0.0
    if moneda == "Dolares":
        return round(importe_pesos / tc_comprobante, 2) if tc_comprobante else None
    tc = tc_pesos_fn(fecha)
    return round(importe_pesos / tc, 2) if tc else None


_SERIE: dict = {"cargada": 0.0, "fechas": [], "valores": []}


def tc_pesos_cache(fecha) -> float | None:
    """Igual que `tc_pesos` pero con la serie en memoria (10 minutos): para cálculos con miles de renglones."""
    import bisect
    import time

    from src.db.connection import fetch_all

    if fecha is None:
        return None
    if time.time() - _SERIE["cargada"] > 600:
        filas = fetch_all("SELECT CONVERT(date, Fecha) AS f, Comp_Divisa AS c FROM dbo.[Dolar BNA] "
                          "WHERE Comp_Divisa > 0 ORDER BY Fecha")
        _SERIE.update(cargada=time.time(), fechas=[str(r["f"])[:10] for r in filas], valores=[float(r["c"]) for r in filas])
    i = bisect.bisect_left(_SERIE["fechas"], str(fecha)[:10]) - 1  # estrictamente anterior
    return _SERIE["valores"][i] if i >= 0 else None
