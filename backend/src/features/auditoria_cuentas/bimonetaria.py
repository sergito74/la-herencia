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


def valuar_usd_por_comprobante(filas: list[dict], compras: dict[int, dict],
                               valuaciones: dict[tuple[str, int], float] | None = None,
                               abiertos: list | None = None) -> dict[tuple[str, int], float]:
    """Dólares de cada fila en pesos de una cuenta que el proveedor lleva en dólares (regla `usd-tc-comprobante`).

    Los comprobantes en dólares (y las filas con valuación explícita) son deuda o crédito en US$ a su tipo de cambio.
    Cada fila en pesos cancela, por antigüedad, los comprobantes en dólares de signo contrario ya vencidos a la fecha
    (Cargill compensa con la cosecha las facturas vencidas y paga el resto en pesos) y vale lo que cancela. Una nota de
    crédito en dólares se pasa a pesos a su propio tipo de cambio y se aplica primero a su factura relacionada
    (CompraDocumentosRelacionados), aunque no haya vencido (Cargill: NC 1126-6320 US$ 304,39 x 62,21 cancela US$ 315,23
    de la FC 2786 a 60,07). Una nota de diferencia de cambio en pesos vinculada a un comprobante en dólares mueve
    pesos / TC de ese comprobante (Cargill: ND 1126-13117 $2.225,58 devuelve US$ 49,71 a la FC 1978 a 44,77); sin
    comprobante relacionado en dólares, la nota cancela como cualquier peso;
    (pesos / TC del comprobante); lo que sobra se compensa con otras filas en pesos sin mover dólares. Las notas en
    pesos de ajuste de tipo de cambio solo se compensan en pesos. Devuelve (Origen, IdOrigen) -> dólares (sin signo).
    """
    from collections import deque

    valuaciones = valuaciones or {}
    usd: deque = deque()   # [signo, dólares pendientes, tc, vencimiento, IdOrigen]
    pesos: deque = deque()  # [clave, signo, pesos pendientes, cancela_usd, comprobantes relacionados]
    salida: dict[tuple[str, int], float] = {}

    def aplicar(p: list, d: list) -> None:
        aplicado = min(p[2], d[1] * d[2])
        p[2] -= aplicado
        d[1] -= aplicado / d[2]
        salida[p[0]] = salida.get(p[0], 0.0) + aplicado / d[2]

    def cruzar(hoy: date) -> None:
        for p in pesos:
            if not p[3]:
                continue
            for d in usd:
                if p[2] > 1e-6 and d[4] in p[4] and d[0] == -p[1] and d[1] > 1e-9:
                    aplicar(p, d)
            for d in usd:
                if p[2] <= 1e-6:
                    break
                if d[0] == -p[1] and d[1] > 1e-9 and (d[3] is None or d[3] <= hoy):
                    aplicar(p, d)
        for a in usd:  # notas en dólares que se compensan entre sí (NC que anula una ND) sin pasar por pesos
            for b in usd:
                if a[1] > 1e-9 and b[1] > 1e-9 and a[0] == -b[0] and a[4] is not None and a[4] == b[4]:
                    m = min(a[1], b[1])
                    a[1] -= m
                    b[1] -= m
        for d in [d for d in usd if d[1] <= 1e-9]:
            usd.remove(d)
        vivos = [p for p in pesos if p[2] > 1e-6]
        for a in vivos:
            for b in vivos:
                if a[2] > 1e-6 and b[2] > 1e-6 and a[1] == -b[1]:
                    m = min(a[2], b[2])
                    a[2] -= m
                    b[2] -= m
        pesos.clear()
        pesos.extend(p for p in vivos if p[2] > 1e-6)

    for f in filas:
        clave = (f["Origen"], int(f["IdOrigen"]))
        importe = float(f["Credito"] or 0) - float(f["Deuda"] or 0)
        if abs(importe) < 1e-9 or f.get("SoloUSD"):
            continue
        signo = 1 if importe > 0 else -1
        compra = compras.get(int(f["IdOrigen"]), {}) if f["Origen"] == "Compras" else {}
        hoy = _dia(f["Fecha"])
        if compra.get("moneda") == DOLARES and (compra.get("tc") or 0) > 1 and signo > 0:
            pesos.append([clave, signo, abs(importe) * float(compra["tc"]), True, compra.get("rel") or set()])
        elif compra.get("moneda") == DOLARES and (compra.get("tc") or 0) > 1:
            usd.append([signo, abs(importe), float(compra["tc"]), _dia(compra.get("vto")) or hoy, int(f["IdOrigen"])])
        elif valuaciones.get(clave):
            # valuación explícita (p.ej. anticipo financiero en US$): se cancela por su propio camino, no con los pesos del día
            usd.append([signo, abs(valuaciones[clave]), abs(importe) / abs(valuaciones[clave]), date.max, None])
        elif compra.get("ajusta") and any(compras.get(r, {}).get("moneda") == DOLARES and (compras[r].get("tc") or 0) > 1
                                          for r in compra.get("rel") or ()):
            rel = next(r for r in sorted(compra["rel"]) if compras.get(r, {}).get("moneda") == DOLARES and (compras[r].get("tc") or 0) > 1)
            tc = float(compras[rel]["tc"])
            salida[clave] = abs(importe) / tc
            usd.append([signo, abs(importe) / tc, tc, max(hoy, _dia(compras[rel].get("vto")) or hoy), rel])
        else:
            # una nota de ajuste en pesos sin comprobante en dólares relacionado (p.ej. diferencia de cambio de un anticipo
            # financiero que en el sistema está en pesos) cancela como cualquier peso
            pesos.append([clave, signo, abs(importe), True, compra.get("rel") or set()])
        cruzar(hoy)
    if abiertos is not None:
        abiertos.extend([{"tipo": "usd", "signo": d[0], "dolares": d[1], "tc": d[2], "vencimiento": d[3], "idCompra": d[4]} for d in usd] +
                        [{"tipo": "pesos", "clave": p[0], "signo": p[1], "pesos": p[2]} for p in pesos])
    return salida


