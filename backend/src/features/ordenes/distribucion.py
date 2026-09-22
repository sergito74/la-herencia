"""Cálculo de la cantidad total de un insumo y validación del cierre exacto.

FR-003: la cantidad total a retirar de un insumo es la suma de (dosis por
hectárea × superficie) de cada lote elegido con `aplicar=True`; el usuario
carga la dosis por hectárea, no la cantidad total.

FR-004: el total retirado debe coincidir siempre con la suma de lo repartido
entre lotes, ajustado por las devoluciones a stock. A diferencia del dato
heredado (13 de 820 renglones no cerraban), acá no se permite guardar una
diferencia sin explicar.
"""

from __future__ import annotations

EPS = 1e-4


def calcular_cantidad_total(distribuciones: list[dict]) -> float:
    """Suma dosisHa * superficie de cada distribución con aplicar=True."""
    return round(sum(float(d["dosisHa"]) * float(d["superficie"]) for d in distribuciones if d.get("aplicar", True)), 4)


def validar_cierre(cantidad_total: float, distribuciones: list[dict], devoluciones: list[float] | None = None) -> None:
    """Lanza ValueError si `cantidad_total` no cierra contra lo repartido + devuelto."""
    repartido = sum(float(d["dosisHa"]) * float(d["superficie"]) for d in distribuciones if d.get("aplicar", True))
    devuelto = sum(devoluciones or [])
    diferencia = round(float(cantidad_total) - repartido - devuelto, 4)
    if abs(diferencia) > EPS:
        raise ValueError(
            [
                f"El total del insumo ({cantidad_total:g}) no cierra contra lo repartido entre lotes "
                f"({repartido:g}) más lo devuelto ({devuelto:g}): diferencia de {diferencia:g}."
            ]
        )
