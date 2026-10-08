"""Cuentas con documentos en dólares y en pesos: un solo criterio — 035 (Historia 0, FR-024).

La vista compartida `vw_MovimientosCuenta_Base` guarda cada documento en su moneda de origen: una factura en
dólares figura por su importe en dólares y un pago bancario por su importe en pesos, y el saldo suma ambos como
si fueran lo mismo. Para las cuentas con documentos en dólares esta capa (solo lectura, no toca la vista) muestra:

  * el saldo en PESOS: cada documento en dólares se pesifica con el tipo de cambio de su factura
    (`Compras.[Tipo de Cambio]`); los pagos, que son siempre en pesos, quedan como están. Es el mismo criterio
    que usa el recálculo FIFO. Con él, una factura de US$ 216,70 a $ 96,69 queda en $ 20.952,45 y un pago de
    $ 20.952,45 la cierra.
  * un saldo en DÓLARES informativo: los documentos en dólares tal cual y cada importe en pesos dividido por el
    dólar BNA vendedor divisa del día anterior (decisión del 01/10/2026 para pagos en pesos de documentos en
    dólares). La diferencia entre ambos saldos es diferencia de cambio.
"""

from __future__ import annotations

from bisect import bisect_left
from datetime import date, datetime

DOLARES = "Dolares"


def _dia(valor) -> date | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return datetime.fromisoformat(str(valor)[:19]).date()


class CotizacionBNA:
    """Dólar BNA vendedor divisa por día (tabla `Dolar BNA`). `dia_anterior(f)` es la cotización más reciente anterior a `f`."""

    def __init__(self, serie: dict[date, float]):
        self._fechas = sorted(serie)
        self._valores = [serie[f] for f in self._fechas]

    def dia_anterior(self, fecha: date | None) -> float | None:
        if fecha is None or not self._fechas:
            return None
        i = bisect_left(self._fechas, fecha)  # primera fecha >= fecha: la anterior es i-1
        return self._valores[i - 1] if i > 0 else None


def tiene_documentos_en_dolares(compras: dict[int, dict]) -> bool:
    return any(c.get("moneda") == DOLARES for c in compras.values())


def moneda_que_gobierna(filas: list[dict], compras: dict[int, dict]) -> str:
    """Moneda que gobierna la cuenta según cómo emite sus documentos el proveedor (decisión de Sergio, 07/10/2026).

    `Dolares` si todos sus documentos están en dólares, `Pesos` si ninguno lo está y `Mixta` si tiene de las dos
    (en ese caso cada documento gobierna en su moneda y, para separar los pagos por moneda, hace falta que el FIFO
    haya asignado cada pago a su documento). Las notas de ajuste de tipo de cambio no cuentan como documentos en pesos.
    """
    en_dolares = en_pesos = False
    for f in filas:
        if f["Origen"] != "Compras":
            continue
        c = compras.get(int(f["IdOrigen"]), {})
        if c.get("moneda") == DOLARES:
            en_dolares = True
        elif not c.get("ajusta"):
            en_pesos = True
    if en_dolares and not en_pesos:
        return DOLARES
    return "Mixta" if en_dolares else "Pesos"


