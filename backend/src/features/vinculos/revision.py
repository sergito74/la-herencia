"""Revisión de un lote por proveedor (031, pedido de Sergio 2026-09-30:
"con esta información es imposible validar"). La unidad de decisión es el
proveedor: se ve su cuenta como está hoy y como quedaría, factura por
factura, con cada pago descripto (banco/tarjeta, fecha, concepto, importe)
y el porqué de cada cambio. Aprobar un proveedor incluye sus ítems en el
lote; recién se aplica lo aprobado."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date

from src.db.connection import execute_write_transaction, fetch_all
from src.features.vinculos import fuente
from src.features.vinculos.cadenas import dia
from src.features.vinculos.lotes import _exigir_estado

_VIAS = {"aplicacion": "Aplicación", "tarjeta": "Tarjeta", "valor-propio": "Cheque propio", "tesoreria": "Tesorería",
         "backfill-impuesto": "Impuesto"}


def _iso(valor) -> str | None:
    d = dia(valor)
    return d.isoformat() if d else None


def describir_pago(raw: dict, origen: str, id_mov) -> dict:
    """Lo que Sergio reconoce de un pago: medio, fecha, concepto, importe."""
    m = raw.get("movimientos", {}).get((origen, id_mov))
    if m is not None:
        return {"medio": "Galicia" if origen == "galicia" else "Nación", "fecha": _iso(m["fecha"]),
                "concepto": (m.get("concepto") or "").strip(), "importe": round(abs(float(m["importe"] or 0)), 2)}
    if origen == "tarjetas":
        linea = raw.get("lineas", {}).get(id_mov) or {}
        tarjeta = linea.get("tarjeta") or "Tarjeta"
        resumen = f" · resumen {linea['resumen']}" if linea.get("resumen") else ""
        return {"medio": tarjeta, "fecha": _iso(linea.get("fecha")),
                "concepto": f"{(linea.get('detalle') or '').strip()}{resumen}",
                "importe": round(abs(float(linea.get("importe") or 0)), 2)}
    if origen == "valores-propios":
        valor = next((v for v in raw.get("valores", []) if v["idValor"] == id_mov), None)
        return {"medio": "Cheque propio", "fecha": _iso(valor and valor.get("fechaEmision")),
                "concepto": f"Cheque n° {valor['numero']}" if valor else f"Cheque {id_mov}",
                "importe": round(abs(float(valor["importe"])), 2) if valor else None}
    nombre = {"efectivo": "Efectivo", "valores-recibidos": "Valor recibido", "mercado-libre": "Mercado Libre"}.get(origen, origen)
    importe = raw.get("importesOtros", {}).get((origen, id_mov))
    return {"medio": nombre, "fecha": _iso(raw.get("fechasOtros", {}).get((origen, id_mov))), "concepto": "",
            "importe": round(abs(importe), 2) if importe is not None else None}


SIN_CONTACTO = 0  # ítems sin proveedor identificable se revisan juntos bajo el id 0


def _items(id_lote: int, id_contacto: int | None = None) -> list[dict]:
    if id_contacto is None:
        filtro, params = "", (id_lote,)
    elif id_contacto == SIN_CONTACTO:
        filtro, params = "AND IdContacto IS NULL", (id_lote,)
    else:
        filtro, params = "AND IdContacto = ?", (id_lote, id_contacto)
    filas = fetch_all(
        "SELECT IdItem AS idItem, Grupo AS grupo, Accion AS accion, IdAplicacion AS idAplicacion, "
        "OrigenMovimiento AS origenMovimiento, IdMovimientoOrigen AS idMovimientoOrigen, TipoDocumento AS tipoDocumento, "
        "IdDocumento AS idDocumento, Importe AS importe, Motivo AS motivo, Candidatos AS candidatos, Incluido AS incluido, "
        f"Elegido AS elegido, IdContacto AS idContacto FROM dbo.CorreccionVinculosItem WHERE IdLote = ? {filtro}", params)
    for f in filas:
        f["candidatos"] = json.loads(f["candidatos"]) if f["candidatos"] else None
        f["importe"] = float(f["importe"] or 0)
        f["idContacto"] = f["idContacto"] if f["idContacto"] is not None else SIN_CONTACTO
    return filas


def _nombres(ids: set) -> dict[int, str]:
    ids = [i for i in ids if i is not None]
    nombres: dict[int, str] = {}
    for k in range(0, len(ids), 500):
        lote = ids[k:k + 500]
        for f in fetch_all(f"SELECT IdContacto AS id, [Razon Social] AS nombre FROM dbo.Contactos "
                           f"WHERE IdContacto IN ({','.join('?' * len(lote))})", tuple(lote)):
            nombres[f["id"]] = f["nombre"]
    return nombres


def _decisiones(id_lote: int) -> dict[int, str]:
    return {f["id"]: f["estado"] for f in fetch_all(
        "SELECT IdContacto AS id, Estado AS estado FROM dbo.CorreccionVinculosRevision WHERE IdLote = ?", (id_lote,))}


def proveedores(id_lote: int) -> list[dict]:
    """Un renglón por proveedor, ordenado por dinero en juego."""
    resumen: dict = defaultdict(lambda: {"cambios": 0, "importe": 0.0, "facturas": set(), "porDecidir": 0})
    for i in _items(id_lote):
        r = resumen[i["idContacto"]]
        r["cambios"] += 1
        r["importe"] += i["importe"] if i["accion"] != "reemplazo" or i["elegido"] else 0
        if i["tipoDocumento"]:
            r["facturas"].add((i["tipoDocumento"], i["idDocumento"]))
        if i["accion"] == "reemplazo" and not i["elegido"]:
            r["porDecidir"] += 1
    nombres, decisiones = _nombres(set(resumen)), _decisiones(id_lote)
    filas = [{"idContacto": c, "nombre": nombres.get(c, "Sin proveedor identificado" if c == SIN_CONTACTO else f"Contacto {c}"),
              "cambios": r["cambios"], "importe": round(r["importe"], 2), "facturas": len(r["facturas"]),
              "reemplazosPorElegir": r["porDecidir"], "estado": decisiones.get(c, "pendiente")}
             for c, r in resumen.items()]
    return sorted(filas, key=lambda f: -f["importe"])


def armar_detalle(raw: dict, items: list[dict]) -> dict:
    """Pura: cuenta del proveedor antes y después del lote."""
    documentos = raw.get("documentos", {})
    anula = {i["idAplicacion"]: i for i in items if i["accion"] in ("anular", "pesificar") and i["idAplicacion"]}
    nuevas = [i for i in items if i["accion"] == "reemplazo" and i["elegido"] and i["tipoDocumento"]]
    cargado = {a["idAplicacion"]: float(a["importe"]) for a in raw.get("aplicaciones", [])}
    claves = {(i["tipoDocumento"], i["idDocumento"]) for i in items if i["tipoDocumento"]}
    por_doc: dict[tuple, list[dict]] = defaultdict(list)
    for v in raw["vinculos"]:
        if v["enDocumento"]:
            por_doc[(v["tipoDocumento"], v["idDocumento"])].append(v)
            if v["idAplicacion"] in anula:
                claves.add((v["tipoDocumento"], v["idDocumento"]))

    facturas = []
    for clave in sorted(claves, key=lambda k: (dia((documentos.get(k) or {}).get("fecha")) or date.min, k)):
        d = documentos.get(clave) or {}
        pagos, antes, despues = [], 0.0, 0.0
        for v in por_doc.get(clave, []):
            item = anula.get(v["idAplicacion"])
            cargado_hoy = cargado.get(v["idAplicacion"], v["importeArs"])
            antes += cargado_hoy
            fila = {"via": _VIAS.get(v["via"], v["via"]), **describir_pago(raw, v["origenMovimiento"], v["idMovimiento"]),
                    "imputado": round(cargado_hoy, 2), "imputadoDespues": None, "cambio": "se mantiene", "motivo": None}
            if item is None:
                despues += cargado_hoy
            elif item["accion"] == "pesificar":
                despues += item["importe"]
                fila.update(cambio="se pesifica", imputadoDespues=round(item["importe"], 2), motivo=item["motivo"])
            else:
                fila.update(cambio="se quita", imputadoDespues=0.0, motivo=item["motivo"])
            pagos.append(fila)
        for n in nuevas:
            if (n["tipoDocumento"], n["idDocumento"]) == clave:
                despues += n["importe"]
                pagos.append({"via": "Aplicación", **describir_pago(raw, n["origenMovimiento"], n["idMovimientoOrigen"]),
                              "imputado": 0.0, "imputadoDespues": round(n["importe"], 2), "cambio": "se agrega",
                              "motivo": n["motivo"]})
        total = d.get("totalArs")
        facturas.append({
            "tipoDocumento": clave[0], "idDocumento": clave[1], "numero": d.get("numero") or f"{clave[0]} {clave[1]}",
            "fecha": _iso(d.get("fecha")), "moneda": d.get("moneda"), "total": total,
            "totalOriginal": d.get("totalOriginal"), "tc": d.get("tc"),
            "pagadoAntes": round(antes, 2), "pagadoDespues": round(despues, 2),
            "saldoAntes": round(total - antes, 2) if total is not None else None,
            "saldoDespues": round(total - despues, 2) if total is not None else None,
            "pagos": pagos,
        })

    usados = {(n["origenMovimiento"], n["idMovimientoOrigen"]) for n in nuevas}
    libres = []
    for id_ap, item in anula.items():
        if item["accion"] != "anular" or (item["origenMovimiento"], item["idMovimientoOrigen"]) in usados:
            continue
        libres.append({**describir_pago(raw, item["origenMovimiento"], item["idMovimientoOrigen"]),
                       "liberado": round(item["importe"], 2), "motivo": item["motivo"]})

    ambiguos = []
    for i in items:
        if i["accion"] == "reemplazo" and i["candidatos"]:
            ambiguos.append({"idItem": i["idItem"], "motivo": i["motivo"], "importe": i["importe"], "elegido": bool(i["elegido"]),
                             "candidatos": [{**c, "pago": describir_pago(raw, c["origenMovimiento"], c["idMovimientoOrigen"]),
                                             "numero": (documentos.get((c["tipoDocumento"], c["idDocumento"])) or {}).get("numero"),
                                             "elegidoActual": bool(i["elegido"]) and i["tipoDocumento"] == c["tipoDocumento"]
                                             and i["idDocumento"] == c["idDocumento"]
                                             and i["idMovimientoOrigen"] == c["idMovimientoOrigen"]}
                                            for c in i["candidatos"]]})
    return {"facturas": facturas, "pagosLibres": libres, "reemplazosPorElegir": ambiguos}


def detalle(id_lote: int, id_contacto: int) -> dict:
    items = _items(id_lote, id_contacto)
    detalle = armar_detalle(fuente.cargar(), items)
    nombre = _nombres({id_contacto}).get(id_contacto, "Sin proveedor identificado" if id_contacto == SIN_CONTACTO else f"Contacto {id_contacto}")
    return {"idContacto": id_contacto, "nombre": nombre, "estado": _decisiones(id_lote).get(id_contacto, "pendiente"),
            **detalle}


def decidir(id_lote: int, id_contacto: int, aprobar: bool, usuario: str) -> dict:
    """Aprobar incluye en el lote todos los ítems del proveedor (los
    reemplazos con varios candidatos, solo si ya se eligió uno). Rechazar
    los deja afuera: esa cuenta queda como está."""
    _exigir_estado(id_lote, "propuesto")
    estado = "aprobado" if aprobar else "rechazado"
    filtro = "IdContacto IS NULL" if id_contacto == SIN_CONTACTO else "IdContacto = ?"
    params_contacto = () if id_contacto == SIN_CONTACTO else (id_contacto,)
    execute_write_transaction([
        ("UPDATE dbo.CorreccionVinculosItem SET Incluido = CASE WHEN ? = 1 AND (Accion <> 'reemplazo' OR Elegido = 1) "
         f"THEN 1 ELSE 0 END WHERE IdLote = ? AND {filtro}", (1 if aprobar else 0, id_lote, *params_contacto)),
        ("DELETE FROM dbo.CorreccionVinculosRevision WHERE IdLote = ? AND IdContacto = ?", (id_lote, id_contacto)),
        ("INSERT INTO dbo.CorreccionVinculosRevision (IdLote, IdContacto, Estado, Usuario) VALUES (?, ?, ?, ?)",
         (id_lote, id_contacto, estado, usuario[:100])),
    ])
    return {"idContacto": id_contacto, "estado": estado}
