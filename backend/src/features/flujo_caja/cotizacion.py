"""Cotización BNA vendedor divisa del día, para convertir movimientos a USD (030).

Fuente: `dbo.[Dolar BNA]` (serie cargada a mano desde "Parametros
financieros.xlsx"; la tabla `cotizacion_bna` existe pero está vacía). Días
sin cotización (fines de semana, feriados) usan la anterior dentro de los 7
días; si no hay ninguna, la conversión se informa como faltante — nunca se
inventa un valor (FR-005).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from src.db.connection import fetch_all
from src.db.params import as_sql_datetime

DIAS_FALLBACK = 7


def _dia(fecha) -> date:
    return fecha.date() if isinstance(fecha, datetime) else fecha


def cargar_serie(desde: date, hasta: date) -> dict[date, float]:
    filas = fetch_all(
        "SELECT Fecha AS fecha, Vend_Divisa AS valor FROM dbo.[Dolar BNA] "
        "WHERE Fecha BETWEEN ? AND ? AND Vend_Divisa > 0",
        (as_sql_datetime(desde - timedelta(days=DIAS_FALLBACK)), as_sql_datetime(hasta)),
    )
    return {_dia(f["fecha"]): float(f["valor"]) for f in filas}


def cotizacion_del_dia(serie: dict[date, float], fecha) -> tuple[float, date] | None:
    dia = _dia(fecha)
    for atras in range(DIAS_FALLBACK + 1):
        d = dia - timedelta(days=atras)
        if d in serie:
            return serie[d], d
    return None


def ultima_fecha_serie() -> date | None:
    filas = fetch_all("SELECT MAX(Fecha) AS fecha FROM dbo.[Dolar BNA] WHERE Vend_Divisa > 0")
    return _dia(filas[0]["fecha"]) if filas and filas[0]["fecha"] else None
