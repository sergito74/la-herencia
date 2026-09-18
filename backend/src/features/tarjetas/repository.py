"""Catálogo de tarjetas y cuenta corriente por tarjeta — 008-tarjetas.

La cuenta corriente de una tarjeta se construye exclusivamente a partir
del total calculado de sus resúmenes (`Tarjetas_Resumenes`), nunca de las
cuotas de compras en cuotas — decisión de producto documentada en
`specs/008-tarjetas/research.md` §3 para evitar contar la misma deuda dos
veces (una cuota de compra en cuotas termina reflejada dentro del resumen
del período que la paga).
"""

from __future__ import annotations

from itertools import combinations

from src.db.connection import fetch_all, fetch_one
from src.features.tarjetas_resumenes.repository import (
    TOLERANCIA_CONCILIACION,
    calcular_total,
    get_lineas,
    get_pagos,
    get_resumen_detalle,
    registrar_pago,
)


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
    """Movimientos de cuenta corriente de la tarjeta: un movimiento de
    deuda por resumen (`Origen='Resumen'`) más un movimiento de crédito
    por cada pago registrado contra un resumen (`Origen='Pago'`, punto 6
    del feedback del usuario, 2026-09-19 — antes solo se mostraba la
    deuda). Las cuotas de compras en cuotas no generan movimiento propio
    (research.md §3)."""
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
    eventos: list[dict] = []
    for resumen in resumenes:
        lineas = get_lineas(resumen["idResumen"])
        total = calcular_total(resumen, lineas)
        pagos = fetch_all(
            "SELECT IdPago AS idPago, Fecha AS fecha, Importe AS importe "
            "FROM dbo.Tarjetas_Resumenes_Pagos WHERE IdResumen = ?",
            (resumen["idResumen"],),
        )
        pagado = sum(float(p["importe"]) for p in pagos)
        diferencia_redondeo = round(total - pagado, 2)
        lineas_vinculadas = sum(1 for l in lineas if l.get("comprasVinculadas"))
        # Estado de conciliación por resumen — para que la cuenta corriente
        # de la tarjeta lo muestre de un vistazo, sin entrar resumen por
        # resumen (feedback 2026-09-21). Tolerancia de redondeo justificada
        # en `TOLERANCIA_CONCILIACION` (análisis del especialista
        # financiero contra los 293 resúmenes reales) — la diferencia nunca
        # se oculta, se expone en `diferenciaRedondeo` con signo.
        eventos.append(
            {
                "idResumen": resumen["idResumen"],
                "fecha": resumen["fecha"],
                "codigo": resumen["codigo"],
                "origen": "Resumen",
                "deuda": total if total > 0 else 0.0,
                "credito": -total if total < 0 else 0.0,
                "pagoConciliado": diferencia_redondeo <= TOLERANCIA_CONCILIACION,
                "diferenciaRedondeo": diferencia_redondeo,
                "lineasTotal": len(lineas),
                "lineasVinculadas": lineas_vinculadas,
            }
        )
        for pago in pagos:
            eventos.append(
                {
                    "idResumen": resumen["idResumen"],
                    "fecha": pago["fecha"],
                    "codigo": resumen["codigo"],
                    "origen": "Pago",
                    "deuda": 0.0,
                    "credito": float(pago["importe"]),
                    "pagoConciliado": None,
                    "diferenciaRedondeo": None,
                    "lineasTotal": None,
                    "lineasVinculadas": None,
                }
            )

    eventos.sort(key=lambda e: (e["fecha"], e["origen"] == "Pago", e["idResumen"]))
    saldo = 0.0
    movimientos: list[dict] = []
    for evento in eventos:
        saldo += evento["deuda"] - evento["credito"]
        movimientos.append({**evento, "saldoAcumulado": saldo})
    return movimientos


def get_id_contacto_tarjeta(id_tarjeta: int) -> int | None:
    """Vínculo por coincidencia de nombre (research.md §3, sin FK real):
    `Tarjetas.TarjetaNombre` = `Contactos.[Razon Social]` con
    `Tipo Contacto = 'Tarjeta de Credito'`."""
    tarjeta = get_tarjeta(id_tarjeta)
    if tarjeta is None:
        return None
    row = fetch_one(
        "SELECT IdContacto FROM dbo.Contactos WHERE [Tipo Contacto] = 'Tarjeta de Credito' AND [Razon Social] = ?",
        (tarjeta["nombre"],),
    )
    return row["IdContacto"] if row else None


