"""Simulación (solo lectura) del kardex FIFO por principio activo, como lo llevaba Sergio (050, 14/11/2026).

Método de sus planillas (Calculo Uso Insumos, UREA - Imputaciones, Planilla proporciones aplicaciones):
  · entran las facturas de insumo; salen las aplicaciones de las órdenes (ya repartidas por lote/cultivo/campaña);
  · cada salida consume las facturas en orden de llegada; si toma de dos, cada parte se reparte entre los
    cultivos de esa orden en la misma proporción;
  · lo que no se usó queda en stock (Adm. General / No Aplica).
Se agrupa por principio activo (la marca aplicada no siempre es la comprada).

Nada se escribe en la base. Compara, por factura + principio activo, el reparto en $ contra lo imputado a mano.
Parámetros de la variante: ATRASO (días que una salida puede adelantarse a la factura: remito antes que factura).

Uso (desde backend/):  python -m scripts.simulacion_kardex_fifo_050 [ATRASO_DIAS]
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from src.db.connection import fetch_all
from src.features.remitos import stock_datos
from scripts.simulacion_reparto_proporcional_050 import aplicaciones

SALIDA = Path(__file__).resolve().parents[2] / "specs" / "050-tamizado-imputacion-cultivos"
NO_APLICA = 20
STOCK = ("stock", None)


def _d(v):
    return v.date() if hasattr(v, "date") else v


def _ia_norm(a: str | None) -> str:
    return " ".join((a or "").upper().replace("EQUIVALENTE ACIDO", "").replace("EQUIVALETE ACIDO", "").split())


def main(atraso: int = 60) -> dict:
    ia = {f["i"]: _ia_norm(f["a"]) for f in fetch_all(
        "SELECT NroReg_int i, [INGREDIENTE ACTIVO] a FROM dbo.Formulados WHERE NroReg_int IS NOT NULL")}
    bases, equiv = stock_datos.unidades_base(), stock_datos.equivalencias()
    cult = {f["i"]: f["n"] for f in fetch_all("SELECT IdCultivo i, Cultivo n FROM dbo.Cultivos")}
    camp = {f["i"]: f["n"] for f in fetch_all("SELECT [IdCampaña] i, [Campaña] n FROM dbo.[Campañas]")}

    # Entradas: renglones de factura/NC de insumo con producto del catálogo.
    entradas: dict[str, list[dict]] = defaultdict(list)
    manual: dict[tuple, Counter] = defaultdict(Counter)
    info: dict[tuple, dict] = {}
    sin_unidad = 0
    for f in fetch_all(
        """
        SELECT d.IdDetalleCompra id, d.IdCompra idc, c.Fecha f, co.[Razon Social] prov, c.[Nro Documento] nro, c.[Tipo documento] tipo,
               d.IdFormulado p, d.[Producto/Servicio] txt, d.Cantidad q, d.Unidad u, de.IdCultivo cu, d.[IdCampaña] ca,
               ISNULL(d.Cantidad,0)*ISNULL(d.[Precio Unitario],0)*CASE WHEN c.Moneda='Dolares' THEN ISNULL(c.[Tipo de Cambio],0) ELSE 1 END pesos
        FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        WHERE c.Fecha >= '2015-09-01' AND d.IdFormulado > 0
        """
    ):
        a = ia.get(f["p"]) or f"#{f['p']}"
        k = (f["idc"], a)
        pesos = float(f["pesos"] or 0)
        ca = f["ca"] if f["ca"] not in (None, NO_APLICA) else None
        manual[k][(f["cu"], ca) if f["cu"] and ca else STOCK] += pesos
        info.setdefault(k, {"fecha": f["f"], "prov": f["prov"], "nro": f["nro"], "txt": f["txt"], "pesos": 0.0})
        info[k]["pesos"] += pesos
        factor, falta = stock_datos.factor_a_base(f["p"], f["u"], bases, equiv)
        sin_unidad += falta
        q = float(f["q"] or 0) * factor
        es_nc = "credito" in (f["tipo"] or "").lower()
        if q > 0 and not es_nc:
            entradas[a].append({"k": k, "fecha": _d(f["f"]), "q": q, "unit": pesos / q, "resto": q})

    # Salidas: aplicaciones por principio activo.
    salidas: dict[str, list[tuple]] = defaultdict(list)
    for pid, lista in aplicaciones().items():
        salidas[ia.get(pid) or f"#{pid}"].extend(lista)

    motor: dict[tuple, Counter] = defaultdict(Counter)
    sin_factura = Counter()
    for a, sal in salidas.items():
        ent = sorted(entradas.get(a, []), key=lambda e: e["fecha"])
        for fecha, cu, ca, q in sorted(sal, key=lambda s: s[0]):
            pend = q
            for e in ent:
                if pend <= 1e-9:
                    break
                if e["resto"] <= 1e-9 or e["fecha"] > fecha + timedelta(days=atraso):
                    continue
                t = min(e["resto"], pend)
                e["resto"] -= t
                pend -= t
                motor[e["k"]][(cu, ca)] += t * e["unit"]
            if pend > 1e-9:
                sin_factura[a] += pend
    for lista in entradas.values():
        for e in lista:
            if e["resto"] > 1e-9:
                motor[e["k"]][STOCK] += e["resto"] * e["unit"]

    res, pes = Counter(), Counter()
    detalle = []
    coinc_pond = tot = 0.0
    for k, man in manual.items():
        p = info[k]["pesos"]
        if p <= 0:
            continue
        mo = motor.get(k, Counter())
        tm, tmo = sum(man.values()), sum(mo.values())
        if tm <= 0 or tmo <= 0:
            b, c = "sin entrada (NC/cantidad 0)", 0.0
        else:
            c = sum(min(man[x] / tm, mo[x] / tmo) for x in set(man) | set(mo))
            b = "100%" if c > 0.995 else "90-99%" if c >= 0.9 else "50-89%" if c >= 0.5 else "<50%"
        res[b] += 1
        pes[b] += p
        coinc_pond += c * p
        tot += p
        if b != "100%":
            detalle.append([info[k]["fecha"], info[k]["prov"], info[k]["nro"], k[1], info[k]["txt"], round(p, 2), round(c * 100, 1),
                            _txt(man, cult, camp), _txt(mo, cult, camp)])

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Coincidencia", "Factura+principio activo", "Importe $"])
    for b in ("100%", "90-99%", "50-89%", "<50%", "sin entrada (NC/cantidad 0)"):
        ws.append([b, res[b], round(pes[b], 2)])
    ws.append(["ponderada por $", None, round(coinc_pond / tot * 100, 1)])
    ws.append(["renglones sin equivalencia de unidad", sin_unidad])
    ws3 = wb.create_sheet("Aplicado sin factura")
    ws3.append(["Principio activo", "Cantidad aplicada sin factura previa"])
    for a, q in sin_factura.most_common():
        ws3.append([a, round(q, 2)])
    ws2 = wb.create_sheet("Diferencias")
    ws2.append(["Fecha", "Proveedor", "Nro", "Principio activo", "Renglón", "Importe $", "Coincidencia %", "Manual", "Kardex FIFO"])
    for f in sorted(detalle, key=lambda r: -r[5]):
        ws2.append(f)
    for w in (ws, ws2, ws3):
        for c in w[1]:
            c.font = Font(bold=True)
    destino = SALIDA / f"simulacion-kardex-fifo-{date.today():%Y%m%d}.xlsx"
    wb.save(destino)
    print("atraso", atraso, dict(res), "ponderado", round(coinc_pond / tot * 100, 1), "sin unidad", sin_unidad)
    print("Excel:", destino)
    return {"res": res, "pond": coinc_pond / tot}


def _txt(c: Counter, cult, camp) -> str:
    t = sum(c.values()) or 1
    return " · ".join(("stock" if k == STOCK else f"{cult.get(k[0], k[0])} {camp.get(k[1], '')}".strip()) + f" {v / t * 100:.0f}%"
                      for k, v in sorted(c.items(), key=lambda x: -x[1]))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 60)
