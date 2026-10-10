"""Hallazgos sobre las aplicaciones de pagos a facturas — 035 (research D1, D2, D3; FR-004 a FR-007, FR-018).

Funciones puras sobre las filas que carga `datos.cargar_aplicaciones()`. Las aplicaciones no cambian el
saldo de ninguna cuenta: un hallazgo avisa que una imputación es sospechosa, no que el saldo esté mal.
"""

from __future__ import annotations

import calendar
import re
from collections import defaultdict
from datetime import date

# Organismos oficiales: se auditan como cuentas; un saldo a nuestro favor es un pago sin boleta cargada.
ORGANISMOS = {119: "AFIP", 12: "ARBA", 72: "Municipalidad de Bolívar", 422: "Municipalidad de Tapalqué", 250: "SENASA",
              315: "UATRE", 447: "Ministerio de Desarrollo Agrario", 351: "Ministerio de Trabajo BA",
              563: "Consejo de Ciencias Económicas", 247: "Colegio de Escribanos"}
AUTOMATICAS = {"automatica-exacta", "automatica-mejor-esfuerzo"}
MEDIOS_CON_FECHA = {"bna", "galicia", "efectivo"}
TOLERANCIA_RELATIVA = 0.005  # 0,5 %, igual que el FIFO
TOLERANCIA_MINIMA = 1.0


def sumar_meses(d: date, meses: int) -> date:
    m = d.month - 1 + meses
    anio, mes = d.year + m // 12, m % 12 + 1
    return date(anio, mes, min(d.day, calendar.monthrange(anio, mes)[1]))


def _total_ars(a: dict) -> float:
    total = float(a["total"])
    if a.get("moneda") == "Dolares" and a.get("tc"):
        total *= float(a["tc"])
    return total


def hallazgos_plazo(apps: list[dict], plazo_meses: int, anticipo_dias: int) -> list[dict]:
    """Un hallazgo por movimiento de pago y contacto con las facturas que superan el plazo.

    `apps`: idAplicacion, medio, idMovimiento, fechaPago, idContacto, idCompra, fechaFactura, importe, origenAplicacion.
    Un pago anterior a la factura por más de `anticipo_dias` es un anticipo largo y también se marca.
    """
    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for a in apps:
        if a["medio"] not in MEDIOS_CON_FECHA or a.get("fechaPago") is None or a.get("fechaFactura") is None:
            continue
        pago, factura = a["fechaPago"], a["fechaFactura"]
        tarde = pago > sumar_meses(factura, plazo_meses)
        anticipo_largo = (factura - pago).days > anticipo_dias
        if tarde or anticipo_largo:
            grupos[(a["medio"], a["idMovimiento"], a["idContacto"])].append({**a, "_tarde": tarde})
    resultado = []
    for (medio, id_mov, id_contacto), lista in grupos.items():
        origenes = {x["origenAplicacion"] for x in lista}
        automatica = bool(origenes & AUTOMATICAS)
        dias = max(((x["fechaPago"] - x["fechaFactura"]).days for x in lista), default=0)
        mas_vieja = min(x["fechaFactura"] for x in lista)
        resultado.append({
            "causa": "aplicacion-fuera-de-plazo" if automatica else "fuera-de-plazo-decidido",
            "idContacto": id_contacto, "medio": medio, "idMovimiento": id_mov, "fechaPago": lista[0]["fechaPago"],
            "importe": round(sum(float(x["importe"]) for x in lista), 2), "cantidadFacturas": len({x["idCompra"] for x in lista}),
            "facturaMasVieja": mas_vieja, "diasMaximos": dias, "origenAplicacion": sorted(origenes)[0],
            "idsAplicacion": sorted(x["idAplicacion"] for x in lista),
            "motivo": (f"El pago se aplicó a facturas de hace más de {plazo_meses} meses" if any(x["_tarde"] for x in lista)
                       else f"Pago anterior a la factura por más de {anticipo_dias} días (anticipo largo)"),
        })
    return resultado


