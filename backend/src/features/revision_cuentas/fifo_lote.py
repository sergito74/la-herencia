"""Regla de lote `fifo-tandas` (cola B) — 036 (research D10 y D11; FR-007 y FR-025).

Recalcula las imputaciones por FIFO con el motor de la 032 (simular, aplicar con respaldo, revertir) solo en las cuentas de la cola B que
completaron E1 a E4. Resuelve también los hallazgos de plazo de 24 meses (anula y reimputa). El saldo no cambia.
"""

from __future__ import annotations

from src.features.recalculo_fifo import ejecuciones
from src.features.revision_cuentas import colas, criterios


def candidatas(contextos: dict[int, dict], usuario: str) -> tuple[list[dict], dict]:
    """Cuentas de la cola B. Las que pasan la puerta del FIFO se simulan juntas; el resto figura sin poder tildarse y con el motivo."""
    en_cola, listas = [], []
    for id_contacto, ctx in contextos.items():
        if colas.asignar_cola(ctx["colas_ctx"])[0] != "B":
            continue
        crit = criterios.evaluar(ctx["criterios_ctx"])
        puede, etapa, faltan = criterios.previos_al_fifo(crit)
        en_cola.append((id_contacto, ctx, puede, etapa, faltan))
        if puede:
            listas.append(id_contacto)
    parametros: dict = {}
    detalle_por_cuenta: dict[int, dict] = {}
    if listas:
        simulacion = ejecuciones.simular(listas, usuario)
        parametros["idEjecucion"] = simulacion["idEjecucion"]
        for i in listas:
            detalle_por_cuenta[i] = ejecuciones.detalle(simulacion["idEjecucion"], i)["contacto"]
    cuentas = []
    for id_contacto, ctx, puede, etapa, faltan in en_cola:
        d = detalle_por_cuenta.get(id_contacto)
        motivos: list[str] = []
        if not puede:
            motivos = [f"Falta completar {etapa} antes del FIFO: " + "; ".join(f"{c['codigo']}: {c['medido']}" for c in faltan)]
        elif d is None or d["tendencia"] == "empeora":
            motivos = ["El recálculo dejaría la cuenta peor que ahora"]
        elif not d["cierraDespues"] and d["tendencia"] != "mejora":
            motivos = ["El FIFO no cambia nada en esta cuenta"]
        cumple = not motivos
        extra = {"cumple": cumple, "motivos": motivos, "idEjecucion": parametros.get("idEjecucion"),
                 "tendencia": None if d is None else d["tendencia"], "cierraDespues": None if d is None else d["cierraDespues"],
                 "nota": None if d is None else f"Imputado hoy {d['aplicadoAntes']:,.2f}; con FIFO {d['aplicadoDespues']:,.2f} ({d['tendencia']})"}
        cuentas.append({"idContacto": id_contacto, "razonSocial": (ctx.get("cuenta") or {}).get("razonSocial"), "saldo": ctx["saldo"], "cumple": cumple,
                        "extra": extra, "movimientos": ctx["movimientos"], "importe": ctx["volumen"]})
    return colas.orden_de_dificultad(cuentas), parametros


def aplicar(lote: dict, tildadas: list[dict], usuario: str) -> None:
    id_ejecucion = lote["parametros"].get("idEjecucion")
    if not id_ejecucion:
        return
    ejecuciones.aplicar(int(id_ejecucion), [c["idContacto"] for c in tildadas], False, usuario)


def revertir(lote: dict, usuario: str) -> None:
    id_ejecucion = lote["parametros"].get("idEjecucion")
    if id_ejecucion:
        ejecuciones.revertir(int(id_ejecucion), usuario)


def descartar(lote: dict) -> None:
    id_ejecucion = lote["parametros"].get("idEjecucion")
    if id_ejecucion:
        ejecuciones.descartar(int(id_ejecucion))
