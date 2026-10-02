"""Cierre sistemático de las líneas de tarjeta pendientes de conciliar (2026-10-01).

Sergio: las conciliaciones de tarjetas estaban ~85% completas; falta terminarlas
"de manera prolija y metódica". El contacto de cada línea es dato del resumen y
NO se cambia. Solo se vinculan líneas con facturas del MISMO contacto, en tres
niveles, cada uno sobre lo que dejó el anterior:

1. **Exacta**: una factura (o 2-3 facturas de fechas cercanas, incluidas NC) que
   cierra con el saldo de la línea dentro de la tolerancia del módulo, y es la
   única combinación posible. Ninguna factura se usa en dos propuestas.
2. **Cuotas**: líneas "n/m" del mismo comercio e importe cuya suma cierra con
   1-3 facturas de la fecha de compra (ej. Neumáticos Corral, 12 cuotas).
3. **FIFO** (principio de 032): por contacto, cada línea en orden de fecha cubre
   las facturas pendientes más antiguas (USD pesificado al TC de la factura), emitidas entre 60 días antes y 15 días
   después del consumo. Si no alcanzan, la línea queda parcial (no se inventa
   nada).

Las líneas sin contacto, negativas (reintegros) o sin facturas candidatas no se
tocan: se listan como excepciones. Escribe con `vincular_compras_lote` (mismas
validaciones y transacción que la pantalla). Respaldo verificado antes de grabar.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.conciliar_tarjetas_pendientes [--aplicar]
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from itertools import combinations

from src.features.tarjetas_resumenes import repository as R
from src.features.tarjetas_resumenes.conciliacion_documentos import tolerancia

CUOTA = re.compile(r"\b(\d{1,2})/(\d{1,2})\s*$")


def _dias(doc, linea) -> int:
    return (doc["fecha"] - linea["fechaCompra"]).days


def _pendientes() -> list[dict]:
    lineas = [x for x in R.get_pendientes() if x["idContacto"] and x["importe"] > 0]
    for x in lineas:
        x["restante"] = round(x["importe"] - R._total_imputado(x["idLineaConsumo"]), 2)
    return lineas


def _docs(lineas) -> dict[int, list[dict]]:
    return R.get_documentos_de_contactos(sorted({x["idContacto"] for x in lineas}))


def nivel_exacta(lineas, docs) -> list[tuple[dict, list[dict]]]:
    props = []
    for x in lineas:
        ds = [d for d in docs.get(x["idContacto"], [])
              if abs(d["saldoPendiente"]) >= .005 and -45 <= _dias(d, x) <= 60]

        def cierra(cb):
            return abs(sum(d["saldoPendiente"] for d in cb) - x["restante"]) <= tolerancia(list(cb))

        unos = [[d] for d in ds if d["saldoPendiente"] > 0 and cierra([d])]
        if len(unos) == 1:
            props.append((x, unos[0]))
            continue
        if unos:
            continue
        cerca = [d for d in ds if abs(_dias(d, x)) <= 15][:14]
        combos = [list(cb) for r in (2, 3) for cb in combinations(cerca, r) if cierra(cb)]
        if len(combos) == 1:
            props.append((x, combos[0]))
    uso = Counter(d["idCompra"] for _, ds in props for d in ds)
    return [(x, ds) for x, ds in props if all(uso[d["idCompra"]] == 1 for d in ds)]


def nivel_cuotas(lineas, docs) -> list[tuple[list[dict], list[dict]]]:
    grupos = defaultdict(list)
    for x in lineas:
        m = CUOTA.search(x["detalle"] or "")
        if m and 2 <= int(m.group(2)) <= 24 and int(m.group(1)) <= int(m.group(2)):
            grupos[(x["idContacto"], round(x["importe"], 2), CUOTA.sub("", x["detalle"]).strip())].append(x)
    props = []
    for ls in grupos.values():
        if len(ls) < 2:
            continue
        total = round(sum(x["restante"] for x in ls), 2)
        primera = min(ls, key=lambda x: x["fechaCompra"])
        ds = [d for d in docs.get(primera["idContacto"], [])
              if d["saldoPendiente"] > 0 and abs(_dias(d, primera)) <= 30]
        tol = max(0.10, 0.01 * len(ls))
        combos = [list(cb) for r in (1, 2, 3) for cb in combinations(ds, r)
                  if abs(sum(d["saldoPendiente"] for d in cb) - total) <= tol]
        if len(combos) == 1:
            props.append((sorted(ls, key=lambda x: (x["fechaCompra"], x["idLineaConsumo"])), combos[0]))
    return props


def nivel_fifo(lineas, docs) -> list[tuple[dict, list[dict], float]]:
    saldo = {d["idCompra"]: d["saldoPendiente"] for ds in docs.values() for d in ds}
    props = []
    for x in sorted(lineas, key=lambda x: (x["fechaCompra"], x["idLineaConsumo"])):
        ds = sorted((d for d in docs.get(x["idContacto"], [])
                     if saldo[d["idCompra"]] > .005 and -60 <= _dias(d, x) <= 15),
                    key=lambda d: (d["fecha"], d["idCompra"]))
        elegidos, acum = [], 0.0
        for d in ds:
            if acum >= x["restante"] - .005:
                break
            usar = min(saldo[d["idCompra"]], x["restante"] - acum)
            elegidos.append(d)
            acum += usar
            saldo[d["idCompra"]] = round(saldo[d["idCompra"]] - usar, 2)
        if elegidos:
            props.append((x, elegidos, round(acum, 2)))
    return props


def _aplicar(id_linea, ids) -> str | None:
    try:
        R.vincular_compras_lote(id_linea, ids)
        return None
    except ValueError as e:
        return str(e.args[0] if e.args else e)


def _sin(lineas, docs, hechas, usadas):
    return ([x for x in lineas if x["idLineaConsumo"] not in hechas],
            {k: [d for d in v if d["idCompra"] not in usadas] for k, v in docs.items()})


def main(aplicar: bool) -> None:
    if aplicar:
        from src.features.vinculos.backup import backup_verificado
        print(f"Respaldo verificado: {backup_verificado('conciliar-tarjetas-pendientes')}")
    errores = []

    lineas = _pendientes()
    docs = _docs(lineas)
    ex = nivel_exacta(lineas, docs)
    print(f"1) Exactas: {len(ex)} líneas ${sum(x['restante'] for x, _ in ex):,.2f}")
    for x, ds in ex:
        print(f"   {x['idLineaConsumo']:5} {x['fechaCompra']:%d/%m/%Y} {x['restante']:>13,.2f} {x['proveedor'][:24]:24} -> "
              + ", ".join(f"{d['numeroDocumento']} {d['saldoPendiente']:,.2f}" for d in ds))
        if aplicar and (e := _aplicar(x["idLineaConsumo"], [d["idCompra"] for d in ds])):
            errores.append((x["idLineaConsumo"], e))

    if aplicar:
        lineas = _pendientes()
        docs = _docs(lineas)
    else:
        lineas, docs = _sin(lineas, docs, {x["idLineaConsumo"] for x, _ in ex}, {d["idCompra"] for _, ds in ex for d in ds})
    cu = nivel_cuotas(lineas, docs)
    print(f"2) Cuotas: {len(cu)} compras, {sum(len(ls) for ls, _ in cu)} líneas")
    for ls, ds in cu:
        print(f"   {ls[0]['proveedor'][:24]} {len(ls)} cuotas de {ls[0]['importe']:,.2f} -> "
              + ", ".join(f"{d['numeroDocumento']} {d['saldoPendiente']:,.2f}" for d in ds))
        if aplicar:
            for x in ls:
                if e := _aplicar(x["idLineaConsumo"], [d["idCompra"] for d in ds]):
                    errores.append((x["idLineaConsumo"], e))

    if aplicar:
        lineas = _pendientes()
        docs = _docs(lineas)
    else:
        lineas, docs = _sin(lineas, docs, {x["idLineaConsumo"] for ls, _ in cu for x in ls},
                            {d["idCompra"] for _, ds in cu for d in ds})
    ff = nivel_fifo(lineas, docs)
    completas = sum(1 for x, _, a in ff if a >= x["restante"] - 1)
    print(f"3) FIFO: {len(ff)} líneas ({completas} completas, {len(ff) - completas} parciales) "
          f"${sum(a for _, _, a in ff):,.2f}")
    por_prov = defaultdict(lambda: [0, 0.0, 0.0, None, None])
    for x, ds, a in ff:
        p = por_prov[x["proveedor"]]
        p[0] += 1
        p[1] += x["restante"]
        p[2] += a
        f0 = min(d["fecha"] for d in ds)
        p[3] = f0 if p[3] is None else min(p[3], f0)
        p[4] = x["fechaCompra"] if p[4] is None else max(p[4], x["fechaCompra"])
    for prov, (n, r, a, fd, fl) in sorted(por_prov.items(), key=lambda kv: -kv[1][1]):
        print(f"   {prov[:30]:30} {n:3} líneas  línea ${r:>13,.2f}  cubierto ${a:>13,.2f}  "
              f"facturas desde {fd:%d/%m/%Y}, última línea {fl:%d/%m/%Y}")
    if aplicar:
        for x, ds, _ in ff:
            if e := _aplicar(x["idLineaConsumo"], [d["idCompra"] for d in ds]):
                errores.append((x["idLineaConsumo"], e))
        print(f"Errores al grabar: {len(errores)}")
        for i, e in errores[:30]:
            print(f"   línea {i}: {e}")
        resto = R.get_pendientes()
        print(f"Quedan sin resolver: {len(resto)} líneas ${sum(x['importe'] for x in resto):,.2f}")
    else:
        print("Simulación: no se escribió nada. Usar --aplicar para grabar.")


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
