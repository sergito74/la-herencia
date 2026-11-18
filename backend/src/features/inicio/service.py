"""Inicio "Para hacer hoy" (spec 051, 18/11/2026).

Reúne en una sola lectura lo que el sistema ya calcula en cada pantalla: pendientes accionables, indicadores, flujo de
los últimos meses y campaña actual. Solo lee. Las cantidades salen de las mismas funciones que usan las pantallas de
origen (FR-002). Como algunas fuentes son lentas (facturas a pagar ~35 s, facturas esperadas ~7 s), el resumen se
calcula en segundo plano y se guarda unos minutos: la pantalla abre al instante con el último resumen y cada parte que
falla queda marcada sin tumbar el resto (FR-001, edge cases).
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, timedelta

from src.db.connection import fetch_all, fetch_one

_log = logging.getLogger(__name__)
_VIGENCIA = 10 * 60
_cache: dict = {"t": 0.0, "datos": None, "calculando": False}
_lock = threading.Lock()


def _f(v) -> float:
    return float(v or 0)


def _seguro(nombre: str, fn):
    try:
        return fn()
    except Exception:  # noqa: BLE001 — una fuente rota no tumba el Inicio
        _log.exception("Inicio: %s", nombre)
        return {"error": True}


# ------------------------------------------------------------------ pendientes

def _bancos_sin_conciliar() -> dict:
    """Movimientos de banco de los últimos 120 días que todavía no tienen contacto ni documento (sin contar impuestos y
    gastos bancarios ni inversiones, igual que los informes del Estudio)."""
    from src.features.tesoreria import listado_estudio as L
    from src.features.tesoreria import estado_resolucion

    desde = date.today() - timedelta(days=120)
    n, total = 0, 0.0
    for medio, sql in (
            ("galicia", "SELECT IdMovimiento AS id, [Descripción] AS d, ISNULL([Débitos],0)+ISNULL([Créditos],0) AS imp, IdContacto AS c "
                        "FROM dbo.[Movimientos Galicia] WHERE Fecha >= ?"),
            ("bna", "SELECT IdMovimientoBNA AS id, Concepto AS d, ABS(Importe) AS imp, IdContacto AS c FROM dbo.[Movimientos BNA] "
                    "WHERE [Fecha / Hora Mov#] >= ?")):
        for m in fetch_all(sql, (desde,)):
            if m["c"] is None and (L._BANCARIO.search(m["d"] or "") or L._INVERSION.search(m["d"] or "")):
                continue
            if estado_resolucion.esta_resuelto(medio, int(m["id"])) == "sin_conciliar":
                n += 1
                total += _f(m["imp"])
    return {"cantidad": n, "importe": round(total, 2)}


def _facturas_esperadas() -> dict:
    from src.features.facturas_faltantes import service

    items = [i for i in service.tablero().get("items", []) if i.get("estado") == "atrasada"]
    return {"cantidad": len(items), "detalle": ", ".join(i["proveedor"] for i in items[:3])}


def _planilla_matias() -> dict:
    from src.features.ordenes import planilla_matias

    u = planilla_matias.ultima_lectura() or {}
    return {"cantidad": len(u.get("paraRevisar", [])) + len(u.get("cambiadas", []))}


def _costo_pendiente() -> dict:
    """Productos con stock cuyo costo todavía no tiene factura ni precio del pedido."""
    from src.features.remitos.stock_datos import calcular_stock

    n = sum(1 for v in calcular_stock().values()
            if any((c.get("restante") or 0) > 1e-9 and c.get("estadoCosto") == "pendiente" for c in v.get("capas", [])))
    return {"cantidad": n}


def _portales() -> dict:
    from src.features.boveda import repository

    r = repository.resumen()
    return {"cantidad": int(r.get("conError", 0)) + int(r.get("requiereIntervencion", 0))}


def _trabajos_sin_pagar() -> dict:
    from src.features.trabajos_eventuales.repository import BASE

    f = fetch_one(
        "SELECT COUNT(*) AS n, SUM(t.Total - ISNULL(pg.Pagado, 0)) AS imp " + BASE +
        " WHERE (pg.Hay = 0 AND t.EstadoPago <> 'Pagado') OR (pg.Hay > 0 AND ISNULL(pg.Pagado, 0) < t.Total)") or {}
    return {"cantidad": int(f.get("n") or 0), "importe": round(_f(f.get("imp")), 2)}


def _facturas_a_pagar() -> dict:
    from src.features.ordenes_pago import repository

    hoy = date.today()
    lista = [x for x in repository.pendientes() if x.get("estado") == "a pagar" and not x.get("suspendida")]
    proximas = [x for x in lista if x.get("vencimiento") and date.fromisoformat(str(x["vencimiento"])[:10]) <= hoy + timedelta(days=7)]
    vencidas = [x for x in lista if (x.get("diasVencida") or 0) > 0]
    # Lo que hay que pagar ya: vencidas y las que vencen en los próximos 7 días (las vencidas están incluidas en ambas).
    return {"cantidad": len(proximas), "vencidas": len(vencidas),
            "importe": round(sum(_f(x.get("saldo")) for x in proximas if x.get("moneda") != "Dolares"), 2),
            "detalle": f"{len(vencidas)} ya vencidas" if vencidas else None}


def _control_costos() -> dict:
    from src.features.imputacion import control_integridad

    e = control_integridad.estado()
    tipos = sorted({p.get("tipo") for p in e.get("problemas", [])})
    return {"cantidad": len(e.get("problemas", [])), "detalle": ", ".join(tipos[:2]), "calculando": e.get("controlando")}


PENDIENTES = [
    # clave, función, texto (singular, plural), destino
    ("bancos", _bancos_sin_conciliar, ("movimiento de banco sin conciliar", "movimientos de banco sin conciliar"), "/finanzas/tesoreria"),
    ("pagar", _facturas_a_pagar, ("factura a pagar, vencida o que vence esta semana", "facturas a pagar, vencidas o que vencen esta semana"), "/finanzas/ordenes-pago"),
    ("esperadas", _facturas_esperadas, ("factura esperada que no llegó", "facturas esperadas que no llegaron"), "/finanzas/facturas-esperadas"),
    ("matias", _planilla_matias, ("orden de Matías para corregir en la planilla", "órdenes de Matías para corregir en la planilla"), "/produccion/ordenes"),
    ("trabajos", _trabajos_sin_pagar, ("trabajo eventual sin pagar", "trabajos eventuales sin pagar"), "/personal/trabajos-eventuales"),
    ("costo", _costo_pendiente, ("producto en depósito con costo pendiente", "productos en depósito con costo pendiente"), "/produccion/stock"),
    ("portales", _portales, ("portal con error", "portales con error"), "/boveda"),
    ("control", _control_costos, ("aviso del control de costos", "avisos del control de costos"), "/imputacion"),
]


# ------------------------------------------------------------------ indicadores

def _bancos_saldo() -> dict:
    from src.features.tesoreria import repository

    out = {}
    for medio in ("galicia", "bna"):
        filas, _ = repository.get_movimientos(medio, None, None, 1, 1)
        if filas:
            out[medio] = {"saldo": _f(filas[0].get("saldo")), "fecha": str(filas[0].get("fecha") or filas[0].get("fechaHora") or "")[:10]}
    return {"total": round(sum(v["saldo"] for v in out.values()), 2), "cuentas": out}


def _deuda_proveedores() -> dict:
    from src.features.cuentas_corrientes import repository

    filas = repository.get_saldos_todos("saldo")
    pesos = sum(_f(s.get("saldoParcial")) for s in filas if _f(s.get("saldoParcial")) < 0)
    dolares = sum(_f(s.get("saldoDolares")) for s in filas if s.get("saldoDolares") is not None and _f(s.get("saldoDolares")) < 0)
    return {"pesos": round(-pesos, 2), "dolares": round(-dolares, 2), "proveedores": sum(1 for s in filas if _f(s.get("saldoParcial")) < 0)}


def _stock() -> dict:
    from src.features.remitos.stock_datos import calcular_stock

    s = calcular_stock()
    return {"valor": round(sum(_f(v.get("valor")) for v in s.values()), 2),
            "productos": sum(1 for v in s.values() if _f(v.get("existencia")) > 1e-9)}


def _cajas() -> dict:
    from src.features.cajas_efectivo import repository
    from src.features.cajas_efectivo.operaciones import CAJAS

    return {"pesos": round(repository.calcular_saldo(CAJAS["giamigli-sa"]) + repository.calcular_saldo(CAJAS["campo-chica"]), 2),
            "dolares": round(repository.calcular_saldo(CAJAS["giamigli-dolares"]), 2)}


def _flujo() -> list[dict]:
    from src.features.flujo_caja import repository

    hasta = date.today()
    desde = date(hasta.year, hasta.month, 1) - timedelta(days=150)
    movs = repository.get_movimientos_normalizados(date(desde.year, desde.month, 1), hasta)
    periodos = repository.agregar_por_periodo(movs, "mensual")
    return [{"periodo": p["periodo"], "neto": round(_f(p["totalNeto"]), 2)} for p in periodos][-6:]


def _campania() -> dict:
    """La campaña gruesa en curso (empieza el 1/7) con sus cultivos y superficie del plan, y las últimas órdenes."""
    hoy = date.today()
    inicio = hoy.year if hoy.month >= 7 else hoy.year - 1
    nombre = f"{inicio}/{inicio + 1}"
    cultivos = fetch_all(
        "SELECT cu.Cultivo AS cultivo, SUM(l.Superficie) AS ha FROM dbo.PlanAgricola p JOIN dbo.[Campañas] k ON k.[IdCampaña] = p.[IdCampaña] "
        "JOIN dbo.Cultivos cu ON cu.IdCultivo = p.IdCultivo JOIN dbo.Lotes l ON l.IdLote = p.IdLote "
        "WHERE k.[Campaña] IN (?, ?) AND ISNULL(p.NoSembrado, 0) = 0 GROUP BY cu.Cultivo ORDER BY SUM(l.Superficie) DESC",
        (nombre, str(inicio + 1)))
    ordenes = fetch_all(
        "SELECT TOP 4 o.IdOrdenTrabajo AS id, o.FechaPedido AS fecha, o.Estado AS estado, t.Labor AS labor FROM dbo.Ordenes_Trabajo o "
        "LEFT JOIN dbo.[Tipo Labores] t ON t.IdLabor = o.IdTipoLabor WHERE o.Estado <> 'Anulada' ORDER BY o.FechaPedido DESC, o.IdOrdenTrabajo DESC")
    return {"nombre": nombre, "cultivos": [{"cultivo": c["cultivo"], "ha": round(_f(c["ha"]), 1)} for c in cultivos],
            "ordenes": [{**o, "fecha": str(o["fecha"])[:10]} for o in ordenes]}


# ------------------------------------------------------------------ armado y caché

def calcular() -> dict:
    pendientes = []
    for clave, fn, (uno, varios), destino in PENDIENTES:
        r = _seguro(clave, fn)
        if r.get("error"):
            pendientes.append({"clave": clave, "texto": varios, "destino": destino, "error": True})
            continue
        n = int(r.get("cantidad") or 0)
        if n > 0:
            pendientes.append({"clave": clave, "cantidad": n, "texto": uno if n == 1 else varios, "destino": destino,
                               "importe": r.get("importe"), "detalle": r.get("detalle"), "vencidas": r.get("vencidas")})
    return {
        "calculado": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pendientes": pendientes,
        "indicadores": {"bancos": _seguro("bancos", _bancos_saldo), "deuda": _seguro("deuda", _deuda_proveedores),
                        "stock": _seguro("stock", _stock), "cajas": _seguro("cajas", _cajas)},
        "flujo": _seguro("flujo", _flujo),
        "campania": _seguro("campania", _campania),
    }


def _refrescar() -> None:
    try:
        datos = calcular()
        with _lock:
            _cache.update(t=time.time(), datos=datos)
    finally:
        _cache["calculando"] = False


def resumen(forzar: bool = False) -> dict:
    """Devuelve el último resumen al instante; si está viejo (o se fuerza), lo recalcula en segundo plano."""
    with _lock:
        viejo = forzar or time.time() - _cache["t"] > _VIGENCIA
        if viejo and not _cache["calculando"]:
            _cache["calculando"] = True
            threading.Thread(target=_refrescar, name="inicio-resumen", daemon=True).start()
        datos = _cache["datos"]
    return {"listo": datos is not None, "actualizando": _cache["calculando"], **(datos or {})}
