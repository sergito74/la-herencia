"""Períodos del resultado ganadero (052 FR-002).

- Ejercicio contable: 1/4 → 31/3 (cierre de Giamigli). Etiqueta "2025/26" = 01/04/2025–31/03/2026.
- Campaña ganadera: 1/7 → 30/6, la de la planilla histórica de Sergio. Etiqueta "2025/26" = 01/07/2025–30/06/2026.
"""

from __future__ import annotations

from datetime import date, datetime

MES_INICIO = {"ejercicio": 4, "campania": 7}


def _d(f) -> date:
    if isinstance(f, datetime):
        return f.date()
    if isinstance(f, date):
        return f
    return datetime.strptime(str(f)[:10], "%Y-%m-%d").date()


def anio_inicio(fecha, vista: str = "ejercicio") -> int:
    f = _d(fecha)
    return f.year if f.month >= MES_INICIO[vista] else f.year - 1


def etiqueta(anio: int) -> str:
    return f"{anio}/{str(anio + 1)[-2:]}"


def de_fecha(fecha, vista: str = "ejercicio") -> str:
    return etiqueta(anio_inicio(fecha, vista))


def anio_de_etiqueta(clave: str) -> int:
    return int(str(clave)[:4])


def rango(anio: int, vista: str = "ejercicio") -> tuple[date, date]:
    m = MES_INICIO[vista]
    desde = date(anio, m, 1)
    hasta = date(anio + 1, m, 1).replace(day=1)
    from datetime import timedelta

    return desde, hasta - timedelta(days=1)


def meses(anio: int, vista: str = "ejercicio") -> list[tuple[int, int]]:
    """(año, mes) de los 12 meses del período."""
    m0 = MES_INICIO[vista]
    return [(anio + (m0 + i - 1) // 12, (m0 + i - 1) % 12 + 1) for i in range(12)]


def anio_campania_agricola(nombre: str) -> int | None:
    """'2025/2026' → 2025; '2026' → 2026 (campañas de verdeos de invierno)."""
    try:
        return int(str(nombre).strip()[:4])
    except (TypeError, ValueError):
        return None