def hallazgos_doble_descuento(docs: list[dict]) -> list[dict]:
    """Facturas que la tarjeta ya cubre por completo y que además tienen un pago bancario aplicado en forma automática.

    `docs`: idCompra, idContacto, nro, total (ARS), tarjeta (importe vinculado desde tarjeta),
    bancarias: lista de {medio, idMovimiento, importe, fechaPago, origenAplicacion}.
    """
    grupos: dict[tuple, dict] = {}
    for d in docs:
        total = float(d["total"])
        if total <= 0 or float(d["tarjeta"] or 0) < total - max(TOLERANCIA_MINIMA, total * TOLERANCIA_RELATIVA):
            continue
        for b in d["bancarias"]:
            if b["origenAplicacion"] not in AUTOMATICAS:
                continue
            g = grupos.setdefault((b["medio"], b["idMovimiento"], d["idContacto"]), {
                "causa": "doble-descuento-tarjeta", "idContacto": d["idContacto"], "medio": b["medio"],
                "idMovimiento": b["idMovimiento"], "fechaPago": b.get("fechaPago"), "importe": 0.0, "cantidadFacturas": 0, "idsAplicacion": [],
                "origenAplicacion": b["origenAplicacion"],
                "motivo": "El pago bancario se aplicó a facturas que la tarjeta ya había cubierto por completo"})
            g["importe"] = round(g["importe"] + float(b["importe"]), 2)
            g["cantidadFacturas"] += 1
            if b.get("idAplicacion") is not None:
                g["idsAplicacion"].append(b["idAplicacion"])
    return list(grupos.values())


def hallazgos_sobrepago(docs: list[dict]) -> list[dict]:
    """Facturas con más aplicado que su importe (sin ser un doble descuento con tarjeta)."""
    resultado = []
    for d in docs:
        total = float(d["total"])
        if total <= 0 or float(d["tarjeta"] or 0) >= total - max(TOLERANCIA_MINIMA, total * TOLERANCIA_RELATIVA):
            continue
        aplicado = float(d["aplicado"])
        if aplicado > total + max(TOLERANCIA_MINIMA, total * TOLERANCIA_RELATIVA):
            resultado.append({"causa": "sobrepago", "idContacto": d["idContacto"], "importe": round(aplicado - total, 2),
                              "motivo": f"Se aplicó más que el importe de la factura {d['nro']}"})
    return resultado


def hallazgos_nota_sin_imputar(notas: list[dict], umbral: float) -> list[dict]:
    """Notas de débito sin ninguna aplicación ni vínculo de tarjeta."""
    return [{"causa": "nota-sin-imputar", "idContacto": n["idContacto"], "importe": round(float(n["total"]), 2),
             "motivo": f"La nota de débito {n['nro']} no está imputada"}
            for n in notas if float(n["total"]) > umbral and not n.get("aplicado") and not n.get("tarjeta")]


def hallazgos_impuesto_sin_boleta(saldos: dict[int, float], umbral: float) -> list[dict]:
    """Organismos con más pagado que boletas cargadas (saldo a nuestro favor). Solo se clasifica: no se rellenan boletas."""
    return [{"causa": "impuesto-sin-boleta", "idContacto": c, "importe": round(v, 2),
             "motivo": f"Se pagó a {ORGANISMOS[c]} más de lo que hay en boletas cargadas"}
            for c, v in saldos.items() if c in ORGANISMOS and v > umbral]


def normalizar_concepto(concepto: str | None) -> str:
    """Concepto sin números ni espacios de más, para agrupar movimientos parecidos."""
    texto = re.sub(r"[0-9]+", "", (concepto or "").upper())
    return re.sub(r"[\s\-/.,:;]+", " ", texto).strip()[:60] or "(SIN CONCEPTO)"


def _palabras(texto: str | None) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", (texto or "").upper()).strip()


