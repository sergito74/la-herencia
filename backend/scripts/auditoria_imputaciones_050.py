"""Auditoría (solo lectura) de la imputación de facturas de insumos desde la primera orden (2015) hasta hoy (050, 15/11/2026).

Pasa el método de Sergio (scripts/simulacion_vinculo_orden_050.py: FIFO por marca sin mirar fechas, después por
principio activo o familia; lo que sobra queda en stock) por ventanas que arrancan en un recuento de la planilla
(el más cercano a junio de cada año, antes de la campaña), y compara con lo imputado a mano factura por factura.
La primera ventana (2015 a primer recuento) arranca sin stock. Manda la orden: donde la imputación manual difiere,
la factura queda para revisar. Nada se escribe en la base.

Uso (desde backend/):  python -m scripts.auditoria_imputaciones_050
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from scripts.recuentos_planilla_050 import leer_recuentos
from scripts.simulacion_kardex_corte_050 import STOCK
from scripts.simulacion_vinculo_orden_050 import main as simular

SALIDA = Path(__file__).resolve().parents[2] / "specs" / "050-tamizado-imputacion-cultivos"
PRIMERA = date(2015, 9, 1)


def anclas() -> list[date]:
    fechas = sorted({r["fecha"] for r in leer_recuentos()})
    out = []
    for y in range(fechas[0].year, date.today().year + 1):
        cand = [f for f in fechas if date(y, 4, 1) <= f <= date(y, 9, 30)]
        if cand:
            out.append(min(cand, key=lambda f: abs((f - date(y, 6, 1)).days)))
    return out


def main() -> None:
    a = anclas()
    ventanas = [(PRIMERA, a[0], None)] + [(a[i], a[i + 1] if i + 1 < len(a) else None, a[i]) for i in range(len(a))]
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Desde", "Hasta", "Apertura", "Importe $", "Coincidencia factura por factura %", "Agregada cultivo/campaña %",
               "Facturas 100%", "Facturas <90%"])
    w2 = wb.create_sheet("Para revisar")
    w2.append(["Ventana", "Fecha", "Proveedor", "Nro", "Principio activo", "Renglón", "Método", "Cantidad", "Importe $",
               "Coincidencia %", "Manual", "Según órdenes"])
    w3 = wb.create_sheet("Faltantes")
    w3.append(["Ventana", "Tipo", "Fecha", "Proveedor / Orden", "Nro", "Producto", "Cantidad", "Unidad", "Importe $", "Imputación manual"])
    tot_cp = tot = 0.0
    for ini, fin, rec in ventanas:
        r = simular(ini, fin, rec, auditoria=True, guardar=False)
        etiqueta = f"{ini:%m/%Y} a {fin:%m/%Y}" if fin else f"{ini:%m/%Y} a hoy"
        agM, agK = r["agM"], r["agK"]
        ag = sum(min(agM[z], agK[z]) for z in set(agM) | set(agK)) / (sum(agM.values()) or 1)
        det = r["detalle"]
        ws.append([ini, fin, rec or "sin stock", round(r["tot"], 2), round(r["cp"] / (r["tot"] or 1) * 100, 1), round(ag * 100, 1),
                   sum(1 for d in det if d[8] > 99.5), sum(1 for d in det if d[8] < 90)])
        tot_cp += r["cp"]
        tot += r["tot"]
        for d in sorted(det, key=lambda d: -d[7]):
            if d[8] < 90:
                w2.append([etiqueta, *d])
        for f in r["faltantes"]:
            w3.append([etiqueta, *f])
        print(etiqueta, "importe $M", round(r["tot"] / 1e6, 1), "factura x factura", round(r["cp"] / (r["tot"] or 1) * 100, 1),
              "agregada", round(ag * 100, 1), "para revisar", sum(1 for d in det if d[8] < 90), "faltantes", len(r["faltantes"]))
    ws.append([])
    ws.append(["Total", None, None, round(tot, 2), round(tot_cp / (tot or 1) * 100, 1)])
    for w in wb.worksheets:
        for c in w[1]:
            c.font = Font(bold=True)
    destino = SALIDA / f"auditoria-imputaciones-{date.today():%Y%m%d}.xlsx"
    wb.save(destino)
    print("total", round(tot_cp / (tot or 1) * 100, 1), "Excel:", destino)


if __name__ == "__main__":
    main()
