"""Detector de pagos sin factura — 036 (research D1 y D2; funciones puras, no leen la base).

Empareja cada pago con la factura (o combinación de facturas) que suma su importe, en una ventana de fechas. Lo que queda
sin emparejar son los pagos sin factura; las facturas que quedan sin pago son facturas sin pago.

Pasadas, en este orden:
  1. un pago contra 1 a 4 facturas con la misma suma (diferencia de hasta $1);
  2. pago más una retención cercana contra 1 a 4 facturas;
  3. FIFO parcial: lo que sobra se aplica a las facturas libres más viejas de la ventana (pagos que cubren muchas facturas,
     o un cobro repartido en varios pagos); el resto es pago sin factura;
  4. las retenciones que sobran se asocian al pago sin factura más cercano (el total de la factura esperada es pago + retención).

En clientes y cuentas mixtas los papeles se invierten (research D1): el cobro es el "pago" y el documento de venta es la
"factura". Cada cuenta se separa en un lado proveedor y un lado cliente según el origen y el signo de cada movimiento.
"""

from __future__ import annotations

import itertools
from datetime import date, timedelta
from statistics import median

from src.features.revision_cuentas.datos import ORIGENES_DOCUMENTO, ORIGENES_VENTA, medio_de_origen, sentido_de_cuenta

TOLERANCIA = 1.0                 # diferencia máxima, en pesos, para dar por iguales una suma de facturas y un pago
MINIMO = 0.005                   # por debajo de esto un movimiento no cuenta
DIAS_ANTES_EXACTO = 600          # una factura puede ser hasta 600 días anterior al pago
DIAS_DESPUES = 7                 # ... y hasta 7 días posterior
DIAS_ANTES_FIFO = 730            # el FIFO parcial mira hasta 24 meses atrás (mismo plazo que la regla de plazo)
DIAS_RETENCION = 45              # una retención se asocia a un pago de hasta 45 días de diferencia
CANDIDATAS = 14                  # facturas libres más cercanas en fecha que se prueban en las combinaciones
MAX_COMBINACION = 4              # máximo de facturas que cubre un pago en el emparejamiento exacto
LAG_POR_DEFECTO = 7              # días entre factura y pago si la cuenta no tiene parejas (research D2)
MARGEN_FECHA = 4                 # el rango de la fecha esperada es la mediana ± 4 días
CORTE_ANTIGUO = date(2021, 1, 1) # lo anterior se informa aparte (research D8)
ORIGENES_RETENCION = frozenset({"Retenciones", "Ret. IVA Granos", "Ret. Ventas Hacienda"})
APERTURA_ACCESS = date(2011, 1, 1)


def _neto(m: dict) -> float:
    return round(float(m["credito"]) - float(m["deuda"]), 2)


def separar_lados(movimientos: list[dict]) -> dict[str, dict]:
    """Separa los movimientos en documentos, pagos y retenciones del lado proveedor y del lado cliente.

    El signo manda: un crédito negativo cuenta como deuda y al revés (por ejemplo un asiento de efectivo con crédito
    negativo es parte de un cobro). `neto` = crédito − deuda.
    """
    lados = {"proveedor": {"docs": [], "pagos": [], "retenciones": []}, "cliente": {"docs": [], "pagos": [], "retenciones": []}}
    sentido = sentido_de_cuenta(movimientos)
    for m in movimientos:
        neto = _neto(m)
        if abs(neto) < MINIMO:
            continue
        origen = m["origen"]
        ev = {"fecha": m["fecha"], "importe": abs(neto), "origen": origen, "idOrigen": m["idOrigen"], "nro": m.get("nro"),
              "restante": abs(neto), "usada": False}
        if origen in ORIGENES_VENTA:
            lado, rol = "cliente", ("docs" if neto > 0 else "pagos")
        elif origen in ORIGENES_DOCUMENTO:
            lado, rol = "proveedor", ("docs" if neto < 0 else "pagos")
        elif sentido == "proveedor":
            # cuenta de proveedor: un pago es crédito; lo que nos devuelve el proveedor (neto negativo) funciona como un documento
            lado, rol = "proveedor", ("pagos" if neto > 0 else "docs")
        elif sentido == "cliente":
            # cuenta de cliente: un cobro es deuda (neto negativo); lo que le devolvemos (neto positivo) funciona como un documento
            lado, rol = "cliente", ("pagos" if neto < 0 else "docs")
        else:
            lado, rol = ("proveedor", "pagos") if neto > 0 else ("cliente", "pagos")
        if rol == "pagos" and origen in ORIGENES_RETENCION:
            rol = "retenciones"
        lados[lado][rol].append(ev)
    return lados


