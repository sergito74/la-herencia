"""Calendario agrícola real (confirmado por el usuario, 2026-09-24) — usado
para que el motor de imputación no atribuya con confianza un costo a un
binomio Cultivo/Campaña que agronómicamente no pudo haber empezado todavía.

Meses aproximados de inicio/fin de cada cultivo, con `margen_previo_meses`
para tolerar labores previas reales (barbecho químico, aplicación de
herbicida antes de sembrar) — confirmado con el usuario: el caso real de
Soja primera (orden ejecutada 2026-09-19, ~2 meses antes de la siembra de
noviembre) es un gasto real de esa campaña, no un error de carga, y el
barbecho químico puede arrancar hasta 4 meses antes de la siembra
(confirmado 2026-09-24 tras encontrar casos reales de julio para cultivos
que siembran en septiembre/noviembre — Sorgo, Maíz, Maíz diferido).

`margen_posterior_meses` tolera labores DESPUÉS del fin teórico (fertilización,
mantenimiento) en los cultivos forrajeros que "se consumen con la hacienda"
(Avena, Sorgo, Maíz diferido) — confirmado con el usuario 2026-09-24: no hay
una regla que limite una Orden a un único cultivo ni que corte el mantenimiento
justo en el mes de fin teórico de cosecha/consumo.

`Sin Cultivo` no tiene calendario propio a propósito: esas Órdenes ya se
imputan a Centro de Costos "Adm. General" sin pasar por esta validación
(FR-005, motor.py).
"""

from __future__ import annotations

from datetime import date

CALENDARIO = {
    "Trigo": {"inicio_mes": 6, "fin_mes": 1, "margen_previo_meses": 4},
    "Soja primera": {"inicio_mes": 11, "fin_mes": 5, "margen_previo_meses": 4},
    "Soja segunda": {"inicio_mes": 12, "fin_mes": 5, "margen_previo_meses": 4},
    "Maiz": {"inicio_mes": 9, "fin_mes": 5, "margen_previo_meses": 4},
    "Girasol": {"inicio_mes": 9, "fin_mes": 4, "margen_previo_meses": 4},
    # Sorgo/Maíz diferido/Avena: forrajeros "que se consumen con la hacienda"
    # (pastoreo directo) — el fin teórico es aproximado, el pastoreo y el
    # mantenimiento posterior (fertilización) no tienen un corte estricto.
    "Sorgo": {"inicio_mes": 11, "fin_mes": 3, "margen_previo_meses": 4, "margen_posterior_meses": 4},
    "Maiz diferido": {"inicio_mes": 11, "fin_mes": 6, "margen_previo_meses": 4, "margen_posterior_meses": 4},
    "Avena": {"inicio_mes": 3, "fin_mes": 11, "margen_previo_meses": 4, "margen_posterior_meses": 4},
    # Pastura: multi-año (4-5 temporadas), sin mes de fin fijo. Margen previo
    # más amplio que los anuales: la preparación de suelo para implantar una
    # pastura (laboreo, fertilización) arranca meses antes que un cultivo
    # anual — confirmado con datos reales (órdenes de sept. para pastura
    # implantada en feb/marzo siguiente, 2026-09-24).
    "Pastura": {"inicio_mes": 2, "fin_mes": None, "margen_previo_meses": 7, "duracion_anios": 5},
}


def _anio_inicio_campania(campania: str | None) -> int | None:
    """`'2026/2027'` → 2026, `'2026'` → 2026, `'No Aplica'`/`None` → `None`."""
    if not campania or campania == "No Aplica":
        return None
    try:
        return int(campania[:4])
    except ValueError:
        return None


def es_fecha_plausible(cultivo: str | None, campania: str | None, fecha: date | None) -> bool | None:
    """`True`/`False` si se pudo evaluar contra el calendario; `None` si el
    cultivo o la campaña no están en `CALENDARIO` (deja pasar sin bloquear
    — evita falsos positivos con datos que no conocemos)."""
    if fecha is None:
        return None
    ventana = CALENDARIO.get(cultivo or "")
    anio = _anio_inicio_campania(campania)
    if ventana is None or anio is None:
        return None

    inicio_mes = ventana["inicio_mes"] - ventana["margen_previo_meses"]
    anio_inicio_real = anio
    if inicio_mes <= 0:
        inicio_mes += 12
        anio_inicio_real -= 1
    inicio = date(anio_inicio_real, inicio_mes, 1)

    fin_mes = ventana["fin_mes"]
    if fin_mes is None:
        fin = date(anio + ventana.get("duracion_anios", 5), 12, 31)
    else:
        fin_mes_con_margen = fin_mes + ventana.get("margen_posterior_meses", 0)
        anio_fin = anio + 1 if fin_mes < ventana["inicio_mes"] else anio
        anio_fin += (fin_mes_con_margen - 1) // 12
        mes_siguiente = (fin_mes_con_margen - 1) % 12 + 2
        anio_fin_ajustado = anio_fin + 1 if mes_siguiente > 12 else anio_fin
        mes_siguiente = 1 if mes_siguiente > 12 else mes_siguiente
        fin = date(anio_fin_ajustado, mes_siguiente, 1)

    return inicio <= fecha < fin
