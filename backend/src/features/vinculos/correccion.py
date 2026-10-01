"""Propuesta de corrección (031, US2). Función pura: a partir de los
hallazgos arma los ítems de un lote — anular, pesificar y reemplazos — con
su grupo (motivo/certeza). No escribe nada; `lotes.py` persiste y aplica.

Reglas acordadas con Sergio:
- Nunca se tocan aplicaciones manuales (FR-009).
- Doble imputación y moneda mezclada: certeza alta. Fecha incoherente:
  alta si el pago es más de 365 días anterior a la factura, media si no.
- Por cada anulación se busca un reemplazo en los dos sentidos (FR-016):
  otro movimiento para la factura que quedó impaga y otra factura para el
  movimiento que quedó libre. Mismo contacto, fecha coherente (margen de
  60 días) y saldo libre compatible (±2%). Con más de un candidato, el
  reemplazo es ambiguo y se elige de a uno. Dentro del lote cada candidato
  se usa una sola vez.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from src.features.vinculos.cadenas import MARGEN_DIAS, TOLERANCIA, dia
from src.features.vinculos.control import dias_antes

DIAS_CERTEZA_ALTA = 365
MAX_CANDIDATOS = 10
_COMPRAS = ("CompraDeuda",)
_VENTAS = ("VentaHacienda", "VentaGranos")
_BANCOS = ("bna", "galicia")


def _tol(importe: float) -> float:
    return max(1.0, abs(importe) * TOLERANCIA)


def _item(grupo, accion, v, motivo, importe=None, **extra) -> dict:
    item = {"grupo": grupo, "accion": accion, "idAplicacion": v.get("idAplicacion") if v else None,
            "origenMovimiento": v["origenMovimiento"] if v else None, "idMovimientoOrigen": v["idMovimiento"] if v else None,
            "tipoDocumento": v["tipoDocumento"] if v else None, "idDocumento": v["idDocumento"] if v else None,
            "importe": round(importe if importe is not None else (v["importeArs"] if v else 0), 2),
            "motivo": motivo, "candidatos": None, "elegido": False}
    item.update(extra)
    return item


def _elegir_candidatos(candidatos: list[dict], necesario: float) -> list[dict]:
    """Prefiere los de saldo libre casi igual a lo necesario; si no hay,
    los que alcanzan a cubrirlo."""
    exactos = [c for c in candidatos if abs(c["libre"] - necesario) <= _tol(necesario)]
    return exactos or [c for c in candidatos if c["libre"] >= necesario - _tol(necesario)]


def proponer(raw: dict, hallazgos: list[dict]) -> list[dict]:
    vinculos = raw["vinculos"]
    documentos = raw.get("documentos", {})
    movimientos = raw.get("movimientos", {})
    por_aplicacion = {v["idAplicacion"]: v for v in vinculos if v["idAplicacion"] is not None}

    # 1. Qué hacer con cada aplicación señalada (una sola acción por aplicación).
    accion: dict[int, tuple[str, str, str]] = {}
    for h in hallazgos:
        id_ap = h.get("idAplicacion")
        v = por_aplicacion.get(id_ap)
        if v is None or v["origenCarga"] == "manual":
            continue
        if h["categoria"] == "doble-imputacion":
            accion[id_ap] = ("anular", "doble-imputacion/alta", "La factura ya está pagada vía tarjeta o cheque propio")
        elif h["categoria"] == "fecha-incoherente" and accion.get(id_ap, ("",))[0] != "anular":
            # Revisión contable (T025): en ventas un cobro anterior puede ser
            # un anticipo o seña legítimo; nunca va como certeza alta.
            certeza = "alta" if h["diasAntes"] > DIAS_CERTEZA_ALTA and v["tipoDocumento"] not in _VENTAS else "media"
            accion[id_ap] = ("anular", f"fecha-incoherente/{certeza}",
                             f"El pago es {h['diasAntes']} días anterior a la factura")
        elif h["categoria"] == "moneda-mezclada" and id_ap not in accion:
            accion[id_ap] = ("pesificar", "moneda-mezclada/alta", "Importe cargado en us$ contra un movimiento en pesos")

    # Documento excedido (FR-004 / SC-001): se anulan sus aplicaciones
    # automáticas más alejadas en fecha hasta que deje de estar excedido.
    # Caso típico: el FIFO aplicó un consumo de tarjeta de 2025 a una
    # factura de 2020 que ya tenía su propio consumo imputado.
    ajustes = _excedidos(raw, hallazgos, por_aplicacion, accion)

    # Moneda mezclada: si las pesificaciones de un mismo movimiento, sumadas,
    # no entran en él, la regla no es concluyente → certeza media.
    pesificado_mov: dict[tuple, float] = defaultdict(float)
    for id_ap, (acc, _g, _m) in accion.items():
        if acc == "pesificar":
            v = por_aplicacion[id_ap]
            pesificado_mov[(v["origenMovimiento"], v["idMovimiento"])] += v["importeArs"]
    for id_ap, (acc, _g, motivo) in list(accion.items()):
        if acc == "pesificar":
            v = por_aplicacion[id_ap]
            m = movimientos.get((v["origenMovimiento"], v["idMovimiento"]))
            if m is not None and pesificado_mov[(v["origenMovimiento"], v["idMovimiento"])] > abs(float(m["importe"] or 0)) + _tol(float(m["importe"] or 0)):
                accion[id_ap] = ("pesificar", "moneda-mezclada/media", motivo + " (las pesificaciones del movimiento superan su importe)")

    items: list[dict] = []
    anuladas: set[int] = set()
    for id_ap, (acc, grupo, motivo) in accion.items():
        v = por_aplicacion[id_ap]
        items.append(_item(grupo, acc, v, motivo))
        if acc == "anular":
            anuladas.add(id_ap)
        if id_ap in ajustes:
            # Ajuste parcial: se anula y se vuelve a crear por lo que corresponde.
            items.append(_item(grupo, "reemplazo", v, f"Ajuste parcial de la aplicación {id_ap}: queda por lo que cierra la factura",
                               importe=ajustes[id_ap], idAplicacion=None, elegido=True))

    # 2. Saldos libres después de anular.
    pagado_doc: dict[tuple, float] = defaultdict(float)
    aplicado_mov: dict[tuple, float] = defaultdict(float)
    for v in vinculos:
        if v["redundante"] or (v["idAplicacion"] in anuladas and v["idAplicacion"] not in ajustes):
            continue
        if v["idAplicacion"] in ajustes:
            v = dict(v, importeArs=ajustes[v["idAplicacion"]])
        if v["enDocumento"]:
            pagado_doc[(v["tipoDocumento"], v["idDocumento"])] += v["importeArs"]
        if v["enMovimiento"]:
            aplicado_mov[(v["origenMovimiento"], v["idMovimiento"])] += v["importeArs"]

    libre_doc = {k: d["totalArs"] - pagado_doc[k] for k, d in documentos.items() if d.get("totalArs") is not None}
    libre_mov = {k: abs(float(m["importe"] or 0)) - aplicado_mov[k] for k, m in movimientos.items()}
    docs_por_contacto: dict[int, list[tuple]] = defaultdict(list)
    for k, d in documentos.items():
        if d.get("idContacto") is not None and k[0] in _COMPRAS + _VENTAS:
            docs_por_contacto[d["idContacto"]].append(k)
    movs_por_contacto: dict[int, list[tuple]] = defaultdict(list)
    for k, m in movimientos.items():
        if m.get("idContacto"):
            movs_por_contacto[m["idContacto"]].append(k)

    # 3. Reemplazos.
    for id_ap in sorted(anuladas - set(ajustes)):
        v = por_aplicacion[id_ap]
        grupo = accion[id_ap][1]
        necesario = v["importeArs"]
        clave_doc = (v["tipoDocumento"], v["idDocumento"])
        doc = documentos.get(clave_doc)

        # 3a. La factura quedó impaga (solo si la anulada la estaba pagando).
        impaga = libre_doc.get(clave_doc, 0) >= necesario - _tol(necesario)
        if not v["redundante"] and impaga and doc and doc.get("idContacto") and clave_doc[0] in _COMPRAS + _VENTAS:
            signo = -1 if clave_doc[0] in _COMPRAS else 1
            f_doc = dia(doc["fecha"])
            cands = []
            for k in movs_por_contacto.get(doc["idContacto"], []):
                m = movimientos[k]
                if k == (v["origenMovimiento"], v["idMovimiento"]) or (float(m["importe"] or 0) * signo) <= 0:
                    continue
                f_mov = dia(m["fecha"])
                if f_doc and f_mov and not (f_doc - timedelta(days=MARGEN_DIAS) <= f_mov <= f_doc + timedelta(days=DIAS_CERTEZA_ALTA)):
                    continue
                cands.append({"origenMovimiento": k[0], "idMovimientoOrigen": k[1], "tipoDocumento": clave_doc[0],
                              "idDocumento": clave_doc[1], "fecha": f_mov, "libre": round(libre_mov.get(k, 0), 2)})
            cands = sorted(_elegir_candidatos(cands, necesario), key=lambda c: abs((c["fecha"] - f_doc).days) if f_doc and c["fecha"] else 0)
            items.extend(_reemplazo(cands, necesario, grupo, id_ap, "Otro pago para la factura que quedó impaga",
                                    libre_mov, lambda c: (c["origenMovimiento"], c["idMovimientoOrigen"])))

        # 3b. El movimiento quedó libre: buscar la factura que realmente pagó.
        clave_mov = (v["origenMovimiento"], v["idMovimiento"])
        m = movimientos.get(clave_mov)
        if v["origenMovimiento"] in _BANCOS and m and m.get("idContacto"):
            familia = _COMPRAS if float(m["importe"] or 0) < 0 else _VENTAS
            f_mov = dia(m["fecha"])
            cands = []
            for k in docs_por_contacto.get(m["idContacto"], []):
                if k == clave_doc or k[0] not in familia or k not in libre_doc:
                    continue
                f_doc = dia(documentos[k]["fecha"])
                if f_doc and f_mov and f_doc > f_mov + timedelta(days=MARGEN_DIAS):
                    continue
                cands.append({"origenMovimiento": clave_mov[0], "idMovimientoOrigen": clave_mov[1], "tipoDocumento": k[0],
                              "idDocumento": k[1], "fecha": f_doc, "libre": round(libre_doc[k], 2)})
            cands = sorted(_elegir_candidatos(cands, necesario), key=lambda c: abs((f_mov - c["fecha"]).days) if f_mov and c["fecha"] else 0)
            items.extend(_reemplazo(cands, necesario, grupo, id_ap, "Otra factura para el pago que quedó libre",
                                    libre_doc, lambda c: (c["tipoDocumento"], c["idDocumento"])))
    return items


def _excedidos(raw: dict, hallazgos: list[dict], por_aplicacion: dict, accion: dict) -> dict[int, float]:
    """Devuelve los ajustes parciales {idAplicacion: importe que queda}."""
    from src.features.vinculos.control import fecha_movimiento

    documentos = raw.get("documentos", {})
    ajustes: dict[int, float] = {}
    por_doc: dict[tuple, list[dict]] = defaultdict(list)
    for v in raw["vinculos"]:
        if v["enDocumento"] and not v["redundante"]:
            por_doc[(v["tipoDocumento"], v["idDocumento"])].append(v)
    for h in hallazgos:
        if h["categoria"] != "documento-excedido":
            continue
        clave = (h["tipoDocumento"], h["idDocumento"])
        total = h["totalDocumento"]
        vigentes = [v for v in por_doc[clave] if accion.get(v["idAplicacion"], ("",))[0] != "anular"]
        pagado = sum(v["importeArs"] for v in vigentes)
        f_doc = dia((documentos.get(clave) or {}).get("fecha"))

        def distancia(v):
            f = fecha_movimiento(raw, v["origenMovimiento"], v["idMovimiento"])
            return abs((f - f_doc).days) if f and f_doc else 0

        # Revisión contable (T025): primero banco/efectivo (la cadena de
        # tarjeta es el pago real), y dentro de cada grupo lo más alejado.
        candidatas = sorted((v for v in vigentes if v["idAplicacion"] is not None and v["origenCarga"] != "manual"),
                            key=lambda v: (v["origenMovimiento"] == "tarjetas", -distancia(v)))
        for v in candidatas:
            exceso = pagado - total
            if exceso <= _tol(total):
                break
            dias = distancia(v)
            certeza = "alta" if dias > DIAS_CERTEZA_ALTA else "media"
            motivo = f"La factura queda imputada por encima de su total; pago a {dias} días de la factura"
            accion[v["idAplicacion"]] = ("anular", f"documento-excedido/{certeza}", motivo)
            if v["importeArs"] > exceso + 0.01:
                ajustes[v["idAplicacion"]] = round(v["importeArs"] - exceso, 2)
                pagado -= exceso
            else:
                pagado -= v["importeArs"]
    return ajustes


def _reemplazo(cands: list[dict], necesario: float, grupo: str, id_ap: int, motivo: str, libres: dict, clave) -> list[dict]:
    cands = [c for c in cands if libres.get(clave(c), 0) >= necesario - _tol(necesario)]
    if not cands:
        return []
    for c in cands:
        c["fecha"] = c["fecha"].isoformat() if c["fecha"] else None
    if len(cands) == 1:
        c = cands[0]
        importe = min(necesario, libres[clave(c)])
        libres[clave(c)] -= importe  # reserva: nadie más en el lote usa ese saldo
        return [{"grupo": grupo, "accion": "reemplazo", "idAplicacion": None, "origenMovimiento": c["origenMovimiento"],
                 "idMovimientoOrigen": c["idMovimientoOrigen"], "tipoDocumento": c["tipoDocumento"], "idDocumento": c["idDocumento"],
                 "importe": round(importe, 2), "motivo": f"{motivo} (reemplaza la aplicación {id_ap})",
                 "candidatos": None, "elegido": True}]
    return [{"grupo": "reemplazo-ambiguo", "accion": "reemplazo", "idAplicacion": None, "origenMovimiento": None,
             "idMovimientoOrigen": None, "tipoDocumento": None, "idDocumento": None, "importe": round(necesario, 2),
             "motivo": f"{motivo} (reemplaza la aplicación {id_ap}); {len(cands)} candidatos",
             "candidatos": cands[:MAX_CANDIDATOS], "elegido": False}]
