"""Reglas puras de 031 (sin base de datos): arma la lista unificada de
vínculos a partir de las filas crudas de las cinco vías y aplica la cadena
factura ← consumo / valor propio ← débito bancario.

Cada vínculo es un dict con:
  via, origenMovimiento, idMovimiento, tipoDocumento, idDocumento,
  importeArs, enDocumento, enMovimiento, redundante, monedaMezclada,
  idAplicacion, origenCarga, cadena.

- `enDocumento`: cuenta para "cuánto tiene pagado la factura" (FR-017). Los
  consumos imputados y los cheques conciliados cuentan aunque todavía no se
  hayan debitado.
- `enMovimiento`: cuenta para "qué documentos paga este movimiento" (flujo
  de caja). Solo lo efectivamente debitado.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime

MARGEN_DIAS = 60
TOLERANCIA = 0.02
VIAS_CADENA = ("tarjeta", "valor-propio")

_RE_CHEQUE = (
    re.compile(r"48HS\.?\s*BANCOS\s*0*(\d+)", re.IGNORECASE),
    re.compile(r"ECHEQ.*?NRO:?\s*0*(\d+)", re.IGNORECASE),
)

TIPO_TESORERIA = {"Compras": "CompraDeuda", "Impuestos": "Impuesto", "Remuneraciones": "Remuneracion"}


def dia(valor) -> date | None:
    if valor is None:
        return None
    return valor.date() if isinstance(valor, datetime) else valor


def excede(importe: float, total: float) -> bool:
    """Exceso por encima de la tolerancia del 2% (mínimo $1)."""
    return importe - total > max(1.0, abs(total) * TOLERANCIA)


def _vinculo(**campos) -> dict:
    base = {"enDocumento": True, "enMovimiento": False, "redundante": False, "monedaMezclada": False,
            "idAplicacion": None, "origenCarga": None, "cadena": None, "idLinea": None, "idValor": None}
    base.update(campos)
    return base


def numero_cheque(concepto: str | None) -> int | None:
    for patron in _RE_CHEQUE:
        m = patron.search(concepto or "")
        if m:
            return int(m.group(1))
    return None


def emparejar_cheques(movimientos: dict, valores: list[dict]) -> dict[tuple, int]:
    """Débito bancario → IdValor. Número de cheque contenido en el concepto,
    importe ±0,01 y débito ≥ emisión. Con varios candidatos gana el de
    fecha más cercana; cada cheque se usa una sola vez."""
    por_numero: dict[int, list[dict]] = defaultdict(list)
    for v in valores:
        if v.get("numero") is not None:
            por_numero[int(v["numero"])].append(v)
    usados: set[int] = set()
    pares: dict[tuple, int] = {}
    debitos = sorted(((k, m) for k, m in movimientos.items() if (m.get("importe") or 0) < 0),
                     key=lambda km: (dia(km[1]["fecha"]) or date.min, km[0]))
    for clave, m in debitos:
        numero = numero_cheque(m.get("concepto"))
        if numero is None:
            continue
        fecha = dia(m["fecha"])
        candidatos = [v for v in por_numero.get(numero, [])
                      if v["idValor"] not in usados and abs(float(v["importe"]) + float(m["importe"])) <= 0.01
                      and (dia(v.get("fechaEmision")) is None or fecha is None or fecha >= dia(v["fechaEmision"]))]
        if not candidatos:
            continue
        elegido = min(candidatos, key=lambda v: abs(((fecha or date.min) - (dia(v.get("fechaEmision")) or fecha or date.min)).days))
        usados.add(elegido["idValor"])
        pares[clave] = elegido["idValor"]
    return pares


def _importe_ars(importe: float, doc: dict | None, origen_carga: str | None, importe_mov: float | None = None) -> tuple[float, bool]:
    """Una aplicación automática a un documento en dólares guardó el importe
    en us$ contra un movimiento en pesos: se pesifica con el TC de la
    factura (FR-010). Las manuales y las del recálculo FIFO (032) ya están
    en pesos. Solo se considera cargada en us$ si, pesificada,
    sigue entrando en el movimiento (si no, ya estaba en pesos). Las
    manuales se toman como están."""
    if doc and doc.get("moneda") == "Dolares" and origen_carga not in ("manual", "fifo-032") and (doc.get("tc") or 0) > 1:
        pesificado = importe * float(doc["tc"])
        if importe_mov is None or pesificado <= abs(importe_mov) * (1 + TOLERANCIA) + 1:
            return round(pesificado, 2), True
    return round(importe, 2), False


def _importe_origen(raw: dict, origen: str, id_mov: int) -> float | None:
    m = raw.get("movimientos", {}).get((origen, id_mov))
    if m is not None:
        return float(m["importe"] or 0)
    if origen == "tarjetas" and id_mov in raw.get("lineas", {}):
        return raw["lineas"][id_mov].get("importe")
    return raw.get("importesOtros", {}).get((origen, id_mov))


def construir_vinculos(raw: dict) -> list[dict]:
    docs = raw.get("documentos", {})
    lineas = raw.get("lineas", {})
    vinculos: list[dict] = []

    # 1. Nivel documento — las cinco vías.
    tarjeta_por_par: dict[tuple, dict] = {}
    for a in raw.get("aplicaciones", []):
        clave_doc = (a["tipoDocumento"], a["idDocumento"])
        importe, mezclada = _importe_ars(float(a["importe"]), docs.get(clave_doc), a.get("origenCarga"),
                                         _importe_origen(raw, a["origenMovimiento"], a["idMovimiento"]))
        if a["origenMovimiento"] == "tarjetas":
            v = _vinculo(via="tarjeta", origenMovimiento="tarjetas", idMovimiento=a["idMovimiento"],
                         tipoDocumento=a["tipoDocumento"], idDocumento=a["idDocumento"], importeArs=importe,
                         monedaMezclada=mezclada, idAplicacion=a["idAplicacion"], origenCarga=a.get("origenCarga"),
                         idLinea=a["idMovimiento"])
            par = (a["idMovimiento"], a["tipoDocumento"], a["idDocumento"])
            if par not in tarjeta_por_par or importe > tarjeta_por_par[par]["importeArs"]:
                tarjeta_por_par[par] = v
            continue
        vinculos.append(_vinculo(via="aplicacion", origenMovimiento=a["origenMovimiento"], idMovimiento=a["idMovimiento"],
                                 tipoDocumento=a["tipoDocumento"], idDocumento=a["idDocumento"], importeArs=importe,
                                 enMovimiento=True, monedaMezclada=mezclada, idAplicacion=a["idAplicacion"],
                                 origenCarga=a.get("origenCarga")))

    # Consumo → factura se guarda en dos lugares (aplicaciones 'tarjetas' y
    # Tarjetas_Resumenes_Lineas_Compras): el mismo par cuenta una sola vez.
    for lc in raw.get("lineasCompras", []):
        par = (lc["idLinea"], "CompraDeuda", lc["idCompra"])
        v = _vinculo(via="tarjeta", origenMovimiento="tarjetas", idMovimiento=lc["idLinea"], tipoDocumento="CompraDeuda",
                     idDocumento=lc["idCompra"], importeArs=round(float(lc["importe"]), 2), idLinea=lc["idLinea"])
        if par not in tarjeta_por_par or v["importeArs"] > tarjeta_por_par[par]["importeArs"]:
            tarjeta_por_par[par] = v
    vinculos.extend(tarjeta_por_par.values())

    for t in raw.get("tesoreria", []):
        tipo = TIPO_TESORERIA.get(t["tipoDocumento"], t["tipoDocumento"])
        if t["medio"] == "valores-propios":
            vinculos.append(_vinculo(via="valor-propio", origenMovimiento="valores-propios", idMovimiento=t["idMovimiento"],
                                     tipoDocumento=tipo, idDocumento=t["idDocumento"],
                                     importeArs=round(float(t["importe"]), 2), idValor=t["idMovimiento"]))
        else:
            vinculos.append(_vinculo(via="tesoreria", origenMovimiento=t["medio"], idMovimiento=t["idMovimiento"],
                                     tipoDocumento=tipo, idDocumento=t["idDocumento"],
                                     importeArs=round(float(t["importe"]), 2), enMovimiento=True))

    for b in raw.get("backfill", []):
        vinculos.append(_vinculo(via="backfill-impuesto", origenMovimiento=b["medio"], idMovimiento=b["idMovimiento"],
                                 tipoDocumento="Impuesto", idDocumento=b["idImpuesto"],
                                 importeArs=round(float(b["importe"]), 2), enMovimiento=True))

    # 2. Doble imputación (FR-014): si la factura ya está pagada vía tarjeta
    # o valor propio, cualquier vínculo directo de dinero a esa factura sobra.
    con_cadena = {(v["tipoDocumento"], v["idDocumento"]) for v in vinculos if v["via"] in VIAS_CADENA}
    for v in vinculos:
        if v["via"] in ("aplicacion", "tesoreria") and (v["tipoDocumento"], v["idDocumento"]) in con_cadena:
            v["redundante"] = True

    # 3. Nivel movimiento por herencia: débito de resumen y débito de cheque.
    vinculos.extend(_partes_de_resumenes(raw.get("pagosResumen", []), vinculos, lineas))
    pares = emparejar_cheques(raw.get("movimientos", {}), raw.get("valores", []))
    vinculos.extend(_partes_de_cheques(pares, vinculos, raw.get("movimientos", {})))
    return vinculos


def _partes_de_resumenes(pagos: list[dict], vinculos: list[dict], lineas: dict) -> list[dict]:
    imputado: dict[int, dict[tuple, float]] = defaultdict(lambda: defaultdict(float))
    for v in vinculos:
        if v["via"] == "tarjeta" and not v["redundante"]:
            linea = lineas.get(v["idLinea"])
            if linea is not None:
                imputado[linea["idResumen"]][(v["tipoDocumento"], v["idDocumento"])] += v["importeArs"]
    total_pagos: dict[int, float] = defaultdict(float)
    for p in pagos:
        total_pagos[p["idResumen"]] += abs(float(p["importe"]))

    resultado = []
    for p in pagos:
        importe_pago = abs(float(p["importe"]))
        docs = imputado.get(p["idResumen"])
        if not docs or importe_pago <= 0:
            continue
        factor = importe_pago / total_pagos[p["idResumen"]]
        partes = {k: imp * factor for k, imp in docs.items()}
        suma = sum(partes.values())
        if suma > importe_pago:
            partes = {k: imp * importe_pago / suma for k, imp in partes.items()}
        for (tipo, id_doc), imp in partes.items():
            resultado.append(_vinculo(via="tarjeta", origenMovimiento=p["origen"], idMovimiento=p["idMovimiento"],
                                      tipoDocumento=tipo, idDocumento=id_doc, importeArs=round(imp, 2),
                                      enDocumento=False, enMovimiento=True, cadena=f"resumen:{p['idResumen']}"))
    return resultado


def _partes_de_cheques(pares: dict, vinculos: list[dict], movimientos: dict) -> list[dict]:
    por_valor: dict[int, list[dict]] = defaultdict(list)
    for v in vinculos:
        if v["via"] == "valor-propio":
            por_valor[v["idValor"]].append(v)
    resultado = []
    for (origen, id_mov), id_valor in pares.items():
        docs = por_valor.get(id_valor)
        if not docs:
            continue
        debito = abs(float(movimientos[(origen, id_mov)]["importe"]))
        suma = sum(d["importeArs"] for d in docs)
        escala = debito / suma if suma > debito else 1.0
        for d in docs:
            resultado.append(_vinculo(via="valor-propio", origenMovimiento=origen, idMovimiento=id_mov,
                                      tipoDocumento=d["tipoDocumento"], idDocumento=d["idDocumento"],
                                      importeArs=round(d["importeArs"] * escala, 2), enDocumento=False,
                                      enMovimiento=True, cadena=f"valor:{id_valor}"))
    return resultado


def pagado_por_documento(vinculos: list[dict]) -> dict[tuple, float]:
    pagado: dict[tuple, float] = defaultdict(float)
    for v in vinculos:
        if v["enDocumento"] and not v["redundante"]:
            pagado[(v["tipoDocumento"], v["idDocumento"])] += v["importeArs"]
    return {k: round(x, 2) for k, x in pagado.items()}


def imputado_por_via(vinculos: list[dict]) -> dict[tuple, dict[str, float]]:
    resultado: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for v in vinculos:
        if v["enDocumento"]:
            via = v["via"] + (" (redundante)" if v["redundante"] else "")
            resultado[(v["tipoDocumento"], v["idDocumento"])][via] += v["importeArs"]
    return resultado


def documentos_de_movimiento(vinculos: list[dict]) -> dict[tuple, list[dict]]:
    """Formato compatible con `partes_desde_aplicaciones` (030), con `via`."""
    resultado: dict[tuple, list[dict]] = defaultdict(list)
    for v in vinculos:
        if v["enMovimiento"] and not v["redundante"]:
            resultado[(v["origenMovimiento"], v["idMovimiento"])].append(
                {"tipoDocumento": v["tipoDocumento"], "idDocumentoAplicado": v["idDocumento"],
                 "importeAplicado": v["importeArs"], "via": v["via"]})
    return dict(resultado)
