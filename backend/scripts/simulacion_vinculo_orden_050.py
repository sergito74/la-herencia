"""Simulación (solo lectura) factura de insumo ↔ orden de trabajo por cantidad exacta (050, 14/11/2026).

Hallazgo en las planillas de Sergio: el proveedor factura cada retiro (p. ej. Bayá Casal 0020-00451187, SNIPER II
620 L = Planilla Retiro 12/09/2025) y la factura se reparte como la orden de ese retiro. Entonces:
  1. Por factura + producto se suma la cantidad facturada (todos sus renglones, que Sergio abría por cultivo).
  2. Se busca la orden o combinación de hasta 4 órdenes, no usadas, cuya cantidad del producto (o, si no, del mismo
     principio activo) suma exactamente lo facturado (±0,5%), entre 365 días antes y 60 días después de la factura.
  3. Vinculada: la factura se reparte como esas órdenes (lote → cultivo/campaña). Sin vínculo: kardex FIFO por
     principio activo con pendientes (lo aplicado sin stock lo cubre la factura que llega después).
Compara contra lo imputado a mano, por factura y en el agregado por cultivo/campaña. No escribe en la base.

Uso (desde backend/):  python -m scripts.simulacion_vinculo_orden_050
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from src.db.connection import fetch_all
from src.features.remitos import stock_datos
from scripts.simulacion_kardex_corte_050 import CORTE, MONETARIAS, RUBROS, STOCK, Sugeridor, _anterior, _d, _ia_norm

SALIDA = Path(__file__).resolve().parents[2] / "specs" / "050-tamizado-imputacion-cultivos"
NO_APLICA = 20
TOL = 0.005


def ordenes_por_producto() -> list[dict]:
    """Una fila por orden + producto: fecha, cantidad total y reparto por cultivo/campaña."""
    filas = fetch_all(
        """
        SELECT ot.IdOrdenTrabajo o, oti.IdProducto p, COALESCE(ot.FechaEjecucion, ot.FechaPedido) f, oti.CantidadTotal q,
               d.IdCultivo cu, d.IdCampania ca, d.CantidadAsignada qa
        FROM dbo.Ordenes_Trabajo ot JOIN dbo.Ordenes_Trabajo_Insumos oti ON oti.IdOrdenTrabajo = ot.IdOrdenTrabajo
        LEFT JOIN dbo.Ordenes_Trabajo_Distrib d ON d.IdOrdenInsumo = oti.IdOrdenInsumo
        WHERE ot.Estado <> 'Anulada' AND oti.CantidadTotal > 0 AND COALESCE(ot.FechaEjecucion, ot.FechaPedido) >= '2024-07-01'
        """
    )
    g: dict[tuple, dict] = {}
    vistos = set()
    for f in filas:
        k = (f["o"], f["p"])
        x = g.setdefault(k, {"orden": f["o"], "p": f["p"], "fecha": _d(f["f"]), "q": 0.0, "reparto": Counter(), "usada": False})
        if (k, id(f)) not in vistos:
            pass
        x["reparto"][(f["cu"], f["ca"])] += float(f["qa"] or 0)
    # La cantidad total es por renglón de insumo; puede haber más de un renglón del mismo producto en la orden.
    for f in fetch_all(
        """SELECT ot.IdOrdenTrabajo o, oti.IdProducto p, SUM(oti.CantidadTotal) q FROM dbo.Ordenes_Trabajo ot
           JOIN dbo.Ordenes_Trabajo_Insumos oti ON oti.IdOrdenTrabajo = ot.IdOrdenTrabajo
           WHERE ot.Estado <> 'Anulada' AND oti.CantidadTotal > 0 GROUP BY ot.IdOrdenTrabajo, oti.IdProducto"""
    ):
        if (f["o"], f["p"]) in g:
            g[(f["o"], f["p"])]["q"] = float(f["q"])
    return list(g.values())


def buscar(objetivo: float, candidatos: list[dict], fecha: date) -> list[dict] | None:
    cand = sorted((c for c in candidatos if not c["usada"] and fecha - timedelta(days=365) <= c["fecha"] <= fecha + timedelta(days=60)),
                  key=lambda c: abs((c["fecha"] - fecha).days))[:14]
    mejor = None
    for n in range(1, 5):
        for combo in combinations(cand, n):
            if abs(sum(c["q"] for c in combo) - objetivo) <= TOL * objetivo:
                dist = sum(abs((c["fecha"] - fecha).days) for c in combo)
                if mejor is None or dist < mejor[0]:
                    mejor = (dist, combo)
        if mejor:
            return list(mejor[1])
    return None


def main() -> None:
    ia = {int(f["i"]): _ia_norm(f["a"]) for f in fetch_all(
        "SELECT IdProducto i, IngredienteActivo a FROM dbo.vw_ProductosBase WHERE IdProducto IS NOT NULL")}
    bases, equiv = stock_datos.unidades_base(), stock_datos.equivalencias()
    cult = {f["i"]: f["n"] for f in fetch_all("SELECT IdCultivo i, Cultivo n FROM dbo.Cultivos")}
    camp = {f["i"]: f["n"] for f in fetch_all("SELECT [IdCampaña] i, [Campaña] n FROM dbo.[Campañas]")}
    sug = Sugeridor()
    tipo = {int(f["i"]): ("Semillas/fertilizantes" if f["t"] in ("Semilla", "Fertilizante") else "Agroquímicos")
            for f in fetch_all("SELECT IdProducto i, TipoProducto t FROM dbo.vw_ProductosBase WHERE IdProducto IS NOT NULL")}

    facturas: dict[tuple, dict] = {}
    cobertura = Counter()
    for f in fetch_all(
        f"""
        SELECT d.IdCompra idc, c.Fecha f, co.[Razon Social] prov, c.[Nro Documento] nro, c.[Tipo documento] tipo,
               d.IdFormulado p, d.[Producto/Servicio] txt, d.Cantidad q, d.Unidad u, de.IdCultivo cu, d.[IdCampaña] ca,
               ISNULL(d.Cantidad,0)*ISNULL(d.[Precio Unitario],0)*CASE WHEN c.Moneda='Dolares' THEN ISNULL(c.[Tipo de Cambio],0) ELSE 1 END pesos
        FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.Rubros ru ON ru.IdRubro = d.IdRubro
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        WHERE c.Fecha >= ? AND ru.Rubro IN ({",".join("?" * len(RUBROS))})
        """,
        (CORTE.isoformat(), *RUBROS),
    ):
        if (f["u"] or "").strip().upper() in MONETARIAS or "credito" in (f["tipo"] or "").lower():
            cobertura["ajuste en $ / NC (sigue a su factura)"] += 1
            continue
        if _anterior(camp.get(f["ca"])):
            cobertura["historia (campaña anterior)"] += 1
            continue
        pid, via = (f["p"], "con producto") if f["p"] else sug.sugerir(f["txt"])
        if pid is None:
            cobertura["sin producto"] += 1
            continue
        cobertura[via] += 1
        k = (f["idc"], pid)
        x = facturas.setdefault(k, {"fecha": _d(f["f"]), "prov": f["prov"], "nro": f["nro"], "txt": f["txt"], "p": pid,
                                    "ia": ia.get(pid) or f"#{pid}", "q": 0.0, "pesos": 0.0, "manual": Counter()})
        factor, _ = stock_datos.factor_a_base(pid, f["u"], bases, equiv)
        pesos = float(f["pesos"] or 0)
        x["q"] += float(f["q"] or 0) * factor
        x["pesos"] += pesos
        ca = f["ca"] if f["ca"] not in (None, NO_APLICA) else None
        x["manual"][(f["cu"], ca) if f["cu"] and ca else STOCK] += pesos

    # Apertura (hoja "Facturas Insumos en Stock" de Sergio): facturas anteriores al arranque que él dejó en Stock.
    for f in fetch_all(
        f"""
        SELECT d.IdCompra idc, c.Fecha f, co.[Razon Social] prov, c.[Nro Documento] nro, d.IdFormulado p, d.[Producto/Servicio] txt,
               d.Cantidad q, d.Unidad u,
               ISNULL(d.Cantidad,0)*ISNULL(d.[Precio Unitario],0)*CASE WHEN c.Moneda='Dolares' THEN ISNULL(c.[Tipo de Cambio],0) ELSE 1 END pesos
        FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.Rubros ru ON ru.IdRubro = d.IdRubro
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        WHERE c.Fecha >= '2022-07-01' AND c.Fecha < ? AND de.Destino = 'Stock' AND c.[Tipo documento] NOT LIKE '%dito%'
          AND ISNULL(d.Unidad, '') NOT IN ('ARS', 'USD') AND ru.Rubro IN ({",".join("?" * len(RUBROS))})
        """,
        (CORTE.isoformat(), *RUBROS),
    ):
        pid = f["p"] or sug.sugerir(f["txt"])[0]
        if not pid or not f["q"]:
            continue
        factor, _ = stock_datos.factor_a_base(pid, f["u"], bases, equiv)
        k = (f["idc"], pid)
        x = facturas.setdefault(k, {"fecha": _d(f["f"]), "prov": f["prov"], "nro": f["nro"], "txt": f["txt"], "p": pid, "apertura": True,
                                    "ia": ia.get(pid) or f"#{pid}", "q": 0.0, "pesos": 0.0, "manual": Counter()})
        x["q"] += float(f["q"]) * factor
        x["pesos"] += float(f["pesos"] or 0)
        cobertura["apertura: en Stock antes del arranque"] += 1

    ordenes = ordenes_por_producto()
    por_prod, por_ia = defaultdict(list), defaultdict(list)
    for o in ordenes:
        por_prod[o["p"]].append(o)
        por_ia[ia.get(o["p"]) or f"#{o['p']}"].append(o)

    # Método de Sergio (facturas Bayá Casal 0020-00451187/91): por marca, las facturas en orden se asignan a las
    # órdenes en orden, por cantidad, sin importar si la factura es anterior o posterior (el proveedor guarda lo
    # pedido). Paso 1 por marca; paso 2 los remanentes por principio activo. Sobrante de factura → stock.
    motor: dict[tuple, Counter] = defaultdict(Counter)
    metodo: dict[tuple, str] = {}
    resto_f = {k: x["q"] for k, x in facturas.items() if x["q"] > 0 and x["pesos"] > 0}
    resto_o = {id(o): o["q"] for o in ordenes if o["fecha"] >= CORTE}

    def emparejar(fks, ords, etiqueta):
        fks = sorted(fks, key=lambda k: (facturas[k]["fecha"], k))
        ords = sorted(ords, key=lambda o: (o["fecha"], o["orden"]))
        i = j = 0
        while i < len(fks) and j < len(ords):
            k, o = fks[i], ords[j]
            if resto_f[k] <= 1e-9:
                i += 1
                continue
            if resto_o[id(o)] <= 1e-9:
                j += 1
                continue
            t = min(resto_f[k], resto_o[id(o)])
            resto_f[k] -= t
            resto_o[id(o)] -= t
            unit = facturas[k]["pesos"] / facturas[k]["q"]
            tot = sum(o["reparto"].values()) or 1
            for kk, v in o["reparto"].items():
                motor[k][kk] += t * unit * v / tot
            metodo.setdefault(k, etiqueta)

    fpp, opp = defaultdict(list), defaultdict(list)
    for k in resto_f:
        fpp[facturas[k]["p"]].append(k)
    for o in ordenes:
        if id(o) in resto_o:
            opp[o["p"]].append(o)
    for pid in fpp:
        emparejar(fpp[pid], opp.get(pid, []), "FIFO por marca")
    fia, oia = defaultdict(list), defaultdict(list)
    for k, q in resto_f.items():
        if q > 1e-9:
            fia[facturas[k]["ia"]].append(k)
    for o in ordenes:
        if id(o) in resto_o and resto_o[id(o)] > 1e-9:
            oia[ia.get(o["p"]) or f"#{o['p']}"].append(o)
    for a in fia:
        emparejar(fia[a], oia.get(a, []), "FIFO por principio activo")
    for k, q in resto_f.items():
        if q > 1e-9:
            motor[k][STOCK] += q * facturas[k]["pesos"] / facturas[k]["q"]
            metodo.setdefault(k, "stock")

    # Comparación.
    res, porm = Counter(), defaultdict(Counter)
    agM, agK = Counter(), Counter()
    portipo = defaultdict(lambda: [0.0, 0.0, Counter(), Counter()])
    detalle = []
    cp = tot = 0.0
    for k, x in facturas.items():
        man, mo = x["manual"], motor.get(k, Counter())
        tm, tmo = sum(man.values()), sum(mo.values())
        if x.get("apertura") or x["pesos"] <= 0 or tm <= 0 or tmo <= 0:
            continue
        c = sum(min(man[z] / tm, mo[z] / tmo) for z in set(man) | set(mo))
        # Lo que Sergio dejó en stock y la simulación ya asignó a una orden posterior es consistente (se usó después).
        c = min(1.0, c + man[STOCK] / tm - min(man[STOCK] / tm, mo[STOCK] / tmo))
        b = "100%" if c > 0.995 else "90-99%" if c >= 0.9 else "50-89%" if c >= 0.5 else "<50%"
        res[b] += 1
        porm[metodo[k]][b] += 1
        cp += c * x["pesos"]
        tot += x["pesos"]
        tp = portipo[tipo.get(x["p"], "Agroquímicos")]
        tp[0] += c * x["pesos"]
        tp[1] += x["pesos"]
        for z, v in man.items():
            tp[2][z] += v
        for z, v in mo.items():
            tp[3][z] += v * x["pesos"] / tmo
        for z, v in man.items():
            agM[z] += v
        for z, v in mo.items():
            agK[z] += v * x["pesos"] / tmo
        detalle.append([x["fecha"], x["prov"], x["nro"], x["ia"], x["txt"], metodo[k], round(x["q"], 2), round(x["pesos"], 2),
                        round(c * 100, 1), _txt(man, cult, camp), _txt(mo, cult, camp)])
    agreg = sum(min(agM[z], agK[z]) for z in set(agM) | set(agK)) / (sum(agM.values()) or 1)

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Renglones desde 01/07/2025", "Cantidad"])
    for kk, v in cobertura.items():
        ws.append([kk, v])
    ws.append([])
    ws.append(["Método", "100%", "90-99%", "50-89%", "<50%"])
    for m, cc in porm.items():
        ws.append([m, cc["100%"], cc["90-99%"], cc["50-89%"], cc["<50%"]])
    ws.append([])
    ws.append(["Coincidencia ponderada por $ (factura por factura)", round(cp / tot * 100, 1)])
    ws.append(["Coincidencia agregada por cultivo/campaña", round(agreg * 100, 1)])
    ws.append([])
    ws.append(["Cultivo/campaña", "Manual $", "Simulación $", "Diferencia $"])
    for z in sorted(set(agM) | set(agK), key=lambda z: -agM[z]):
        nombre = "stock" if z == STOCK else f"{cult.get(z[0], z[0])} {camp.get(z[1], '')}".strip()
        ws.append([nombre, round(agM[z], 2), round(agK[z], 2), round(agK[z] - agM[z], 2)])
    w2 = wb.create_sheet("Facturas")
    w2.append(["Fecha", "Proveedor", "Nro", "Principio activo", "Renglón", "Método", "Cantidad", "Importe $", "Coincidencia %",
               "Manual", "Simulación"])
    for f in sorted(detalle, key=lambda r: (r[8], -r[7])):
        w2.append(f)
    for w in wb.worksheets:
        for cel in w[1]:
            cel.font = Font(bold=True)
    destino = SALIDA / f"simulacion-vinculo-orden-{date.today():%Y%m%d}.xlsx"
    wb.save(destino)
    print("cobertura", dict(cobertura))
    for m, cc in porm.items():
        print(m, dict(cc))
    for t, (a1, a2, m1, k1) in portipo.items():
        ag = sum(min(m1[z], k1[z]) for z in set(m1) | set(k1)) / (sum(m1.values()) or 1)
        print(t, "importe $M", round(a2 / 1e6, 1), "factura x factura", round(a1 / a2 * 100, 1), "agregado", round(ag * 100, 1))
        ws.append([t, "importe $", round(a2, 2), "factura x factura %", round(a1 / a2 * 100, 1), "agregado %", round(ag * 100, 1)])
    wb.save(destino)
    print("ponderada", round(cp / tot * 100, 1), "agregada", round(agreg * 100, 1))
    print("Excel:", destino)


def _txt(c: Counter, cult, camp) -> str:
    t = sum(c.values()) or 1
    return " · ".join(("stock" if k == STOCK else f"{cult.get(k[0], k[0])} {camp.get(k[1], '')}".strip()) + f" {v / t * 100:.0f}%"
                      for k, v in sorted(c.items(), key=lambda x: -x[1]))


if __name__ == "__main__":
    main()
