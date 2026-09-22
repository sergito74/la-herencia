"""Cálculo de la Campaña "actual" según la fecha de hoy (FR-001).

`Campañas` no tiene columnas de fecha (verificado contra `WC`) — se deriva del
nombre: "YYYY/YYYY+1" cubre aproximadamente julio de YYYY a junio de YYYY+1
(campaña agrícola típica); "YYYY" suelto cubre ese año calendario completo
(research.md §5). Si la fecha de hoy no cae en el rango de ninguna Campaña
(o el nombre no es parseable, ej. "No Aplica"), se cae a la Campaña más
reciente con algún dato cargado, como resguardo.
"""

from __future__ import annotations

import re
from datetime import date

from src.db.connection import fetch_all

_RE_DOBLE = re.compile(r"^(\d{4})/(\d{4})$")
_RE_SIMPLE = re.compile(r"^(\d{4})$")


def _rango(texto: str) -> tuple[date, date] | None:
    m = _RE_DOBLE.match(texto)
    if m:
        a1, a2 = int(m.group(1)), int(m.group(2))
        return date(a1, 7, 1), date(a2, 6, 30)
    m = _RE_SIMPLE.match(texto)
    if m:
        anio = int(m.group(1))
        return date(anio, 1, 1), date(anio, 12, 31)
    return None


def _hoy() -> date:
    return date.today()


def campania_actual() -> int:
    """Devuelve la Campaña "actual". Descubierto durante la implementación
    (no contemplado en research.md): una Campaña "YYYY/YYYY+1" (agrícola,
    jul-jun) y una "YYYY" suelta (calendario) pueden contener la misma fecha
    de hoy simultáneamente — ambas con datos reales (ej. "2026/2027" y
    "2026" en WC). Se prioriza el formato "YYYY/YYYY+1" (la campaña agrícola
    típica del sistema); "YYYY" solo gana si ninguna "YYYY/YYYY+1" coincide."""
    hoy = _hoy()
    campanias = fetch_all("SELECT IdCampaña AS id, Campaña AS texto FROM dbo.Campañas")
    coincidencias = [c for c in campanias if (rango := _rango(c["texto"] or "")) and rango[0] <= hoy <= rango[1]]
    if not coincidencias:
        return _campania_mas_reciente_con_datos()
    dobles = [c for c in coincidencias if _RE_DOBLE.match(c["texto"])]
    return (dobles or coincidencias)[0]["id"]


def _campania_mas_reciente_con_datos() -> int:
    fila = fetch_all(
        """
        SELECT MAX(IdCampaña) AS id FROM (
            SELECT IdCampaña FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCampaña IS NOT NULL
            UNION
            SELECT p.IdCampaña FROM dbo.PlanAgricola p
            UNION
            SELECT c.IdCampaña FROM dbo.Campañas c
            JOIN dbo.vw_ResultadosCultivo_Ventas v ON v.Campaña = c.Campaña
        ) x
        """
    )
    return fila[0]["id"]
