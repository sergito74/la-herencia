"""Regla de lote `anular-doble-descuento` (cola C) — 036 (research D10; reemplaza las tareas T029 a T033 de la 035).

Anula las imputaciones del banco que duplican lo que ya cubrió la tarjeta: baja lógica en `AplicacionesPago` (`Anulada = 1`, con motivo,
usuario y fecha), sin borrar nada. El saldo no cambia (sale de los movimientos de la vista). Se revierte con la corrección registrada de la 035.
"""

from __future__ import annotations

import json

from src.db.connection import execute_write_transaction
from src.features.revision_cuentas import colas

MOTIVO = "Doble descuento: el pago bancario duplica lo que ya cubrió la tarjeta (lote 036)"


def ids_por_cuenta(hallazgos: list[dict]) -> dict[int, dict]:
    """Imputaciones de doble descuento agrupadas por cuenta: ids de `AplicacionesPago`, cantidad de pagos e importe (función pura)."""
    salida: dict[int, dict] = {}
    for h in hallazgos:
        if h.get("causa") != "doble-descuento-tarjeta":
            continue
        d = salida.setdefault(h["idContacto"], {"ids": [], "pagos": 0, "importe": 0.0})
        d["ids"] += [int(i) for i in h.get("idsAplicacion", [])]
        d["pagos"] += 1
        d["importe"] = round(d["importe"] + float(h.get("importe") or 0), 2)
    for d in salida.values():
        d["ids"] = sorted(set(d["ids"]))
    return salida


def combinar_tarjetas_duplicadas(por_cuenta: dict[int, dict], duplicadas: dict[int, dict]) -> dict[int, dict]:
    """Suma al detalle de la regla las imputaciones de tarjeta que sobran y que el FIFO no reemplaza (función pura, sin repetir ids)."""
    salida = {i: {"ids": list(d["ids"]), "pagos": d["pagos"], "importe": d["importe"]} for i, d in por_cuenta.items()}
    for id_contacto, t in duplicadas.items():
        d = salida.setdefault(id_contacto, {"ids": [], "pagos": 0, "importe": 0.0})
        nuevas = [i for i in t["ids"] if i not in d["ids"]]
        if nuevas:
            d["ids"] = sorted(set(d["ids"]) | set(nuevas))
            d["importe"] = round(d["importe"] + t["importe"], 2)
    return salida


def candidatas(contextos: dict[int, dict]) -> tuple[list[dict], dict]:
    """Cuentas de la cola C con las imputaciones que se anularían. Ninguna viene tildada."""
    from src.features.auditoria_cuentas import datos as datos_035
    from src.features.auditoria_cuentas import hallazgos as detectores

    from src.features.revision_cuentas import datos as datos_036

    por_cuenta = ids_por_cuenta(detectores.hallazgos_doble_descuento(datos_035.cargar_hallazgos()["documentos"]))
    por_cuenta = combinar_tarjetas_duplicadas(por_cuenta, datos_036.tarjetas_duplicadas())   # T042
    cuentas = []
    for id_contacto, ctx in contextos.items():
        if colas.asignar_cola(ctx["colas_ctx"])[0] != "C":
            continue
        d = por_cuenta.get(id_contacto, {"ids": [], "pagos": 0, "importe": 0.0})
        cumple = bool(d["ids"])
        extra = {"cumple": cumple, "motivos": [] if cumple else ["No hay imputaciones duplicadas para anular"], "idsPropuestos": d["ids"],
                 "nota": f"{d['pagos']} pagos y {len(d['ids'])} imputaciones por {d['importe']:,.2f} que se anularían (el saldo no cambia)" if cumple else None}
        cuentas.append({"idContacto": id_contacto, "razonSocial": (ctx.get("cuenta") or {}).get("razonSocial"), "saldo": ctx["saldo"], "cumple": cumple,
                        "extra": extra, "movimientos": ctx["movimientos"], "importe": ctx["volumen"]})
    return colas.orden_de_dificultad(cuentas), {}


def aplicar(lote: dict, tildadas: list[dict], usuario: str) -> None:
    """Anula en una sola transacción las imputaciones de las cuentas tildadas y guarda sus ids en cada fila para poder revertir."""
    operaciones: list = []
    for c in tildadas:
        ids = sorted(set(c["extra"].get("idsPropuestos", [])))
        if not ids:
            continue
        marcas = ",".join("?" * len(ids))
        operaciones.append((f"UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() "
                            f"WHERE Anulada = 0 AND IdAplicacion IN ({marcas})", (MOTIVO[:200], usuario[:60], *ids)))
        operaciones.append(("UPDATE dbo.AuditoriaCorreccionesCuentas SET IdsAplicacion = ? WHERE IdCorreccion = ? AND IdContacto = ?",
                            (json.dumps(ids), lote["idCorreccion"], c["idContacto"])))
    if operaciones:
        execute_write_transaction(operaciones)


def revertir(lote: dict, usuario: str) -> None:
    """Devuelve las imputaciones anuladas por el lote (la corrección registrada guarda sus ids)."""
    from src.features.auditoria_cuentas import correcciones

    correcciones.revertir(lote["idCorreccion"], usuario)