def _candidatas(docs: list[dict], fecha: date, dias_antes: int) -> list[dict]:
    desde, hasta = fecha - timedelta(days=dias_antes), fecha + timedelta(days=DIAS_DESPUES)
    libres = [d for d in docs if not d["usada"] and d["restante"] > TOLERANCIA and desde <= d["fecha"] <= hasta]
    return sorted(libres, key=lambda d: abs((fecha - d["fecha"]).days))[:CANDIDATAS]


def _combinacion(docs: list[dict], fecha: date, objetivo: float) -> tuple[dict, ...] | None:
    candidatas = _candidatas(docs, fecha, DIAS_ANTES_EXACTO)
    for k in range(1, MAX_COMBINACION + 1):
        for comb in itertools.combinations(candidatas, k):
            if abs(sum(d["importe"] for d in comb) - objetivo) <= TOLERANCIA:
                return comb
    return None


def _lag_mediano(parejas: list[tuple[date, int]], fecha: date) -> int:
    """Mediana de días factura→pago de las parejas de los 24 meses anteriores al pago (7 si no hay)."""
    recientes = [lag for f, lag in parejas if fecha - timedelta(days=DIAS_ANTES_FIFO) <= f <= fecha]
    return int(round(median(recientes))) if recientes else LAG_POR_DEFECTO


def _emparejar_lado(docs: list[dict], pagos: list[dict], retenciones: list[dict]) -> dict:
    pagos = sorted(pagos, key=lambda p: (p["fecha"], p["idOrigen"]))
    parejas: list[tuple[date, int]] = []   # (fecha del pago, días hasta la factura más nueva de la combinación)
    sin_emparejar: list[dict] = []

    # Pasadas 1 y 2: emparejamiento exacto, con y sin retención
    for p in pagos:
        comb = _combinacion(docs, p["fecha"], p["importe"])
        retencion = None
        if comb is None:
            cercanas = sorted((r for r in retenciones if not r["usada"] and abs((r["fecha"] - p["fecha"]).days) <= DIAS_RETENCION),
                              key=lambda r: abs((r["fecha"] - p["fecha"]).days))
            for r in cercanas:
                comb = _combinacion(docs, p["fecha"], p["importe"] + r["importe"])
                if comb is not None:
                    retencion = r
                    break
        if comb is None:
            sin_emparejar.append(p)
            continue
        for d in comb:
            d["usada"], d["restante"] = True, 0.0
        if retencion is not None:
            retencion["usada"] = True
        parejas.append((p["fecha"], (p["fecha"] - max(d["fecha"] for d in comb)).days))

    # Pasada 3: FIFO parcial de lo que sobra contra las facturas libres más viejas de la ventana
    sin_factura: list[dict] = []
    for p in sin_emparejar:
        resto = p["importe"]
        desde, hasta = p["fecha"] - timedelta(days=DIAS_ANTES_FIFO), p["fecha"] + timedelta(days=DIAS_DESPUES)
        for d in sorted((d for d in docs if d["restante"] > TOLERANCIA and desde <= d["fecha"] <= hasta), key=lambda d: (d["fecha"], d["idOrigen"])):
            if resto <= TOLERANCIA:
                break
            usado = min(resto, d["restante"])
            d["restante"] = round(d["restante"] - usado, 2)
            d["usada"] = d["restante"] <= TOLERANCIA
            resto = round(resto - usado, 2)
        if resto > TOLERANCIA:
            sin_factura.append({**p, "importe": resto, "parcial": resto < p["importe"] - TOLERANCIA, "confianza": "alta" if resto == p["importe"] else "media"})
    # Pasada 4: las retenciones que sobran se asocian al pago sin factura más cercano (el total esperado es pago + retención)
    for r in retenciones:
        if r["usada"]:
            continue
        cercanos = sorted((p for p in sin_factura if "retencion" not in p and abs((r["fecha"] - p["fecha"]).days) <= DIAS_RETENCION),
                          key=lambda p: abs((r["fecha"] - p["fecha"]).days))
        if cercanos:
            cercanos[0]["retencion"] = r["importe"]
            r["usada"] = True
    for r in retenciones:
        if not r["usada"]:
            sin_factura.append({**r, "parcial": False, "confianza": "alta", "esRetencion": True})
    return {"sin_factura": sin_factura, "docs_sin_pago": [d for d in docs if d["restante"] > TOLERANCIA], "parejas": parejas}