def _recorrer(filas: list[dict], compras: dict[int, dict], cotizacion: CotizacionBNA, entregas: dict[tuple[str, int], date] | None,
              tc_pagos: float | None, tc_ventas: dict[int, float] | None = None) -> tuple[list[dict], list[str], float, float]:
    """Pasa las filas a pesos y dólares. `tc_pagos`: si viene, los importes en pesos se pasan a dólares con ese tipo de cambio
    (el pactado en las facturas) en vez del dólar BNA del día anterior.

    Dos criterios (decisión de Sergio, 08/10/2026, hallados en FEDEA contra su libro en dólares): (1) un documento en pesos marcado
    como ajuste de tipo de cambio (`Ajusta Tipo Cambio`) corrige solo la cuenta en pesos y no mueve los dólares; (2) una venta de
    granos se pasa a dólares con el tipo de cambio de la propia venta (`tc_ventas`: IdVenta -> TC) y no con el dólar BNA."""
    saldo_pesos = saldo_dolares = 0.0
    salida, avisos = [], []
    for f in filas:
        deuda, credito = float(f["Deuda"] or 0), float(f["Credito"] or 0)
        fecha = _dia(f["Fecha"])
        compra = compras.get(int(f["IdOrigen"])) if f["Origen"] == "Compras" else None
        en_dolares = bool(compra and compra.get("moneda") == DOLARES)
        entrega = (entregas or {}).get((f["Origen"], int(f["IdOrigen"])))
        tc_venta = (tc_ventas or {}).get(int(f["IdOrigen"])) if f["Origen"] == "Venta Granos" else None
        tc_dia = tc_pagos or tc_venta or cotizacion.dia_anterior(entrega or fecha)
        ajuste_pesos = bool(compra and compra.get("ajusta") and not en_dolares)
        fila = {"fecha": fecha, "documento": f["Documento"], "numeroDocumento": f["Nro Documento"], "origenTipo": f["Origen"],
                "idOrigen": int(f["IdOrigen"]), "moneda": DOLARES if en_dolares else "Pesos", "deudaOriginal": deuda, "creditoOriginal": credito,
                "tipoDeCambio": None, "tcEstimado": False, "fechaEntrega": entrega}
        if en_dolares:
            tc = float(compra["tc"]) if (compra.get("tc") or 0) > 1 else None
            if tc is None:
                tc, fila["tcEstimado"] = tc_dia, True
                avisos.append(f"El documento {f['Nro Documento']} está en dólares y no tiene tipo de cambio: se usó el dólar BNA del día anterior"
                              if tc_dia else f"El documento {f['Nro Documento']} está en dólares y no tiene tipo de cambio")
            fila["tipoDeCambio"] = tc
            deuda_p, credito_p = (round(deuda * tc, 2), round(credito * tc, 2)) if tc else (0.0, 0.0)
            deuda_d, credito_d = deuda, credito
        else:
            deuda_p, credito_p = deuda, credito
            deuda_d, credito_d = (round(deuda / tc_dia, 4), round(credito / tc_dia, 4)) if tc_dia else (0.0, 0.0)
            if ajuste_pesos:
                deuda_d = credito_d = 0.0
        saldo_pesos = round(saldo_pesos + credito_p - deuda_p, 4)
        saldo_dolares = round(saldo_dolares + credito_d - deuda_d, 4)
        fila.update(deudaPesos=deuda_p, creditoPesos=credito_p, saldoPesos=round(saldo_pesos, 2), saldoDolares=round(saldo_dolares, 2))
        salida.append(fila)
    return salida, avisos, saldo_pesos, saldo_dolares


def construir(filas: list[dict], compras: dict[int, dict], cotizacion: CotizacionBNA, entregas: dict[tuple[str, int], date] | None = None,
              tc_pactado: bool = False, tc_ventas: dict[int, float] | None = None) -> dict:
    """Movimientos de una cuenta con su moneda, importes en pesos, saldo acumulado en pesos y en dólares.

    `filas`: filas de la vista ya ordenadas por (Fecha, Origen, IdOrigen) con Fecha, Documento, Nro Documento,
    Deuda, Credito, Origen, IdOrigen. `compras`: IdDeuda -> {moneda, tc} de los renglones `Compras`.
    `entregas`: (Origen, IdOrigen) de un débito bancario -> fecha en que se entregó el cheque. El pago con cheque queda
    fijado en pesos el día de la entrega, no el del débito: para pasarlo a dólares se usa el dólar de ese día.
    `tc_pactado`: Sergio declaró que el proveedor factura en dólares a un tipo de cambio pactado (regla `tc-pactado`):
    los pagos en pesos se pasan a dólares con el tipo de cambio de las facturas y no con el dólar BNA, así que no hay
    diferencia de cambio. Solo para cuentas cuyos documentos están todos en dólares. Nunca se deduce solo: dos casos con
    la misma forma (pago exacto en pesos al tipo de cambio de la factura) pueden tener o no un tipo de cambio pactado.
    """
    gobierna = moneda_que_gobierna(filas, compras)
    salida, avisos, saldo_pesos, saldo_dolares = _recorrer(filas, compras, cotizacion, entregas, None, tc_ventas)
    facturado_usd = sum(x["deudaOriginal"] for x in salida if x["moneda"] == DOLARES)
    facturado_pesos = sum(x["deudaPesos"] for x in salida if x["moneda"] == DOLARES)
    pactado = False
    if tc_pactado and gobierna == DOLARES and facturado_usd:
        salida, avisos, saldo_pesos, saldo_dolares = _recorrer(filas, compras, cotizacion, entregas, round(facturado_pesos / facturado_usd, 6), tc_ventas)
        pactado = True
    return {"filas": salida, "saldoPesos": round(saldo_pesos, 2), "saldoDolares": round(saldo_dolares, 2), "gobierna": gobierna,
            "saldoGobierna": round(saldo_dolares if gobierna == DOLARES else saldo_pesos, 2),
            # una diferencia de cambio chica no es un problema: hasta US$ 1 o el 0,5 % de lo facturado en dólares (tolerancia del FIFO)
            "toleranciaDolares": round(max(1.0, 0.005 * facturado_usd), 2), "tcPactado": pactado,
            "bimonetaria": any(x["moneda"] == DOLARES for x in salida)
            and any(x["moneda"] == "Pesos" and x["origenTipo"] == "Compras" and x["deudaOriginal"] > 0 for x in salida),
            "tieneDolares": any(x["moneda"] == DOLARES for x in salida), "avisos": sorted(set(avisos))}


