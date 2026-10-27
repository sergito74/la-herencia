"""Planificador de corridas de la bóveda (042, FR-012/013, research.md R3).

Corre dentro del backend, solo mientras la aplicación está abierta
(Clarification 27/10: no hay tareas de Windows). Un hilo revisa cada
`INTERVALO` segundos qué portales vencieron y los corre de a uno. La próxima
corrida se calcula **desde ahora**, no desde la hora perdida: si la app estuvo
cerrada varios períodos, al abrirla corre una sola vez (recuperación única).
"""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime, time, timedelta

log = logging.getLogger(__name__)
INTERVALO = 60
_arrancado = threading.Event()


def proxima_corrida(frecuencia: str, dia_semana: int | None, dia_mes: int | None, hora: time,
                    desde: datetime) -> datetime | None:
    """Primer momento programado estrictamente posterior a `desde`.

    `dia_semana`: 1 = lunes … 7 = domingo. `dia_mes`: 1–28 (todos los meses lo tienen)."""
    if frecuencia == "desactivada":
        return None
    if frecuencia == "diaria":
        candidato = datetime.combine(desde.date(), hora)
        return candidato if candidato > desde else candidato + timedelta(days=1)
    if frecuencia == "semanal":
        if not dia_semana or not 1 <= dia_semana <= 7:
            raise ValueError("La frecuencia semanal necesita el día de la semana (1 a 7)")
        dias = (dia_semana - 1 - desde.weekday()) % 7
        candidato = datetime.combine(desde.date() + timedelta(days=dias), hora)
        return candidato if candidato > desde else candidato + timedelta(days=7)
    if frecuencia == "mensual":
        if not dia_mes or not 1 <= dia_mes <= 28:
            raise ValueError("La frecuencia mensual necesita el día del mes (1 a 28)")
        candidato = datetime.combine(date(desde.year, desde.month, dia_mes), hora)
        if candidato > desde:
            return candidato
        anio, mes = (desde.year + 1, 1) if desde.month == 12 else (desde.year, desde.month + 1)
        return datetime.combine(date(anio, mes, dia_mes), hora)
    raise ValueError(f"Frecuencia desconocida: {frecuencia}")


def _hora(valor) -> time:
    if isinstance(valor, time):
        return valor
    return time.fromisoformat(str(valor)[:8])


def reprogramar(id_portal: int, desde: datetime | None = None) -> datetime | None:
    from src.features.boveda import repository

    prog = repository.obtener_programacion(id_portal)
    if not prog:
        return None
    proxima = proxima_corrida(prog["frecuencia"], prog["diaSemana"], prog["diaMes"], _hora(prog["hora"]),
                              desde or datetime.now())
    repository.fijar_proxima(id_portal, proxima)
    return proxima


def tick(ahora: datetime | None = None) -> list[int]:
    """Corre en serie los portales vencidos. Devuelve los ids corridos."""
    from src.features.boveda import repository, servicio

    corridos = []
    for p in repository.portales_vencidos(ahora or datetime.now()):
        estado = None
        try:
            _, estado = servicio.correr_portal(p["idPortal"], "programada", "sistema")
        except Exception:
            log.exception("Bóveda: falló la corrida programada del portal %s", p["idPortal"])
        finally:
            # Desde ahora: recuperación única aunque se hayan perdido varios períodos. Si se salteó por
            # una corrida manual en curso, queda vencida y se reintenta en el próximo tick.
            if estado != "salteada":
                reprogramar(p["idPortal"])
            corridos.append(p["idPortal"])
    return corridos


def _bucle() -> None:
    pausa = threading.Event()
    while True:
        try:
            tick()
        except Exception:
            log.exception("Bóveda: falló la revisión de corridas programadas")
        pausa.wait(INTERVALO)


def arrancar() -> None:
    """Inicia el hilo una sola vez por proceso (evento `startup` del backend)."""
    if _arrancado.is_set():
        return
    _arrancado.set()
    threading.Thread(target=_bucle, daemon=True, name="boveda-planificador").start()
