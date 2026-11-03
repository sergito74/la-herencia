"""Esperas robustas para Playwright (03/11/2026).

`networkidle` exige 500 ms sin tráfico: portales con chat, analítica o sondeos (Sancor, ARCA, Allianz) nunca llegan
y la espera de 90 s terminaba en error. Se espera `load` (obligatorio) y luego la calma de red como mejor esfuerzo.
"""

from __future__ import annotations

CALMA_MS = 15000


def calma(p, timeout: int = CALMA_MS) -> None:
    """Espera que la red se calme, sin fallar si no se calma."""
    try:
        p.wait_for_load_state("networkidle", timeout=timeout)
    except Exception as e:  # solo el timeout se tolera
        if type(e).__name__ != "TimeoutError":
            raise


def ir(p, url: str, timeout: int = 90000):
    """`goto` hasta `load` y calma de red como mejor esfuerzo."""
    r = p.goto(url, wait_until="load", timeout=timeout)
    calma(p)
    return r


def cargada(p, timeout: int = 90000) -> None:
    """Reemplazo de `wait_for_load_state("networkidle")`."""
    p.wait_for_load_state("load", timeout=timeout)
    calma(p)
