"""Generador de cronograma de cuotas (FR-005, 008-tarjetas).

Fórmula confirmada contra `data-model.md`: financiación sin interés,
cuota fija con ajuste de redondeo en la última. No reproduce el patrón
de cuotas crecientes que existe en el histórico real de compras cargadas
con interés bancario (research.md §2) — esas 18 compras históricas solo
se leen, nunca se regeneran.
"""

from __future__ import annotations

from datetime import date


def _sumar_meses(fecha: date, meses: int) -> date:
    mes_total = fecha.month - 1 + meses
    anio = fecha.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = fecha.day
    # Ajusta el día si el mes destino tiene menos días (ej. 31 de enero + 1 mes).
    while True:
        try:
            return date(anio, mes, dia)
        except ValueError:
            dia -= 1


def generar_cronograma(fecha_compra: date, importe_total: float, cantidad_cuotas: int) -> list[dict]:
    """Devuelve `cantidad_cuotas` cuotas: `cuotaBase` para las primeras
    `N-1`, la última absorbe el resto de redondeo (data-model.md)."""
    cuota_base = round(importe_total / cantidad_cuotas, 2)
    cuotas: list[dict] = []
    acumulado = 0.0
    for i in range(1, cantidad_cuotas + 1):
        if i < cantidad_cuotas:
            importe = cuota_base
            acumulado += importe
        else:
            importe = round(importe_total - acumulado, 2)
        cuotas.append(
            {
                "numeroCuota": i,
                "fechaVencimiento": _sumar_meses(fecha_compra, i),
                "importe": importe,
                "cobrado": False,
            }
        )
    return cuotas