_COTIZACION: dict = {"v": None}


def cotizacion_bna() -> CotizacionBNA:
    """Serie del dólar BNA vendedor divisa (se lee una vez por proceso: se completa de a un día)."""
    from src.db.connection import fetch_all

    if _COTIZACION["v"] is None:
        _COTIZACION["v"] = CotizacionBNA({_dia(f["f"]): float(f["v"]) for f in fetch_all(
            "SELECT Fecha AS f, Vend_Divisa AS v FROM dbo.[Dolar BNA] WHERE Vend_Divisa IS NOT NULL", ())})
    return _COTIZACION["v"]


_VISTA: dict = {"t": 0.0, "filas": None, "compras": None, "entregas": None, "tc_ventas": {}}
TTL_VISTA = 120


def invalidar() -> None:
    _VISTA["filas"] = None


def _vista_en_memoria(refrescar: bool = False) -> tuple[dict[int, list], dict[int, dict], dict[tuple[str, int], date]]:
    """La vista completa y las compras, una sola vez cada 2 minutos: leer la vista de un contacto tarda ~1 s y la completa ~0,4 s."""
    import time
    from collections import defaultdict

    from src.db.connection import fetch_all

    if refrescar or _VISTA["filas"] is None or time.time() - _VISTA["t"] > TTL_VISTA:
        por_contacto: dict[int, list] = defaultdict(list)
        for f in fetch_all(
                "SELECT IdContacto, Fecha, Documento, [Nro Documento], Deuda, Credito, Origen, IdOrigen FROM dbo.vw_MovimientosCuenta_Base "
                "WHERE IdContacto IS NOT NULL ORDER BY IdContacto, Fecha, Origen, IdOrigen", ()):
            por_contacto[f["IdContacto"]].append(f)
        compras = {int(c["id"]): {"moneda": c["moneda"], "tc": c["tc"], "ajusta": bool(c["ajusta"])} for c in fetch_all(
            "SELECT IdDeuda AS id, Moneda AS moneda, [Tipo de Cambio] AS tc, [Ajusta Tipo Cambio] AS ajusta FROM dbo.Compras", ())}
        entregas: dict[tuple[str, int], date] = {}
        try:
            for e in fetch_all("SELECT MedioMovimiento AS m, IdMovimiento AS i, FechaEntrega AS f FROM dbo.ChequesEntregados "
                               "WHERE MedioMovimiento IN ('galicia', 'bna') AND IdMovimiento IS NOT NULL AND FechaEntrega IS NOT NULL", ()):
                entregas[("Galicia" if e["m"] == "galicia" else "Banco Nacion", int(e["i"]))] = _dia(e["f"])
        except Exception:
            pass  # todavía no se cargaron los cheques entregados
        tc_ventas = {int(v["i"]): float(v["tc"]) for v in fetch_all(
            "SELECT IdVenta AS i, [Tipo Cambio] AS tc FROM dbo.[Venta Granos] WHERE ISNULL([Tipo Cambio], 0) > 1", ())}
        _VISTA.update(t=time.time(), filas=dict(por_contacto), compras=compras, entregas=entregas, tc_ventas=tc_ventas)
    return _VISTA["filas"], _VISTA["compras"], _VISTA["entregas"]


def cuentas_con_tc_pactado() -> set[int]:
    """Cuentas donde Sergio declaró un tipo de cambio pactado (reglas activas `tc-pactado` de `AuditoriaConocidos`)."""
    from src.features.auditoria_cuentas import conocidos

    return {int(k["clave"]) for k in conocidos.listar() if k["tipo"] == "tc-pactado" and str(k["clave"]).isdigit()}


def cargar_cuenta(id_contacto: int, refrescar: bool = False) -> dict:
    """La cuenta de la vista con el criterio bimonetario (solo lectura, desde la copia en memoria)."""
    filas, compras, entregas = _vista_en_memoria(refrescar)
    return construir(filas.get(id_contacto, []), compras, cotizacion_bna(), entregas, id_contacto in cuentas_con_tc_pactado(), _VISTA.get("tc_ventas"))


def cargar_cuentas(ids: list[int]) -> dict[int, dict]:
    """Varias cuentas con el mismo criterio."""
    if not ids:
        return {}
    filas, compras, entregas = _vista_en_memoria()
    cot = cotizacion_bna()
    pactados = cuentas_con_tc_pactado()
    return {i: construir(filas.get(i, []), compras, cot, entregas, i in pactados, _VISTA.get("tc_ventas")) for i in ids}