def _recorrer(filas: list[dict], compras: dict[int, dict], cotizacion: CotizacionBNA, entregas: dict[tuple[str, int], date] | None,
              tc_pagos: float | None, tc_ventas: dict[int, float] | None = None,
              valuaciones: dict[tuple[str, int], float] | None = None,
              usd_creditos: dict[tuple[str, int], float] | None = None) -> tuple[list[dict], list[str], float, float]:
    """Pasa las filas a pesos y dólares. `tc_pagos`: si viene, los importes en pesos se pasan a dólares con ese tipo de cambio
    (el pactado en las facturas) en vez del dólar BNA del día anterior.

    Dos criterios (decisión de Sergio, 08/10/2026, hallados en FEDEA contra su libro en dólares): (1) un documento en pesos marcado
    como ajuste de tipo de cambio (`Ajusta Tipo Cambio`) corrige solo la cuenta en pesos y no mueve los dólares; (2) una venta de
    granos se pasa a dólares con el tipo de cambio de la propia venta (`tc_ventas`: IdVenta -> TC) y no con el dólar BNA.
    (3) `valuaciones`: (Origen, IdOrigen) -> dólares que el proveedor acreditó o debitó en su propio libro por esa fila (tabla
    `ValuacionProveedor`); si existe, manda sobre todo lo anterior y conserva el signo de la fila."""
    saldo_pesos = saldo_dolares = 0.0
    salida, avisos = [], []
    for f in filas:
        deuda, credito = float(f["Deuda"] or 0), float(f["Credito"] or 0)
        fecha = _dia(f["Fecha"])
        compra = compras.get(int(f["IdOrigen"])) if f["Origen"] == "Compras" else None
        solo_usd = bool(f.get("SoloUSD"))
        en_dolares = solo_usd or bool(compra and compra.get("moneda") == DOLARES)
        entrega = (entregas or {}).get((f["Origen"], int(f["IdOrigen"])))
        tc_venta = (tc_ventas or {}).get(int(f["IdOrigen"])) if f["Origen"] == "Venta Granos" else None
        tc_dia = tc_pagos or tc_venta or cotizacion.dia_anterior(entrega or fecha)
        ajuste_pesos = bool(compra and compra.get("ajusta") and not en_dolares)
        fila = {"fecha": fecha, "documento": f["Documento"], "numeroDocumento": f["Nro Documento"], "origenTipo": f["Origen"],
                "idOrigen": int(f["IdOrigen"]), "moneda": DOLARES if en_dolares else "Pesos", "deudaOriginal": deuda, "creditoOriginal": credito,
                "tipoDeCambio": None, "tcEstimado": False, "fechaEntrega": entrega}
        if solo_usd:
            # Efecto de una aplicación externa: no duplica su origen en pesos.
            deuda_p = credito_p = 0.0
            deuda_d, credito_d = deuda, credito
        elif en_dolares:
            tc = float(compra["tc"]) if (compra.get("tc") or 0) > 1 else None
            if tc is None:
                tc, fila["tcEstimado"] = tc_dia, True
                avisos.append(f"El documento {f['Nro Documento']} está en dólares y no tiene tipo de cambio: se usó el dólar BNA del día anterior"
                              if tc_dia else f"El documento {f['Nro Documento']} está en dólares y no tiene tipo de cambio")
            fila["tipoDeCambio"] = tc
            deuda_p, credito_p = (round(deuda * tc, 2), round(credito * tc, 2)) if tc else (0.0, 0.0)
            deuda_d, credito_d = deuda, credito
            clave = (f["Origen"], int(f["IdOrigen"]))
            if usd_creditos and clave in usd_creditos:  # NC en US$ aplicada en pesos (regla usd-tc-comprobante)
                credito_d = round(usd_creditos[clave] * (1 if credito >= 0 else -1), 4) if credito else 0.0
        else:
            deuda_p, credito_p = deuda, credito
            deuda_d, credito_d = (round(deuda / tc_dia, 4), round(credito / tc_dia, 4)) if tc_dia else (0.0, 0.0)
            if ajuste_pesos:
                deuda_d = credito_d = 0.0
            valuada = (valuaciones or {}).get((f["Origen"], int(f["IdOrigen"])))
            if valuada is not None:
                deuda_d = round(valuada, 4) if deuda else 0.0
                credito_d = round(valuada * (1 if credito >= 0 else -1), 4) if credito else 0.0
        saldo_pesos = round(saldo_pesos + credito_p - deuda_p, 4)
        saldo_dolares = round(saldo_dolares + credito_d - deuda_d, 4)
        fila.update(deudaPesos=deuda_p, creditoPesos=credito_p, saldoPesos=round(saldo_pesos, 2), saldoDolares=round(saldo_dolares, 2))
        salida.append(fila)
    return salida, avisos, saldo_pesos, saldo_dolares