def explicado_por(concepto: str | None, reglas: list[str]) -> str | None:
    """Clave de la primera regla `concepto-movimiento` activa que contiene el concepto, o None.

    Una clave sin números (por ejemplo `INTERESES`) también se busca en el concepto sin sus números, así una
    regla creada desde un grupo ("TRANSF JUAN") alcanza a "TRANSF 1234 JUAN"."""
    texto = _palabras(concepto)
    sin_numeros = re.sub(r"[0-9]+", " ", texto)
    sin_numeros = re.sub(r"\s+", " ", sin_numeros).strip()
    for regla in reglas:
        clave = _palabras(regla)
        if not clave:
            continue
        if f" {clave} " in f" {texto} " or clave in texto:
            return regla
        if not re.search(r"[0-9]", clave) and clave in sin_numeros:
            return regla
    return None


def hallazgos_movimiento_sin_contacto(movs: list[dict], reglas: list[str]) -> dict:
    """Movimientos del banco sin contacto, sin conciliación ni cruce, de CUALQUIER importe.

    Los que una regla conocida explica se cuentan aparte; el resto se agrupa por concepto para que Sergio
    decida una regla por grupo (nunca movimiento por movimiento)."""
    explicados: dict[str, dict] = {}
    grupos: dict[str, dict] = {}
    for m in movs:
        clave = explicado_por(m.get("concepto"), reglas)
        importe = float(m["importe"])
        if clave:
            g = explicados.setdefault(clave, {"clave": clave, "movimientos": 0, "importe": 0.0})
            g["movimientos"] += 1
            g["importe"] += abs(importe)
            continue
        concepto = normalizar_concepto(m.get("concepto"))
        g = grupos.setdefault(concepto, {"concepto": concepto, "movimientos": 0, "importe": 0.0, "neto": 0.0, "ejemplos": []})
        g["movimientos"] += 1
        g["importe"] += abs(importe)
        g["neto"] += importe
        if len(g["ejemplos"]) < 5:
            g["ejemplos"].append({"medio": m["medio"], "idMovimiento": m["idMovimiento"], "fecha": m.get("fecha"), "importe": importe,
                                  "concepto": m.get("concepto")})
    for g in list(grupos.values()) + list(explicados.values()):
        g["importe"] = round(g["importe"], 2)
    for g in grupos.values():
        g["neto"] = round(g["neto"], 2)
    return {"sinExplicar": sorted(grupos.values(), key=lambda g: -g["importe"]),
            "explicados": sorted(explicados.values(), key=lambda g: -g["importe"]),
            "movimientosSinExplicar": sum(g["movimientos"] for g in grupos.values()),
            "importeSinExplicar": round(sum(g["importe"] for g in grupos.values()), 2)}


def hallazgos_contacto_duplicado(contactos: list[dict], cuits_compartidos: frozenset[str] | set[str] | tuple = ()) -> list[dict]:
    """Contactos con el mismo CUIT; solo se informa, nunca se unifican. Los CUIT declarados como compartidos (estaciones de una misma
    operadora, por ejemplo) no se informan."""
    por_cuit: dict[str, list[dict]] = defaultdict(list)
    for c in contactos:
        cuit = "".join(ch for ch in (c.get("cuit") or "") if ch.isdigit())
        if len(cuit) == 11 and cuit not in cuits_compartidos:
            por_cuit[cuit].append(c)
    resultado = []
    for cuit, lista in por_cuit.items():
        if len(lista) > 1:
            nombres = ", ".join(f"{c['razonSocial']} ({c['idContacto']})" for c in lista)
            for c in lista:
                resultado.append({"causa": "contacto-duplicado", "idContacto": c["idContacto"], "importe": None,
                                  "motivo": f"Mismo CUIT en más de un contacto: {nombres}"})
    return resultado


def todos(datos: dict, parametros: dict) -> list[dict]:
    umbral = float(parametros["umbralPesos"])
    res = []
    res += hallazgos_plazo(datos["aplicaciones"], int(parametros["plazoMaximoMeses"]), int(parametros["anticipoDias"]))
    res += hallazgos_doble_descuento(datos["documentos"])
    res += hallazgos_sobrepago(datos["documentos"])
    res += hallazgos_nota_sin_imputar(datos["notas"], umbral)
    res += hallazgos_contacto_duplicado(datos["contactos"], set(datos.get("cuitsCompartidos", ())))
    res += hallazgos_impuesto_sin_boleta(datos.get("saldosOrganismos", {}), umbral)
    return res