def detectar(movimientos: list[dict]) -> dict:
    """Pagos sin factura, facturas sin pago y control de consistencia de una cuenta.

    `movimientos`: lista de `datos.movimientos_de_cuenta` (fecha, origen, idOrigen, nro, deuda, credito).
    """
    lados = separar_lados(movimientos)
    pagos_sin: list[dict] = []
    facturas_sin: list[dict] = []
    explicado = 0.0
    for lado, g in lados.items():
        r = _emparejar_lado(g["docs"], g["pagos"], g["retenciones"])
        for p in r["sin_factura"]:
            retencion = round(p.get("retencion", 0.0), 2)
            lag = _lag_mediano(r["parejas"], p["fecha"])
            pagos_sin.append({
                "lado": lado, "origen": p["origen"], "medio": medio_de_origen(p["origen"]), "idMovimiento": p["idOrigen"],
                "fecha": p["fecha"], "importe": round(p["importe"], 2),
                "retencionAsociada": retencion or None, "importeEsperadoFactura": round(p["importe"] + retencion, 2),
                "fechaEsperadaDesde": p["fecha"] - timedelta(days=lag + MARGEN_FECHA),
                "fechaEsperadaHasta": p["fecha"] - timedelta(days=max(lag - MARGEN_FECHA, 0)),
                "confianza": p["confianza"], "anteriorA2021": p["fecha"] < CORTE_ANTIGUO, "parcial": p.get("parcial", False),
            })
            explicado += (p["importe"] + retencion) * (1 if lado == "proveedor" else -1)
        for d in r["docs_sin_pago"]:
            facturas_sin.append({"lado": lado, "origen": d["origen"], "idOrigen": d["idOrigen"], "numero": d["nro"], "fecha": d["fecha"],
                                 "importe": round(d["restante"], 2)})
            explicado += -d["restante"] if lado == "proveedor" else d["restante"]
    saldo = round(sum(_neto(m) for m in movimientos), 2)
    total_pagos = round(sum(p["importe"] + (p["retencionAsociada"] or 0) for p in pagos_sin), 2)
    total_facturas = round(sum(f["importe"] for f in facturas_sin), 2)
    primera = min((m["fecha"] for m in movimientos), default=None)
    return {
        "pagos": sorted(pagos_sin, key=lambda p: (p["fecha"], p["idMovimiento"])),
        "facturasSinPago": sorted(facturas_sin, key=lambda f: (f["fecha"], f["idOrigen"])),
        "consistencia": {"pagosSinFactura": total_pagos, "facturasSinPago": total_facturas, "saldo": saldo,
                         # cada emparejamiento puede dejar centavos de redondeo: un centavo por movimiento más $1
                         "cierra": abs(saldo - explicado) <= TOLERANCIA + 0.01 * len(movimientos),
                         "sinApertura": primera is not None and primera < APERTURA_ACCESS},
    }
