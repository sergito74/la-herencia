"""036 — redondeo de facturas pagadas 1 a 1 con una diferencia chica (solo lectura salvo --aplicar en otra etapa).

Sergio 29/10/2026: las facturas que tienen identificado su pago 1 a 1 se redondean a lo pagado, con criterio, para no
arrastrar centavos en el FIFO. Límite de prueba: $1,50. Un pago es "1 a 1" con una factura si es el único pago de la
cuenta a ±60 días con importe a menos de LIMITE de esa factura, y esa factura es la única a menos de LIMITE de ese pago
en la misma ventana. La tarjeta usa su vínculo explícito (Tarjetas_Resumenes_Lineas_Compras).
Uso (desde backend/): python -m scripts.redondeo_pagos_uno_a_uno_036 <idContacto> [salida.xlsx]
"""

from __future__ import annotations

import sys
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Font

from src.db.connection import fetch_all
from src.features.recalculo_fifo import entrada

LIMITE = 1.50
VENTANA = 60
NOMBRE = {"Banco Nacion": "BNA", "Galicia": "Galicia", "Pagos efectivo": "Efectivo", "Tarjetas": "Tarjeta",
          "Tarjeta sin imputar": "Tarjeta"}


def pares(ct: int) -> list[dict]:
    e = entrada.armar([ct])[ct]
    docs = [i for i in e["items"] if i["clave"][0] == "Compras" and i["lado"] == "D" and i["clase"] == "doc"]
    pagos = [i for i in e["items"] if i["lado"] == "C" and i["clase"] == "dinero"]
    cerca = lambda a, b: abs((a["fecha"] - b["fecha"]).days) <= VENTANA
    dif = lambda d, p: round(float(d["importe"]) - float(p["importe"]), 2)
    salida = []
    for d in docs:
        cand = [p for p in pagos if cerca(d, p) and 0.005 < abs(dif(d, p)) <= LIMITE]
        exactos = [p for p in pagos if cerca(d, p) and abs(dif(d, p)) <= 0.005]
        if len(cand) != 1 or exactos:
            continue
        p = cand[0]
        rivales = [o for o in docs if o is not d and cerca(o, p) and abs(dif(o, p)) <= LIMITE]
        if rivales:
            continue
        salida.append({"id": d["clave"][1], "nro": d["nro"], "fecha": d["fecha"], "total": round(float(d["importe"]), 2),
                       "pago": f"{NOMBRE.get(p['clave'][0], p['clave'][0])} {p['fecha']:%d/%m/%Y}", "pagado": round(float(p["importe"]), 2),
                       "dif": dif(d, p), "dias": (p["fecha"] - d["fecha"]).days})
    return sorted(salida, key=lambda x: x["fecha"])


if __name__ == "__main__":
    filas = pares(int(sys.argv[1]))
    for f in filas:
        print(f["nro"], f["fecha"], f["total"], f["pago"], f["pagado"], f["dif"], f"{f['dias']} días")
    print(len(filas), "facturas; ajuste total", round(sum(f["dif"] for f in filas), 2))
    if len(sys.argv) > 2:
        libro = Workbook()
        hoja = libro.active
        hoja.append(["Factura", "Emisión", "Total", "Pago 1 a 1", "Importe pagado", "Redondeo", "Días entre factura y pago"])
        for c in hoja[1]:
            c.font = Font(bold=True)
        for f in filas:
            hoja.append([f["nro"], f["fecha"], f["total"], f["pago"], f["pagado"], -f["dif"], f["dias"]])
            hoja.cell(hoja.max_row, 2).number_format = "DD/MM/YYYY"
        for col, w in zip("ABCDEFG", (16, 12, 14, 22, 15, 11, 12)):
            hoja.column_dimensions[col].width = w
        libro.save(sys.argv[2])
