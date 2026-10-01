"""Control de integridad (031, FR-011): lista las inconsistencias de los
vínculos. Función pura sobre lo que carga `fuente.cargar()`."""

from __future__ import annotations

from collections import defaultdict

from src.features.vinculos.cadenas import MARGEN_DIAS, dia, excede, imputado_por_via

CATEGORIAS = ("documento-excedido", "movimiento-excedido", "doble-imputacion", "fecha-incoherente", "moneda-mezclada")


def fecha_movimiento(raw: dict, origen: str, id_mov: int):
    m = raw.get("movimientos", {}).get((origen, id_mov))
    if m is not None:
        return dia(m["fecha"])
    return dia(raw.get("fechasOtros", {}).get((origen, id_mov)))


def dias_antes(raw: dict, v: dict) -> int | None:
    """Cuántos días antes del documento se hizo el pago (positivo = antes)."""
    doc = raw.get("documentos", {}).get((v["tipoDocumento"], v["idDocumento"]))
    f_mov = fecha_movimiento(raw, v["origenMovimiento"], v["idMovimiento"])
    if not doc or doc.get("fecha") is None or f_mov is None:
        return None
    return (dia(doc["fecha"]) - f_mov).days


def _hallazgo(categoria: str, v: dict | None = None, **extra) -> dict:
    h = {"categoria": categoria, "tipoDocumento": None, "idDocumento": None, "origenMovimiento": None,
         "idMovimiento": None, "totalDocumento": None, "imputadoPorVia": {}, "exceso": None, "diasAntes": None,
         "idAplicacion": None, "importe": None}
    if v is not None:
        h.update(tipoDocumento=v["tipoDocumento"], idDocumento=v["idDocumento"], origenMovimiento=v["origenMovimiento"],
                 idMovimiento=v["idMovimiento"], idAplicacion=v["idAplicacion"], importe=v["importeArs"])
    h.update(extra)
    return h


def hallazgos(raw: dict) -> list[dict]:
    vinculos = raw["vinculos"]
    documentos = raw.get("documentos", {})
    resultado: list[dict] = []

    por_via = imputado_por_via(vinculos)
    for clave, vias in por_via.items():
        doc = documentos.get(clave)
        total = doc.get("totalArs") if doc else None
        if total is None:
            continue
        pagado = sum(imp for via, imp in vias.items() if "(redundante)" not in via)
        if excede(pagado, total):
            resultado.append(_hallazgo("documento-excedido", tipoDocumento=clave[0], idDocumento=clave[1],
                                       totalDocumento=total, imputadoPorVia={k: round(x, 2) for k, x in vias.items()},
                                       exceso=round(pagado - total, 2)))

    por_mov: dict[tuple, float] = defaultdict(float)
    for v in vinculos:
        if v["enMovimiento"] and not v["redundante"]:
            por_mov[(v["origenMovimiento"], v["idMovimiento"])] += v["importeArs"]
    for clave, aplicado in por_mov.items():
        m = raw.get("movimientos", {}).get(clave)
        if m is not None and excede(aplicado, abs(float(m["importe"] or 0))):
            resultado.append(_hallazgo("movimiento-excedido", origenMovimiento=clave[0], idMovimiento=clave[1],
                                       totalDocumento=abs(float(m["importe"])), exceso=round(aplicado - abs(float(m["importe"])), 2)))

    for v in vinculos:
        if not v["enDocumento"]:
            continue
        if v["redundante"]:
            resultado.append(_hallazgo("doble-imputacion", v))
        if v["idAplicacion"] is not None and v["origenCarga"] != "manual":
            antes = dias_antes(raw, v)
            if antes is not None and antes > MARGEN_DIAS:
                resultado.append(_hallazgo("fecha-incoherente", v, diasAntes=antes))
        if v["monedaMezclada"]:
            resultado.append(_hallazgo("moneda-mezclada", v))
    return resultado


def totales(lista: list[dict]) -> dict[str, int]:
    conteo = {c: 0 for c in CATEGORIAS}
    for h in lista:
        conteo[h["categoria"]] += 1
    return conteo
