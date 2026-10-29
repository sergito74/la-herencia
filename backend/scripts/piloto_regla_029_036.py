"""036 — piloto de la regla aprobada el 29/10/2026 (sección 12 de la auditoría de aplicaciones), solo lectura.

Compara, por contacto, el FIFO-032 puro contra la regla_029 (importe idéntico, combinación única, FIFO con cortes):
cuántas aplicaciones ignoran un pago con documento de importe idéntico (±60 días), cuántas son anticipos de más de
90 días, y lo pendiente. Uso (desde backend/): python -m scripts.piloto_regla_029_036 115 48 [--detalle salida.json]
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date

from src.features.recalculo_fifo import cambio, entrada, motor


def metricas(items: list[dict], res: dict) -> dict:
    por_clave = {i["clave"]: i for i in items}
    por_credito = defaultdict(list)
    for a in res["aplicaciones"]:
        por_credito[tuple(a["credito"])].append(a)
    ignorados = 0
    for cr, apps in por_credito.items():
        c = por_clave.get(cr)
        if not c or c["clase"] != "dinero":
            continue
        gemelos = [i for i in items if i["lado"] != c["lado"] and i["clase"] == "doc" and abs(float(i["importe"]) - float(c["importe"])) <= 0.01
                   and abs((i["fecha"] - c["fecha"]).days) <= 60]
        if len(gemelos) == 1 and all(tuple(a["debito"]) != gemelos[0]["clave"] for a in apps):
            ignorados += 1
    anticipos = sum(1 for a in res["aplicaciones"] if a["fechaVencimiento"] and a["fechaCredito"]
                    and (a["fechaVencimiento"] - a["fechaCredito"]).days > 90)
    return {"aplicaciones": len(res["aplicaciones"]), "matchIgnorado": ignorados, "anticipos90": anticipos,
            "pendienteDebitos": res["pendienteDebitos"], "pendienteCreditos": res["pendienteCreditos"],
            "anticipoAbierto": res["anticipoAbierto"], "reglas": dict(Counter(a["regla"] for a in res["aplicaciones"])),
            "marcas": res["marcas"]}


if __name__ == "__main__":
    ids = [int(x) for x in sys.argv[1:] if x.isdigit()]
    hoy = date.today()
    tc = cambio.funcion_tc(hoy)
    detalle = {}
    for id_contacto, e in entrada.armar(ids).items():
        viejo = motor.recalcular(e["items"], e["fijos"], tc, hoy)
        nuevo = motor.recalcular(e["items"], e["fijos"], tc, hoy, regla_029=True)
        print(f"== {id_contacto} {e['nombre']}")
        for nombre, r in (("FIFO-032", viejo), ("regla_029", nuevo)):
            print(f"   {nombre:10}", metricas(e["items"], r))
        detalle[id_contacto] = {"items": e["items"], "nuevo": nuevo["aplicaciones"]}
    if "--detalle" in sys.argv:
        json.dump(detalle, open(sys.argv[sys.argv.index("--detalle") + 1], "w", encoding="utf-8"), default=str, indent=1)
