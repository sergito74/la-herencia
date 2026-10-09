"""Caché en memoria de los contextos de todas las cuentas — 036.

Calcular las 518 cuentas lleva unos 8 segundos; las colas, el tablero y los lotes comparten el resultado. Cualquier cambio hecho desde esta
feature (ficha, marcas, saldos externos, lotes) lo invalida; lo demás se ve a los pocos minutos o con `refrescar`.
"""

from __future__ import annotations

import time
from datetime import date

TTL_SEGUNDOS = 180
_CACHE: dict = {"corte": None, "t": 0.0, "v": None}


def invalidar() -> None:
    _CACHE["v"] = None


def contextos(corte: date, cargar, refrescar: bool = False) -> dict[int, dict]:
    """Contextos de todas las cuentas al corte; `cargar(corte)` los calcula cuando no están en la caché."""
    if refrescar or _CACHE["v"] is None or _CACHE["corte"] != corte or time.time() - _CACHE["t"] > TTL_SEGUNDOS:
        _CACHE.update(v=cargar(corte), corte=corte, t=time.time())
    return _CACHE["v"]
