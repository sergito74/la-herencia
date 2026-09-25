"""Lectura normalizada y agregación de movimientos bancarios reales (018).

Solo lectura (`fetch_all`) sobre `Movimientos BNA`/`Movimientos Galicia` —
nunca escribe (constitución II, FR-006). No introduce una fuente de verdad
paralela: los mismos totales que muestra Tesorería para un banco/rango deben
coincidir exactamente con lo que agrega este módulo (SC-002).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from src.db.connection import fetch_all
from src.db.params import as_sql_datetime
from src.features.flujo_caja import atribucion
from src.features.flujo_caja.clasificacion import es_interno

FECHA_PRIMER_SALDO_CONOCIDO = date(2010, 8, 31)


def get_movimientos_normalizados(fecha_desde: date, fecha_hasta: date) -> list[dict]:
    """Movimientos de BNA (3 cuentas ya distinguidas) + Galicia en un mismo
    formato: `{fecha, banco, numeroCuentaBancaria, importe, concepto,
    idContacto, contacto, esInterno}`."""
    desde, hasta = as_sql_datetime(fecha_desde), as_sql_datetime(fecha_hasta)

    filas_bna = fetch_all(
        """
        SELECT m.IdMovimientoBNA AS idMovimiento, m.[Fecha / Hora Mov#] AS fecha, m.Importe AS importe,
               m.Concepto AS concepto, m.IdContacto AS idContacto, m.Contacto AS contacto,
               cb.NumeroCuenta AS numeroCuentaBancaria
        FROM dbo.[Movimientos BNA] m
        LEFT JOIN dbo.CuentasBancarias cb ON cb.IdCuentaBancaria = m.IdCuentaBancaria
        WHERE m.[Fecha / Hora Mov#] BETWEEN ? AND ?
        """,
        (desde, hasta),
    )
    movimientos = [
        {
            "fecha": f["fecha"],
            "banco": "BNA",
            "origenMovimiento": "bna",
            "idMovimientoOrigen": f["idMovimiento"],
            "numeroCuentaBancaria": f["numeroCuentaBancaria"],
            "importe": float(f["importe"]),
            "concepto": f["concepto"],
            "idContacto": f["idContacto"],
            "contacto": f["contacto"],
            "esInterno": es_interno("BNA", f["concepto"]),
        }
        for f in filas_bna
    ]

    filas_galicia = fetch_all(
        """
        SELECT IdMovimiento AS idMovimiento, Fecha AS fecha, [Débitos] AS debitos, [Créditos] AS creditos,
               [Descripción] AS concepto, [Grupo de Conceptos] AS grupoConceptos,
               IdContacto AS idContacto, Contacto AS contacto
        FROM dbo.[Movimientos Galicia]
        WHERE Fecha BETWEEN ? AND ?
        """,
        (desde, hasta),
    )
    numero_cuenta_galicia = "0000798-8 383-4"
    for f in filas_galicia:
        importe = float(f["creditos"] or 0) - float(f["debitos"] or 0)
        movimientos.append(
            {
                "fecha": f["fecha"],
                "banco": "Galicia",
                "origenMovimiento": "galicia",
                "idMovimientoOrigen": f["idMovimiento"],
                "numeroCuentaBancaria": numero_cuenta_galicia,
                "importe": importe,
                "concepto": f["concepto"],
                "idContacto": f["idContacto"],
                "contacto": f["contacto"],
                "esInterno": es_interno("Galicia", None, f["grupoConceptos"]),
            }
        )

    return movimientos


def _clave_periodo(fecha: datetime, granularidad: str) -> str:
    if granularidad == "semanal":
        iso = fecha.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if granularidad == "trimestral":
        return f"{fecha.year:04d}-T{(fecha.month - 1) // 3 + 1}"
    if granularidad == "anual":
        return f"{fecha.year:04d}"
    return f"{fecha.year:04d}-{fecha.month:02d}"


def agregar_por_periodo(movimientos: list[dict], granularidad: str) -> list[dict]:
    """Agrupa `movimientos` (de `get_movimientos_normalizados`) por mes o
    semana, separando el neto operativo de los movimientos internos
    (FR-001/FR-002) y contando lo sin clasificar (FR-009)."""
    periodos: dict[str, dict] = {}

    for m in movimientos:
        clave = _clave_periodo(m["fecha"], granularidad)
        periodo = periodos.setdefault(
            clave,
            {
                "periodo": clave,
                "porCuenta": {},
                "totalIngresos": 0.0,
                "totalEgresos": 0.0,
                "internosIngresos": 0.0,
                "internosEgresos": 0.0,
                "sinClasificarCantidad": 0,
                "sinClasificarImporte": 0.0,
            },
        )

        cuenta_key = (m["banco"], m["numeroCuentaBancaria"])
        cuenta = periodo["porCuenta"].setdefault(
            cuenta_key, {"banco": m["banco"], "numeroCuenta": m["numeroCuentaBancaria"], "ingresos": 0.0, "egresos": 0.0}
        )

        importe = m["importe"]
        if m["esInterno"]:
            if importe >= 0:
                periodo["internosIngresos"] += importe
            else:
                periodo["internosEgresos"] += importe
        else:
            if importe >= 0:
                periodo["totalIngresos"] += importe
                cuenta["ingresos"] += importe
            else:
                periodo["totalEgresos"] += importe
                cuenta["egresos"] += importe

        if not m["esInterno"] and m["idContacto"] is None:
            periodo["sinClasificarCantidad"] += 1
            periodo["sinClasificarImporte"] += abs(importe)

    resultado = []
    for clave in sorted(periodos.keys()):
        p = periodos[clave]
        resultado.append(
            {
                "periodo": p["periodo"],
                "porCuenta": [
                    {**c, "neto": round(c["ingresos"] + c["egresos"], 2)} for c in p["porCuenta"].values()
                ],
                "totalIngresos": round(p["totalIngresos"], 2),
                "totalEgresos": round(p["totalEgresos"], 2),
                "totalNeto": round(p["totalIngresos"] + p["totalEgresos"], 2),
                "movimientosInternos": {
                    "ingresos": round(p["internosIngresos"], 2),
                    "egresos": round(p["internosEgresos"], 2),
                    "total": round(p["internosIngresos"] + p["internosEgresos"], 2),
                },
                "sinClasificar": {
                    "cantidad": p["sinClasificarCantidad"],
                    "importeAbsoluto": round(p["sinClasificarImporte"], 2),
                },
            }
        )
    return resultado


def ultima_fecha_por_cuenta() -> list[dict]:
    """`MAX(Fecha)` por cuenta conocida (FR-004) — incluye las 3 cuentas BNA
    (también las dadas de baja) y Galicia, sin filtrar por vigencia."""
    filas_bna = fetch_all(
        """
        SELECT cb.Banco AS banco, cb.NumeroCuenta AS numeroCuenta,
               MAX(m.[Fecha / Hora Mov#]) AS fecha
        FROM dbo.CuentasBancarias cb
        LEFT JOIN dbo.[Movimientos BNA] m ON m.IdCuentaBancaria = cb.IdCuentaBancaria
        WHERE cb.Banco = 'BNA'
        GROUP BY cb.Banco, cb.NumeroCuenta
        """
    )
    fecha_galicia = fetch_all("SELECT MAX(Fecha) AS fecha FROM dbo.[Movimientos Galicia]")
    resultado = [
        {"banco": f["banco"], "numeroCuenta": f["numeroCuenta"], "fecha": f["fecha"]} for f in filas_bna
    ]
    resultado.append(
        {
            "banco": "Galicia",
            "numeroCuenta": "0000798-8 383-4",
            "fecha": fecha_galicia[0]["fecha"] if fecha_galicia else None,
        }
    )
    return resultado


def atribuir_movimientos(movimientos: list[dict]) -> list[dict]:
    """Agrega `rubro`/`centroCosto` a cada movimiento no interno (018 v2,
    2026-09-24: "ingresos y egresos de dinero reales", nunca documentos de
    venta/compra — el rubro solo sirve para AGRUPAR el movimiento real, el
    importe siempre es el del banco, no el de la venta/compra)."""
    reales = [m for m in movimientos if not m["esInterno"]]
    if not reales:
        return movimientos

    fechas = [m["fecha"].date() if hasattr(m["fecha"], "date") else m["fecha"] for m in reales]
    indice_ingresos = atribucion.construir_indice_ingresos(min(fechas), max(fechas))

    for m in reales:
        fecha = m["fecha"].date() if hasattr(m["fecha"], "date") else m["fecha"]
        importe_abs = round(abs(m["importe"]), 2)

        # 019: las aplicaciones reales (pago/cobro -> documento) son la
        # fuente PRIMARIA de rubro — el matching exacto por importe/fecha
        # queda como fallback (research.md §7).
        atrib = atribucion.atribuir_desde_aplicaciones(m.get("origenMovimiento"), m.get("idMovimientoOrigen"))
        if atrib is None:
            if m["importe"] < 0:
                atrib = atribucion.atribuir_egreso(m["idContacto"], fecha, importe_abs)
            else:
                atrib = atribucion.atribuir_ingreso(indice_ingresos, m["idContacto"], fecha, importe_abs)
            if atrib["rubro"] == atribucion.SIN_RUBRO:
                # FR-010: sin match ni aplicación, se distingue historico
                # (antes del corte, no exigible) de pendiente real de aplicar.
                if fecha < atribucion.FECHA_CORTE_APLICACION:
                    atrib = {"rubro": atribucion.HISTORICO_SIN_APLICAR, "centroCosto": None}
                else:
                    atrib = {"rubro": atribucion.PENDIENTE_DE_APLICAR, "centroCosto": None}

        m["rubro"] = atrib["rubro"]
        m["centroCosto"] = atrib["centroCosto"]
    return movimientos


def agregar_por_rubro(movimientos_atribuidos: list[dict], granularidad: str) -> dict:
    """Ingresos (lista plana) y Egresos (agrupados por Centro de Costos, con
    subtotal) × período — formato pedido por Sergio (Cash Flow 2025-2026.xlsx,
    adaptado: acá el Rubro/Centro de Costos sale de la atribución real, no
    se tipea a mano, y los grupos de Egresos SÍ tienen subtotal)."""
    periodos: set[str] = set()
    ingresos: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    egresos: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for m in movimientos_atribuidos:
        if m["esInterno"]:
            continue
        clave = _clave_periodo(m["fecha"], granularidad)
        periodos.add(clave)
        if m["importe"] >= 0:
            ingresos[m["rubro"]][clave] += m["importe"]
        else:
            egresos[(m["centroCosto"] or "Sin centro de costos", m["rubro"])][clave] += m["importe"]

    periodos_ordenados = sorted(periodos)

    filas_ingresos = [
        {"rubro": rubro, "valores": {p: round(v.get(p, 0.0), 2) for p in periodos_ordenados}, "total": round(sum(v.values()), 2)}
        for rubro, v in sorted(ingresos.items())
    ]
    total_ingresos_por_periodo = {
        p: round(sum(f["valores"][p] for f in filas_ingresos), 2) for p in periodos_ordenados
    }

    grupos: dict[str, list[dict]] = defaultdict(list)
    for (centro, rubro), v in sorted(egresos.items()):
        grupos[centro].append(
            {"rubro": rubro, "valores": {p: round(v.get(p, 0.0), 2) for p in periodos_ordenados}, "total": round(sum(v.values()), 2)}
        )
    centros_costo = []
    for centro, filas in sorted(grupos.items()):
        subtotal_por_periodo = {p: round(sum(f["valores"][p] for f in filas), 2) for p in periodos_ordenados}
        centros_costo.append(
            {
                "centroCosto": centro,
                "rubros": filas,
                "subtotalPorPeriodo": subtotal_por_periodo,
                "subtotal": round(sum(subtotal_por_periodo.values()), 2),
            }
        )
    total_egresos_por_periodo = {
        p: round(sum(c["subtotalPorPeriodo"][p] for c in centros_costo), 2) for p in periodos_ordenados
    }

    return {
        "periodos": periodos_ordenados,
        "ingresos": {"rubros": filas_ingresos, "totalPorPeriodo": total_ingresos_por_periodo},
        "egresos": {"centrosCosto": centros_costo, "totalPorPeriodo": total_egresos_por_periodo},
    }


def saldo_inicial_al(fecha_desde: date) -> float:
    """Suma de `SaldoApertura` de cada cuenta + todos sus movimientos reales
    (incluidos los internos — la plata que realmente hay en el banco no
    distingue interno/operativo) desde su apertura hasta `fecha_desde`
    (exclusive). Pedido explícito de Sergio: el saldo inicial sale de lo ya
    cargado en el sistema, no se tipea a mano."""
    cuentas = fetch_all("SELECT SaldoApertura AS saldoApertura FROM dbo.CuentasBancarias")
    saldo = sum(float(c["saldoApertura"]) for c in cuentas)

    hasta = as_sql_datetime(fecha_desde)
    fila_bna = fetch_all(
        "SELECT SUM(Importe) AS total FROM dbo.[Movimientos BNA] WHERE [Fecha / Hora Mov#] < ?", (hasta,)
    )
    fila_galicia = fetch_all(
        "SELECT SUM([Créditos]) AS creditos, SUM([Débitos]) AS debitos FROM dbo.[Movimientos Galicia] WHERE Fecha < ?",
        (hasta,),
    )
    saldo += float(fila_bna[0]["total"] or 0)
    saldo += float(fila_galicia[0]["creditos"] or 0) - float(fila_galicia[0]["debitos"] or 0)
    return round(saldo, 2)