def get_pagos_candidatos(id_tarjeta: int) -> list[dict]:
    """Movimientos bancarios reales (`Movimientos BNA`/`Movimientos
    Galicia`) con `IdContacto` apuntando a esta tarjeta — ya vienen
    cargados así en los datos reales (no es un match por fecha/importe).
    Excluye los que ya están vinculados a un pago existente (punto 6 del
    feedback del usuario, 2026-09-19)."""
    tarjeta = get_tarjeta(id_tarjeta)
    id_contacto = get_id_contacto_tarjeta(id_tarjeta)
    if tarjeta is None or id_contacto is None:
        return []

    ya_vinculados = {
        row["idMovimientoOrigen"]
        for row in fetch_all(
            "SELECT IdMovimientoOrigen AS idMovimientoOrigen FROM dbo.Tarjetas_Resumenes_Pagos "
            "WHERE Origen = ? AND IdMovimientoOrigen IS NOT NULL",
            (tarjeta["banco"] == "Banco Nacion" and "BNA" or "Galicia",),
        )
    }

    candidatos: list[dict] = []
    if tarjeta["banco"] == "Banco Nacion":
        rows = fetch_all(
            "SELECT IdMovimientoBNA AS idMovimiento, [Fecha / Hora Mov#] AS fecha, "
            "Importe AS importe, Concepto AS concepto "
            "FROM dbo.[Movimientos BNA] WHERE IdContacto = ? AND Importe < 0 "
            "ORDER BY [Fecha / Hora Mov#] DESC",
            (id_contacto,),
        )
        for row in rows:
            if row["idMovimiento"] in ya_vinculados:
                continue
            candidatos.append(
                {
                    "origen": "BNA",
                    "idMovimiento": row["idMovimiento"],
                    "fecha": row["fecha"],
                    "importe": abs(float(row["importe"])),
                    "concepto": row["concepto"],
                }
            )
    elif tarjeta["banco"] == "Banco Galicia":
        rows = fetch_all(
            "SELECT IdMovimiento AS idMovimiento, Fecha AS fecha, "
            "Débitos AS importe, Concepto AS concepto "
            "FROM dbo.[Movimientos Galicia] WHERE IdContacto = ? AND Débitos > 0 "
            "ORDER BY Fecha DESC",
            (id_contacto,),
        )
        for row in rows:
            if row["idMovimiento"] in ya_vinculados:
                continue
            candidatos.append(
                {
                    "origen": "Galicia",
                    "idMovimiento": row["idMovimiento"],
                    "fecha": row["fecha"],
                    "importe": float(row["importe"]),
                    "concepto": row["concepto"],
                }
            )
    return candidatos


def auto_vincular_pago(id_resumen: int) -> bool:
    """Busca activamente si el pago de este resumen ya está en los
    movimientos bancarios reales, y lo vincula solo si encuentra una
    coincidencia exacta e inequívoca — el usuario no tiene que buscar
    nada (feedback 2026-09-19, punto 6). No reintenta si el resumen ya
    tiene algún pago registrado (evita duplicar).

    Dos patrones confirmados contra datos reales (research):
    1. Un solo movimiento por el importe exacto del resumen.
    2. Dos movimientos el mismo día que suman el importe exacto (ej.
       Visa Galicia separa "Total Consumos" del resto de los cargos en
       dos débitos distintos, mismo día).
    Ventana de ±20 días alrededor de la fecha de vencimiento — igual
    criterio que se usó para medir la tasa de coincidencia real (63,5%
    de los 293 resúmenes reales) antes de implementar esto."""
    if get_pagos(id_resumen):
        return False

    resumen = fetch_one("SELECT IdTarjeta, FechaVencimiento FROM dbo.Tarjetas_Resumenes WHERE IdResumen = ?", (id_resumen,))
    if resumen is None or resumen["FechaVencimiento"] is None:
        return False

    cabecera = get_resumen_detalle(id_resumen)
    lineas = get_lineas(id_resumen)
    total = round(calcular_total(cabecera, lineas), 2)
    vto = resumen["FechaVencimiento"]

    candidatos = get_pagos_candidatos(resumen["IdTarjeta"])
    ventana = [c for c in candidatos if abs((c["fecha"] - vto).days) <= 20]

    for c in ventana:
        if abs(c["importe"] - total) < 0.02:
            registrar_pago(id_resumen, c["fecha"], c["importe"], c["origen"], c["idMovimiento"])
            return True

    por_fecha: dict = {}
    for c in ventana:
        por_fecha.setdefault(c["fecha"], []).append(c)
    for candidatos_del_dia in por_fecha.values():
        if len(candidatos_del_dia) < 2:
            continue
        for a, b in combinations(candidatos_del_dia, 2):
            if abs(a["importe"] + b["importe"] - total) < 0.02:
                registrar_pago(id_resumen, a["fecha"], a["importe"], a["origen"], a["idMovimiento"])
                registrar_pago(id_resumen, b["fecha"], b["importe"], b["origen"], b["idMovimiento"])
                return True

    return False
