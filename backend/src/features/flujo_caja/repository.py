"""Lectura normalizada y agregación de movimientos bancarios reales (018).

Solo lectura (`fetch_all`) sobre `Movimientos BNA`/`Movimientos Galicia` —
nunca escribe (constitución II, FR-006). No introduce una fuente de verdad
paralela: los mismos totales que muestra Tesorería para un banco/rango deben
coincidir exactamente con lo que agrega este módulo (SC-002).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from src.db.connection import fetch_all
from src.db.params import as_sql_datetime
from src.features.flujo_caja import atribucion
from src.features.flujo_caja import cotizacion as cot
from src.features.flujo_caja.clasificacion import TIPOS_INTERNOS, emparejar_traspasos, es_interno, tipo_interno

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
            "tipoInterno": tipo_interno("BNA", float(f["importe"]), f["concepto"]),
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
                "tipoInterno": tipo_interno("Galicia", importe, None, f["grupoConceptos"]),
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


CUENTA_NACION = "Nación"
CUENTA_GALICIA = "Galicia CC"
CUENTA_FIMA = "Galicia Fondo FIMA"
ACLARACION_FIMA = "Colocado menos rescatado (FIMA y plazos fijos). No es el saldo real del fondo: los rescates incluyen rendimiento, por eso puede dar negativo"
SIN_CENTRO = atribucion.CENTRO_COSTO_SIN_ASIGNAR


def _cuenta(m: dict) -> str:
    return CUENTA_NACION if m["banco"] == "BNA" else CUENTA_GALICIA


def _dia(fecha) -> date:
    return fecha.date() if isinstance(fecha, datetime) else fecha


def _atribucion_fallback(m: dict, indice_ingresos) -> tuple[str, str | None]:
    """Regla de 018 v2 para un movimiento sin aplicaciones (una sola parte)."""
    if atribucion.es_ley_25413(m.get("concepto")):
        return atribucion.RUBRO_LEY_25413, atribucion.CENTRO_COSTO_LEY_25413
    if atribucion.es_arba_recaudacion(m.get("concepto")):
        return atribucion.RUBRO_ARBA_RECAUDACION, atribucion.CENTRO_COSTO_LEY_25413
    fecha = _dia(m["fecha"])
    importe_abs = round(abs(m["importe"]), 2)
    if m["importe"] < 0:
        atrib = atribucion.atribuir_egreso(m["idContacto"], fecha, importe_abs)
    else:
        atrib = atribucion.atribuir_ingreso(indice_ingresos, m["idContacto"], fecha, importe_abs)
    if atrib["rubro"] == atribucion.SIN_RUBRO:
        return atribucion.rubro_sin_aplicar(fecha), None
    return atrib["rubro"], atrib["centroCosto"]


def atribuir_movimientos(movimientos: list[dict]) -> list[dict]:
    """Agrega `partes` a cada movimiento (030): una o más `{seccion, rubro,
    centroCosto, importeArs, documentoAplicado}` cuya suma es el importe del
    movimiento. Los internos van a su fila de "Movimientos entre cuentas
    propias"; el resto se reparte por las aplicaciones (019) o, sin ellas,
    con la regla de 018 v2. `rubro`/`centroCosto` quedan con la parte mayor,
    por compatibilidad con los consumidores de 018."""
    emparejar_traspasos(movimientos)
    reales = [m for m in movimientos if not m["esInterno"]]
    indice_ingresos = {}
    aplicaciones = {}
    if reales:
        fechas = [_dia(m["fecha"]) for m in reales]
        indice_ingresos = atribucion.construir_indice_ingresos(min(fechas), max(fechas))
        from src.features.aplicaciones_pago.repository import aplicaciones_vigentes_por_movimiento

        aplicaciones = aplicaciones_vigentes_por_movimiento()
    memo_compras: dict = {}

    for m in movimientos:
        signo = 1 if m["importe"] >= 0 else -1
        if m["esInterno"]:
            partes = [{"seccion": "internos", "rubro": m.get("tipoInterno") or "Traspaso entre bancos",
                       "centroCosto": None, "importe": round(abs(m["importe"]), 2), "documentoAplicado": None}]
        else:
            fijo = atribucion.es_ley_25413(m.get("concepto")) or atribucion.es_arba_recaudacion(m.get("concepto"))
            partes = None
            if not fijo:
                partes = atribucion.partes_desde_aplicaciones(
                    aplicaciones.get((m.get("origenMovimiento"), m.get("idMovimientoOrigen")), []),
                    m["importe"], m["fecha"], memo_compras)
            if partes is None:
                rubro, centro = _atribucion_fallback(m, indice_ingresos)
                partes = [{"rubro": rubro, "centroCosto": centro, "importe": round(abs(m["importe"]), 2), "documentoAplicado": None}]
            for p in partes:
                p["seccion"] = "ingresos" if signo > 0 else "egresos"
        for p in partes:
            p["importeArs"] = round(signo * p.pop("importe"), 2)
            if p["seccion"] == "egresos" and not p["centroCosto"]:
                p["centroCosto"] = SIN_CENTRO
            p.update(fecha=_dia(m["fecha"]), cuenta=_cuenta(m), concepto=m.get("concepto"), contacto=m.get("contacto"),
                     origenMovimiento=m.get("origenMovimiento"), idMovimiento=m.get("idMovimientoOrigen"),
                     importeMovimiento=round(m["importe"], 2), sinContraparte=bool(m.get("sinContraparte")),
                     esFima=m["banco"] == "Galicia" and m["esInterno"] and m.get("tipoInterno") != "Traspaso entre bancos")
        m["partes"] = partes
        mayor = max(partes, key=lambda p: abs(p["importeArs"]))
        m["rubro"], m["centroCosto"] = mayor["rubro"], mayor["centroCosto"]
    return movimientos


def partes_de_movimientos(movimientos: list[dict]) -> list[dict]:
    return [p for m in atribuir_movimientos(movimientos) for p in m["partes"]]


def convertir_partes_a_usd(partes: list[dict], serie: dict) -> None:
    """Cada parte con la cotización BNA vendedor divisa de su día (o la
    anterior ≤ 7 días). Sin cotización → `importeUsd=None` (se informa, no se inventa)."""
    for p in partes:
        c = cot.cotizacion_del_dia(serie, p["fecha"])
        if c is None:
            p.update(cotizacion=None, fechaCotizacion=None, importeUsd=None)
        else:
            p.update(cotizacion=c[0], fechaCotizacion=c[1], importeUsd=round(p["importeArs"] / c[0], 2))


def periodos_del_rango(desde: date, hasta: date, granularidad: str) -> list[str]:
    claves: list[str] = []
    d = desde
    while d <= hasta:
        k = _clave_periodo(d, granularidad)
        if not claves or claves[-1] != k:
            claves.append(k)
        d += timedelta(days=1)
    return claves


def fin_de_periodo(clave: str, desde: date, hasta: date, granularidad: str) -> date:
    fin = desde
    d = desde
    while d <= hasta:
        if _clave_periodo(d, granularidad) == clave:
            fin = d
        d += timedelta(days=1)
    return fin


def _valor(p: dict, moneda: str) -> float | None:
    return p["importeArs"] if moneda == "ARS" else p.get("importeUsd")


def clave_celda(p: dict) -> tuple:
    return (p["seccion"], p["centroCosto"] if p["seccion"] == "egresos" else None, p["rubro"])


def agregar_por_rubro(partes: list[dict], granularidad: str, periodos: list[str], moneda: str = "ARS") -> dict:
    """Ingresos por rubro, egresos por centro de costo con subtotal, internos
    en sus tres filas fijas y los netos por período (030, contracts/api.md)."""
    celdas: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    sin_tc: dict[tuple, dict] = {}
    for p in partes:
        per = _clave_periodo(p["fecha"], granularidad)
        v = _valor(p, moneda)
        clave = clave_celda(p)
        if v is None:
            s = sin_tc.setdefault((per,) + clave, {"periodo": per, "seccion": p["seccion"], "centroCosto": clave[1],
                                                     "rubro": p["rubro"], "cantidad": 0, "importeArs": 0.0})
            s["cantidad"] += 1
            s["importeArs"] = round(s["importeArs"] + p["importeArs"], 2)
            continue
        celdas[clave][per] += v

    def fila(rubro, valores):
        vals = {per: round(valores.get(per, 0.0), 2) for per in periodos}
        return {"rubro": rubro, "valores": vals, "total": round(sum(vals.values()), 2)}

    def totales(filas):
        return {per: round(sum(f["valores"][per] for f in filas), 2) for per in periodos}

    ingresos = [fila(r, v) for (sec, _, r), v in sorted(celdas.items()) if sec == "ingresos"]
    grupos: dict[str, list] = defaultdict(list)
    for (sec, centro, r), v in sorted(celdas.items()):
        if sec == "egresos":
            grupos[centro].append(fila(r, v))
    centros = []
    for centro, filas in sorted(grupos.items()):
        sub = totales(filas)
        centros.append({"centroCosto": centro, "rubros": filas, "subtotalPorPeriodo": sub, "subtotal": round(sum(sub.values()), 2)})
    internos = [fila(t, celdas.get(("internos", None, t), {})) for t in TIPOS_INTERNOS]

    tot_ing, tot_int = totales(ingresos), totales(internos)
    tot_egr = {per: round(sum(c["subtotalPorPeriodo"][per] for c in centros), 2) for per in periodos}
    return {
        "periodos": periodos,
        "ingresos": {"rubros": ingresos, "totalPorPeriodo": tot_ing},
        "egresos": {"centrosCosto": centros, "totalPorPeriodo": tot_egr},
        "netoOperativoPorPeriodo": {per: round(tot_ing[per] + tot_egr[per], 2) for per in periodos},
        "internos": {"rubros": internos, "totalPorPeriodo": tot_int},
        "sinTipoCambio": list(sin_tc.values()),
    }


def saldos_por_cuenta_al(fecha: date) -> dict[str, float]:
    """Saldo de cada cuenta al inicio de `fecha` (exclusive), en pesos: Nación
    (las 3 cuentas BNA), Galicia CC y el FIMA reconstruido como capital neto
    colocado (−Σ movimientos Galicia "Inversiones"; sin rendimiento, que no
    está en los extractos)."""
    hasta = as_sql_datetime(fecha)
    aperturas = fetch_all("SELECT Banco AS banco, SUM(SaldoApertura) AS saldo FROM dbo.CuentasBancarias GROUP BY Banco")
    apertura = {a["banco"]: float(a["saldo"] or 0) for a in aperturas}
    bna = fetch_all("SELECT SUM(Importe) AS total FROM dbo.[Movimientos BNA] WHERE [Fecha / Hora Mov#] < ?", (hasta,))
    gal = fetch_all(
        "SELECT SUM(ISNULL([Créditos],0) - ISNULL([Débitos],0)) AS total, "
        "SUM(CASE WHEN [Grupo de Conceptos] LIKE '%inversiones%' THEN ISNULL([Créditos],0) - ISNULL([Débitos],0) ELSE 0 END) AS inversiones "
        "FROM dbo.[Movimientos Galicia] WHERE Fecha < ?",
        (hasta,),
    )
    return {
        CUENTA_NACION: round(apertura.get("BNA", 0) + float(bna[0]["total"] or 0), 2),
        CUENTA_GALICIA: round(apertura.get("Galicia", 0) + float(gal[0]["total"] or 0), 2),
        CUENTA_FIMA: round(-float(gal[0]["inversiones"] or 0), 2),
    }


def saldo_inicial_al(fecha_desde: date) -> float:
    """Total de 018 (Nación + Galicia CC, sin el FIMA reconstruido)."""
    s = saldos_por_cuenta_al(fecha_desde)
    return round(s[CUENTA_NACION] + s[CUENTA_GALICIA], 2)


def saldos_finales(saldos_iniciales: dict[str, float], partes: list[dict], granularidad: str, periodos: list[str]) -> dict[str, dict[str, float]]:
    """Saldo en pesos de cada cuenta al cierre de cada período. Una colocación
    FIMA resta de Galicia CC y suma al FIMA (total sin cambio)."""
    netos: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for p in partes:
        per = _clave_periodo(p["fecha"], granularidad)
        netos[p["cuenta"]][per] += p["importeArs"]
        if p["esFima"]:
            netos[CUENTA_FIMA][per] -= p["importeArs"]
    resultado: dict[str, dict[str, float]] = {}
    for cuenta, inicial in saldos_iniciales.items():
        acumulado, serie = inicial, {}
        for per in periodos:
            acumulado += netos[cuenta].get(per, 0.0)
            serie[per] = round(acumulado, 2)
        resultado[cuenta] = serie
    return resultado


def flujo_por_rubro(desde: date, hasta: date, granularidad: str, moneda: str) -> dict:
    """Cálculo completo de la pantalla (030), recalculado siempre (FR-009)."""
    movimientos = get_movimientos_normalizados(desde, hasta)
    partes = partes_de_movimientos(movimientos)
    periodos = periodos_del_rango(desde, hasta, granularidad)
    serie = None
    if moneda == "USD":
        serie = cot.cargar_serie(desde, hasta)
        convertir_partes_a_usd(partes, serie)
    agregado = agregar_por_rubro(partes, granularidad, periodos, moneda)

    iniciales = saldos_por_cuenta_al(desde)
    finales = saldos_finales(iniciales, partes, granularidad, periodos)
    saldos_sin_tc: list[str] = []

    def convertir(valor: float, fecha: date, etiqueta: str) -> float | None:
        if moneda == "ARS":
            return valor
        c = cot.cotizacion_del_dia(serie, fecha)
        if c is None:
            if etiqueta not in saldos_sin_tc:
                saldos_sin_tc.append(etiqueta)
            return None
        return round(valor / c[0], 2)

    cuentas_ini = [
        {"cuenta": c, "importe": convertir(v, desde, "inicial"), **({"aclaracion": ACLARACION_FIMA} if c == CUENTA_FIMA else {})}
        for c, v in iniciales.items()
    ]
    total_ini = convertir(sum(iniciales.values()), desde, "inicial")
    fin_por = {per: fin_de_periodo(per, desde, hasta, granularidad) for per in periodos}
    final_cuenta = {c: {per: convertir(v, fin_por[per], per) for per, v in serie_c.items()} for c, serie_c in finales.items()}
    final_total = {per: convertir(sum(finales[c][per] for c in finales), fin_por[per], per) for per in periodos}

    return {
        "moneda": moneda,
        **agregado,
        "saldoInicial": {"cuentas": cuentas_ini, "total": total_ini},
        "saldoFinalPorPeriodo": final_total,
        "saldoFinalPorCuenta": final_cuenta,
        "saldosSinTipoCambio": saldos_sin_tc,
        "traspasosSinContraparte": [
            {"fecha": p["fecha"], "cuenta": p["cuenta"], "importe": p["importeArs"], "idMovimiento": p["idMovimiento"]}
            for p in partes if p["sinContraparte"]
        ],
        "ultimaFechaCotizacion": cot.ultima_fecha_serie() if moneda == "USD" else None,
        "_partes": partes,
    }


def detalle_celda(desde: date, hasta: date, granularidad: str, moneda: str, periodo: str, seccion: str,
                  rubro: str, centro_costo: str | None) -> dict:
    """Partes que componen una celda; `total` es exactamente el valor de la
    celda en `flujo_por_rubro` con los mismos parámetros (FR-006)."""
    if periodo not in periodos_del_rango(desde, hasta, granularidad):
        raise ValueError("El período no corresponde al rango y la granularidad elegidos.")
    partes = partes_de_movimientos(get_movimientos_normalizados(desde, hasta))
    if moneda == "USD":
        convertir_partes_a_usd(partes, cot.cargar_serie(desde, hasta))
    clave = (seccion, centro_costo if seccion == "egresos" else None, rubro)
    items = [p for p in partes if _clave_periodo(p["fecha"], granularidad) == periodo and clave_celda(p) == clave]
    items.sort(key=lambda p: (p["fecha"], p["cuenta"], p["idMovimiento"] or 0))
    total = round(sum((_valor(p, moneda) or 0) for p in items if _valor(p, moneda) is not None), 2)
    return {"total": total, "items": [{k: v for k, v in p.items() if k != "esFima"} for p in items]}