def construir(filas: list[dict], compras: dict[int, dict], cotizacion: CotizacionBNA, entregas: dict[tuple[str, int], date] | None = None,
              tc_pactado: bool = False, tc_ventas: dict[int, float] | None = None,
              valuaciones: dict[tuple[str, int], float] | None = None,
              efectos_valuacion: dict[tuple[str, int], dict] | None = None, usd_tc_comprobante: bool = False) -> dict:
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
    if efectos_valuacion:
        # Los dólares nacen al aplicar el crédito, no al emitir su origen.
        # Agrupar las partes del mismo comprobante; nunca mutar la entrada.
        valuaciones = dict(valuaciones or {})
        eventos: dict[tuple, dict] = {}
        origenes = []
        for f in filas:
            origenes.append(f)
            key = (f["Origen"], int(f["IdOrigen"]))
            efecto = efectos_valuacion.get(key)
            if efecto is None or key not in valuaciones:
                continue
            fecha_origen = _dia(efecto.get("fechaOrigen")) or _dia(f["Fecha"])
            partes = efecto.get("eventos")
            if partes is None:
                partes = [{"fecha": efecto["fecha"], "documento": efecto["documento"], "dolares": abs(float(valuaciones[key]))}]
            if not partes or abs(sum(float(p["dolares"]) for p in partes)-abs(float(valuaciones[key]))) > .0001:
                raise ValueError("Las aplicaciones USD deben sumar la valuación del origen")
            for parte in partes:
                fecha = _dia(parte["fecha"])
                if fecha is None or fecha < fecha_origen:
                    raise ValueError("La aplicación USD no puede preceder al documento de origen")
            if efecto.get("fechaOrigen") is not None:
                f = dict(f)
                f["Fecha"] = fecha_origen
                origenes[-1] = f
            if efecto.get("pesos") is not None:
                # Importe/fecha reconocidos en el libro del proveedor. El
                # registro bancario sigue intacto en su fuente y auditoría.
                f = dict(f)
                f["Fecha"] = fecha_origen if efecto.get("fechaOrigen") is not None else _dia(partes[0]["fecha"])
                for campo in ("Deuda", "Credito"):
                    if f.get(campo):
                        f[campo] = abs(float(efecto["pesos"])) * (1 if f[campo] > 0 else -1)
                origenes[-1] = f
            for parte in partes:
                fecha = _dia(parte["fecha"])
                group = (fecha, parte["documento"])
                event = eventos.setdefault(group, {"Fecha": fecha, "Documento": "Aplicación proveedor",
                    "Nro Documento": parte["documento"], "Deuda": 0.0, "Credito": 0.0,
                    "Origen": "Aplicacion proveedor", "IdOrigen": int(f["IdOrigen"]), "SoloUSD": True})
                importe = float(parte["dolares"])
                if float(f["Deuda"] or 0):
                    event["Deuda"] = round(event["Deuda"] + importe, 4)
                elif float(f["Credito"] or 0):
                    event["Credito"] = round(event["Credito"] + importe, 4)
            valuaciones[key] = 0.0
        filas = sorted([*origenes, *eventos.values()], key=lambda f: (_dia(f["Fecha"]), f["Origen"], int(f["IdOrigen"])))
    gobierna = moneda_que_gobierna(filas, compras)
    usd_creditos: dict[tuple[str, int], float] = {}
    if usd_tc_comprobante:
        # Regla `usd-tc-comprobante`: el proveedor lleva la cuenta en dólares; los pesos valen lo que cancelan.
        auto = valuar_usd_por_comprobante(filas, compras, valuaciones)
        valuaciones = dict(valuaciones or {})
        for f in filas:
            clave = (f["Origen"], int(f["IdOrigen"]))
            compra = compras.get(int(f["IdOrigen"]), {}) if f["Origen"] == "Compras" else {}
            if compra.get("moneda") != DOLARES and clave not in valuaciones:
                valuaciones[clave] = auto.get(clave, 0.0)
            elif compra.get("moneda") == DOLARES and float(f["Credito"] or 0) - float(f["Deuda"] or 0) > 0:
                usd_creditos[clave] = auto.get(clave, 0.0)
        gobierna = DOLARES
    salida, avisos, saldo_pesos, saldo_dolares = _recorrer(filas, compras, cotizacion, entregas, None, tc_ventas, valuaciones, usd_creditos)
    facturado_usd = sum(x["deudaOriginal"] for x in salida if x["moneda"] == DOLARES)
    facturado_pesos = sum(x["deudaPesos"] for x in salida if x["moneda"] == DOLARES)
    pactado = False
    if tc_pactado and gobierna == DOLARES and facturado_usd:
        salida, avisos, saldo_pesos, saldo_dolares = _recorrer(filas, compras, cotizacion, entregas, round(facturado_pesos / facturado_usd, 6), tc_ventas, valuaciones)
        pactado = True
    return {"filas": salida, "saldoPesos": round(saldo_pesos, 2), "saldoDolares": round(saldo_dolares, 2), "gobierna": gobierna,
            "saldoGobierna": round(saldo_dolares if gobierna == DOLARES else saldo_pesos, 2),
            # una diferencia de cambio chica no es un problema: hasta US$ 1 o el 0,5 % de lo facturado en dólares (tolerancia del FIFO)
            "toleranciaDolares": round(max(1.0, 0.005 * facturado_usd), 2), "tcPactado": pactado, "usdTcComprobante": usd_tc_comprobante,
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


_VISTA: dict = {"t": 0.0, "filas": None, "compras": None, "entregas": None, "tc_ventas": {}, "valuaciones": {}}
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
        compras = {int(c["id"]): {"moneda": c["moneda"], "tc": c["tc"], "ajusta": bool(c["ajusta"]), "vto": c["vto"]} for c in fetch_all(
            "SELECT c.IdDeuda AS id, c.Moneda AS moneda, c.[Tipo de Cambio] AS tc, c.[Ajusta Tipo Cambio] AS ajusta, v.vto "
            "FROM dbo.Compras c LEFT JOIN (SELECT IdCompra, MAX([Fecha de vencimiento]) AS vto FROM dbo.[Vencimiento Compras] GROUP BY IdCompra) v "
            "ON v.IdCompra = c.IdDeuda", ())}
        try:
            for r in fetch_all("SELECT IdCompra AS a, IdCompraRelacionada AS b FROM dbo.CompraDocumentosRelacionados", ()):
                for x, y in ((int(r["a"]), int(r["b"])), (int(r["b"]), int(r["a"]))):
                    if x in compras:
                        compras[x].setdefault("rel", set()).add(y)
        except Exception:
            pass  # todavía no existe la tabla de documentos relacionados
        entregas: dict[tuple[str, int], date] = {}
        try:
            for e in fetch_all("SELECT MedioMovimiento AS m, IdMovimiento AS i, FechaEntrega AS f FROM dbo.ChequesEntregados "
                               "WHERE MedioMovimiento IN ('galicia', 'bna') AND IdMovimiento IS NOT NULL AND FechaEntrega IS NOT NULL", ()):
                entregas[("Galicia" if e["m"] == "galicia" else "Banco Nacion", int(e["i"]))] = _dia(e["f"])
        except Exception:
            pass  # todavía no se cargaron los cheques entregados
        tc_ventas = {int(v["i"]): float(v["tc"]) for v in fetch_all(
            "SELECT IdVenta AS i, [Tipo Cambio] AS tc FROM dbo.[Venta Granos] WHERE ISNULL([Tipo Cambio], 0) > 1", ())}
        valuaciones: dict[tuple[str, int], float] = {}
        try:
            for v in fetch_all("SELECT Origen AS o, IdOrigen AS i, Dolares AS d FROM dbo.ValuacionProveedor", ()):
                valuaciones[(v["o"], int(v["i"]))] = abs(float(v["d"]))
        except Exception:
            pass  # todavía no se creó la tabla
        efectos = {}
        # Columnas opcionales agregadas por la conciliación036; instalación
        # anterior mantiene sus valuaciones inmediatas sin perderlas.
        if fetch_all("SELECT COL_LENGTH('dbo.ValuacionProveedor','FechaEfectoUSD') AS n", ())[0]["n"] is not None:
            for v in fetch_all("SELECT Origen AS o,IdOrigen AS i,FechaEfectoUSD AS f,DocumentoEfectoUSD AS d "
                               "FROM dbo.ValuacionProveedor WHERE FechaEfectoUSD IS NOT NULL", ()):
                efectos[(v["o"], int(v["i"]))] = {"fecha": _dia(v["f"]), "documento": v["d"]}
            if fetch_all("SELECT COL_LENGTH('dbo.ValuacionProveedor','ImporteReconocidoPesos') AS n", ())[0]["n"] is not None:
                for v in fetch_all("SELECT Origen AS o,IdOrigen AS i,ImporteReconocidoPesos AS p FROM dbo.ValuacionProveedor "
                                   "WHERE FechaEfectoUSD IS NOT NULL AND ImporteReconocidoPesos IS NOT NULL", ()):
                    efectos[(v["o"], int(v["i"]))]["pesos"] = float(v["p"])
        if fetch_all("SELECT OBJECT_ID('dbo.ValuacionProveedorEventos','U') AS n", ())[0]["n"] is not None:
            for v in fetch_all("SELECT Origen AS o,IdOrigen AS i,IdContacto AS c,Fecha AS f,Documento AS d,Dolares AS usd FROM dbo.ValuacionProveedorEventos ORDER BY Fecha,Documento", ()):
                key = (v['o'], int(v['i']))
                if key not in valuaciones:
                    raise ValueError('Aplicaciones proveedor sin valuación de origen')
                if not any(f['Origen']==v['o'] and int(f['IdOrigen'])==int(v['i']) for f in por_contacto.get(int(v['c']), [])):
                    raise ValueError('Aplicación proveedor ajena al contacto del origen')
                effect = efectos.setdefault(key, {})
                effect.setdefault('eventos', []).append({'fecha':_dia(v['f']), 'documento':v['d'], 'dolares':float(v['usd'])})
        if fetch_all("SELECT COL_LENGTH('dbo.ValuacionProveedor','FechaReconocimientoPesos') AS n", ())[0]["n"] is not None:
            for v in fetch_all('SELECT Origen AS o,IdOrigen AS i,FechaReconocimientoPesos AS f FROM dbo.ValuacionProveedor WHERE FechaReconocimientoPesos IS NOT NULL', ()):
                key=(v['o'],int(v['i']))
                if key in efectos: efectos[key]['fechaOrigen']=_dia(v['f'])
        _VISTA.update(t=time.time(), filas=dict(por_contacto), compras=compras, entregas=entregas, tc_ventas=tc_ventas, valuaciones=valuaciones, efectos_valuacion=efectos)
    return _VISTA["filas"], _VISTA["compras"], _VISTA["entregas"]


def cuentas_con_tc_pactado() -> set[int]:
    """Cuentas donde Sergio declaró un tipo de cambio pactado (reglas activas `tc-pactado` de `AuditoriaConocidos`)."""
    from src.features.auditoria_cuentas import conocidos

    return {int(k["clave"]) for k in conocidos.listar() if k["tipo"] == "tc-pactado" and str(k["clave"]).isdigit()}


def cuentas_usd_tc_comprobante() -> set[int]:
    """Cuentas que el proveedor lleva en dólares al TC de cada comprobante (reglas activas `usd-tc-comprobante`)."""
    from src.features.auditoria_cuentas import conocidos

    return {int(k["clave"]) for k in conocidos.listar() if k["tipo"] == "usd-tc-comprobante" and str(k["clave"]).isdigit()}


def cargar_cuenta(id_contacto: int, refrescar: bool = False) -> dict:
    """La cuenta de la vista con el criterio bimonetario (solo lectura, desde la copia en memoria)."""
    filas, compras, entregas = _vista_en_memoria(refrescar)
    return construir(filas.get(id_contacto, []), compras, cotizacion_bna(), entregas, id_contacto in cuentas_con_tc_pactado(), _VISTA.get("tc_ventas"),
                     _VISTA.get("valuaciones"), _VISTA.get("efectos_valuacion"), id_contacto in cuentas_usd_tc_comprobante())


def cargar_cuentas(ids: list[int]) -> dict[int, dict]:
    """Varias cuentas con el mismo criterio."""
    if not ids:
        return {}
    filas, compras, entregas = _vista_en_memoria()
    cot = cotizacion_bna()
    pactados = cuentas_con_tc_pactado()
    en_usd = cuentas_usd_tc_comprobante()
    return {i: construir(filas.get(i, []), compras, cot, entregas, i in pactados, _VISTA.get("tc_ventas"), _VISTA.get("valuaciones"),
                         _VISTA.get("efectos_valuacion"), i in en_usd) for i in ids}
