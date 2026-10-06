"""Control de integridad de las cuentas de tarjetas — 034 (FR-010, FR-012).

Función pura sobre el diccionario que arma `repository.cargar_control()`
(solo lectura). Una función por categoría; ninguna escribe ni corrige.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

TOLERANCIA_PENDIENTE = 300.0   # $300 en pesos (feedback_umbral_conciliacion); nunca en dólares
TOLERANCIA_CENTAVOS = 0.01
TOLERANCIA_SALDO = 1.0         # FR-009: saldo de la cuenta vs pendiente del módulo
DIAS_CONTINUIDAD = 92
DIAS_DEVOLUCION = 45
PATRON_MONEDA = re.compile(r"\b(USD|U\$S|US\$|DOLAR(ES)?|DÓLAR(ES)?|EURO(S)?)\b", re.IGNORECASE)

CATEGORIAS = (
    "pago-en-proveedor", "movimiento-sin-resumen", "pago-sin-origen-o-importe", "resumen-con-pendiente",
    "devolucion-sin-cruzar", "saldo-inicial-con-pagos", "tarjeta-sin-contacto",
    "consumo-sin-vinculo-con-deuda-abierta", "consumo-sin-proveedor", "diferencia-contrapartida",
    "continuidad-de-resumenes", "indicios-de-otra-moneda",
)


def _h(categoria: str, motivo: str, **datos) -> dict:
    h = {"categoria": categoria, "idTarjeta": None, "tarjeta": None, "medio": None, "idMovimiento": None,
         "idResumen": None, "idLineaConsumo": None, "fecha": None, "importe": None, "motivo": motivo}
    h.update(datos)
    return h


def hallazgos(raw: dict) -> list[dict]:
    hoy: date = raw.get("hoy") or date.today()
    nombres = {t["idTarjeta"]: t["nombre"] for t in raw["tarjetas"]}
    res: list[dict] = []

    def tarjeta(id_t):
        return {"idTarjeta": id_t, "tarjeta": nombres.get(id_t)}

    for t in raw["tarjetas"]:
        if t.get("idContacto") is None:
            res.append(_h("tarjeta-sin-contacto", "La tarjeta no tiene contacto asociado", **tarjeta(t["idTarjeta"])))

    # (a) y (c): pagos de resumen (un movimiento puede repartirse entre varios resúmenes)
    suma_por_mov: dict[tuple, float] = {}
    for p in raw["pagos"]:
        if p.get("idMovimientoOrigen") is not None:
            k = (p.get("medio"), p["idMovimientoOrigen"])
            suma_por_mov[k] = suma_por_mov.get(k, 0.0) + p["importe"]
    for p in raw["pagos"]:
        base = dict(**tarjeta(p["idTarjeta"]), medio=p.get("medio"), idMovimiento=p.get("idMovimientoOrigen"),
                    idResumen=p["idResumen"], fecha=p["fecha"], importe=p["importe"])
        if p.get("idMovimientoOrigen") is None:
            res.append(_h("pago-sin-origen-o-importe", "Pago de resumen sin movimiento bancario de origen", **base))
        elif p.get("importeMovimiento") is None or                 abs(abs(p["importeMovimiento"]) - suma_por_mov[(p.get("medio"), p["idMovimientoOrigen"])]) > TOLERANCIA_CENTAVOS:
            res.append(_h("pago-sin-origen-o-importe", "Los pagos registrados no suman el importe del movimiento bancario", **base))
        if p.get("contactoMovimiento") is not None and p["contactoMovimiento"] not in raw["contactosTarjeta"]:
            res.append(_h("pago-en-proveedor", "El movimiento del pago está asignado a un contacto que no es la tarjeta "
                          "(se acreditaría dos veces)", **base))
        if p.get("estadoResumen") == "Cerrado":
            res.append(_h("saldo-inicial-con-pagos", "Resumen de saldo inicial (Cerrado) con pagos registrados", **base))

    # (b): movimientos a la cuenta de la tarjeta sin resumen
    for m in raw["movimientosTarjeta"]:
        if m["tieneResumen"] or m.get("esCruzado"):
            continue
        res.append(_h("movimiento-sin-resumen", "Movimiento asignado a la tarjeta sin resumen vinculado",
                      **tarjeta(m["idTarjeta"]), medio=m["medio"], idMovimiento=m["idMovimiento"],
                      fecha=m["fecha"], importe=abs(m["importe"])))

    # (d) y (k): resúmenes
    por_tarjeta: dict[int, list[dict]] = {}
    for r in raw["resumenes"]:
        por_tarjeta.setdefault(r["idTarjeta"], []).append(r)
    for id_t, lista in por_tarjeta.items():
        lista.sort(key=lambda r: r["fechaCierre"] or date.min)
        for i, r in enumerate(lista):
            if r["estado"] == "Cerrado":
                continue
            if r["pendiente"] > TOLERANCIA_PENDIENTE:
                res.append(_h("resumen-con-pendiente", "Resumen con saldo pendiente de pago",
                              **tarjeta(id_t), idResumen=r["idResumen"], fecha=r["fechaCierre"], importe=r["pendiente"]))
                if i == len(lista) - 1 or all(x["fechaCierre"] == r["fechaCierre"] for x in lista[i + 1:]):
                    res.append(_h("continuidad-de-resumenes", "Resumen con pendiente y sin resumen posterior",
                                  **tarjeta(id_t), idResumen=r["idResumen"], fecha=r["fechaCierre"], importe=r["pendiente"]))
    for t in raw["tarjetas"]:
        if not t["activa"]:
            continue
        lista = [r for r in por_tarjeta.get(t["idTarjeta"], []) if r["estado"] != "Cerrado" and r["fechaCierre"]]
        if lista:
            ultimo = max(r["fechaCierre"] for r in lista)
            if (hoy - ultimo).days > DIAS_CONTINUIDAD:
                res.append(_h("continuidad-de-resumenes",
                              f"Tarjeta activa cuyo último resumen cerró hace más de {DIAS_CONTINUIDAD} días",
                              **tarjeta(t["idTarjeta"]), fecha=ultimo))

    # Las líneas negativas (devoluciones) del mismo resumen compensan el resto sin vincular de sus compras
    devoluciones: dict[tuple, float] = {}
    for c in raw["consumos"]:
        if c["importe"] < 0:
            k = (c["idTarjeta"], c["idResumen"])
            devoluciones[k] = devoluciones.get(k, 0.0) + (-c["importe"] - c["vinculado"])
    restos: dict[tuple, float] = {}
    for c in raw["consumos"]:
        if c["importe"] > 0 and not c["tieneProveedor"]:
            k = (c["idTarjeta"], c["idResumen"])
            restos[k] = restos.get(k, 0.0) + max(0.0, c["importe"] - c["vinculado"])

    # (h), (i), (l): consumos
    for c in raw["consumos"]:
        base = dict(**tarjeta(c["idTarjeta"]), idResumen=c["idResumen"], idLineaConsumo=c["idLineaConsumo"],
                    fecha=c["fecha"], importe=c["importe"])
        resto = c["importe"] - c["vinculado"]
        k = (c["idTarjeta"], c["idResumen"])
        compensado = restos.get(k, 0.0) - devoluciones.get(k, 0.0) <= TOLERANCIA_PENDIENTE
        if c["importe"] > 0 and not c["tieneProveedor"] and not c.get("cruzado") and resto > TOLERANCIA_PENDIENTE                 and not compensado:
            res.append(_h("consumo-sin-proveedor", "Parte del consumo sin proveedor ni factura vinculada", **base,
                          ) | {"importe": round(resto, 2)})
        elif c["importe"] > 0 and c["tieneProveedor"] and c["importe"] - c["vinculado"] > TOLERANCIA_PENDIENTE \
                and c.get("proveedorDebe"):
            res.append(_h("consumo-sin-vinculo-con-deuda-abierta",
                          "Consumo con proveedor, sin vínculo a un documento, y el proveedor tiene deuda abierta", **base))
        texto = " ".join(x for x in (c.get("detalle"), c.get("observaciones")) if x)
        if PATRON_MONEDA.search(texto):
            res.append(_h("indicios-de-otra-moneda", "El detalle menciona otra moneda: revisar si el importe está en pesos", **base))

    # (e): créditos bancarios sin contacto que devuelven un débito de tarjeta
    cruzados = raw.get("crucesVigentes", set())
    for cr in raw["creditosSinContacto"]:
        if (cr["medio"], cr["idMovimiento"]) in cruzados:
            continue
        for d in raw["debitosTarjeta"]:
            if abs(d["importe"] - cr["importe"]) <= TOLERANCIA_CENTAVOS and \
                    timedelta(0) <= cr["fecha"] - d["fecha"] <= timedelta(days=DIAS_DEVOLUCION):
                res.append(_h("devolucion-sin-cruzar", "Crédito bancario que devuelve un débito de la tarjeta y no está cruzado",
                              **tarjeta(d["idTarjeta"]), medio=cr["medio"], idMovimiento=cr["idMovimiento"],
                              fecha=cr["fecha"], importe=cr["importe"]))
                break

    # (j): saldo de la cuenta vs pendiente del módulo
    for s in raw.get("saldos", []):
        dif = abs(s["saldo"] + s["pendienteNeto"])
        if dif >= TOLERANCIA_SALDO:
            res.append(_h("diferencia-contrapartida", "El saldo de la cuenta no coincide con el pendiente del módulo de tarjetas",
                          **tarjeta(s["idTarjeta"]), importe=round(dif, 2)))
    return res


def resumen_por_categoria(items: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for h in items:
        out[h["categoria"]] = out.get(h["categoria"], 0) + 1
    return out
