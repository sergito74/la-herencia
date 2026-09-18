"""Catálogo de tarjetas y cuenta corriente por tarjeta — 008-tarjetas.

La cuenta corriente de una tarjeta se construye exclusivamente a partir
del total calculado de sus resúmenes (`Tarjetas_Resumenes`), nunca de las
cuotas de compras en cuotas — decisión de producto documentada en
`specs/008-tarjetas/research.md` §3 para evitar contar la misma deuda dos
veces (una cuota de compra en cuotas termina reflejada dentro del resumen
del período que la paga).
"""

from __future__ import annotations

from src.db.connection import fetch_all
from src.features.tarjetas_resumenes.repository import calcular_total, get_lineas


def get_tarjetas(solo_activas: bool = False) -> list[dict]:
    sql = (
        "SELECT IdTarjeta AS idTarjeta, TarjetaNombre AS nombre, Banco AS banco, Activa AS activa "
        "FROM dbo.Tarjetas"
    )
    if solo_activas:
        sql += " WHERE Activa = 1"
    sql += " ORDER BY TarjetaNombre"
    return fetch_all(sql)


def get_tarjeta(id_tarjeta: int) -> dict | None:
    rows = fetch_all(
        "SELECT IdTarjeta AS idTarjeta, TarjetaNombre AS nombre, Banco AS banco, Activa AS activa "
        "FROM dbo.Tarjetas WHERE IdTarjeta = ?",
        (id_tarjeta,),
    )
    return rows[0] if rows else None


def get_movimientos(id_tarjeta: int) -> list[dict]:
    """Un movimiento por resumen de la tarjeta, ordenado cronológicamente,
    con saldo acumulado (data-model.md, sección "Movimiento de Cuenta
    Corriente de Tarjeta"). Las cuotas de compras en cuotas no generan
    movimiento propio (research.md §3)."""
    resumenes = fetch_all(
        "SELECT IdResumen AS idResumen, FechaCierre AS fecha, ResumenCodigo AS codigo, "
        "ImpuestoSellos AS impuestoSellos, GastosAdmin AS gastosAdmin, MantCuenta AS mantCuenta, "
        "RenovAnual AS renovAnual, PromocionBNA AS promocionBNA, CreditoContingente AS creditoContingente, "
        "IntFinanc AS intFinanc, IntCompens AS intCompens, IVA105 AS iva105, PercepIVA105 AS percepIVA105, "
        "IVA21 AS iva21, PercepIVA21 AS percepIVA21, PercepIIBB AS percepIIBB, "
        "AjusteResAnterior AS ajusteResAnterior "
        "FROM dbo.Tarjetas_Resumenes WHERE IdTarjeta = ? ORDER BY FechaCierre ASC, IdResumen ASC",
        (id_tarjeta,),
    )
    saldo = 0.0
    movimientos: list[dict] = []
    for resumen in resumenes:
        lineas = get_lineas(resumen["idResumen"])
        total = calcular_total(resumen, lineas)
        deuda = total if total > 0 else 0.0
        credito = -total if total < 0 else 0.0
        saldo += deuda - credito
        movimientos.append(
            {
                "idResumen": resumen["idResumen"],
                "fecha": resumen["fecha"],
                "codigo": resumen["codigo"],
                "deuda": deuda,
                "credito": credito,
                "saldoAcumulado": saldo,
            }
        )
    return movimientos
