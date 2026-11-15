"""Control (solo lectura) del kardex contra los recuentos de Sergio desde 2019 (050, 15/11/2026).

Entre dos recuentos seguidos de la planilla Stock Insumos.xlsx, por principio activo (o familia de fertilizante):
    recuento anterior + facturado (facturas; las NC/ND no entran mercadería) − aplicado (órdenes) = recuento siguiente.
Lo que no cierra es un faltante concreto (mes + producto): factura o remito que falta, orden sin cargar, o un
recuento que no se hizo. Hay meses sin recuento porque no se contó; el tramo entonces es más largo, no un error.
Nada se escribe en la base.

Uso (desde backend/):  python -m scripts.control_recuentos_050
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from src.db.connection import fetch_all
from src.features.remitos import stock_datos
from scripts.recuentos_planilla_050 import Catalogo, familia_fertilizante, leer_recuentos
from scripts.simulacion_kardex_corte_050 import MONETARIAS, RUBROS, Sugeridor, _d, _ia_norm
from scripts.simulacion_reparto_proporcional_050 import aplicaciones

SALIDA = Path(__file__).resolve().parents[2] / "specs" / "050-tamizado-imputacion-cultivos"
TOL = 0.02  # solo para clasificar "cierra" en el resumen; la diferencia se muestra entera.


def main() -> None:
    sug, cat = Sugeridor(), Catalogo()
    bases, equiv = stock_datos.unidades_base(), stock_datos.equivalencias()
    ia: dict[int, str] = {}
    for f in fetch_all("SELECT CAST(IdProducto AS bigint) i, Producto n, TipoProducto t, IngredienteActivo a FROM dbo.vw_ProductosBase"):
        if f["i"] is None:
            continue
        fam = familia_fertilizante(f["n"]) if f["t"] == "Fertilizante" else None
        ia[int(f["i"])] = f"FAMILIA {fam}" if fam else (f["n"] if f["t"] in ("Semilla", "Fertilizante") else _ia_norm(f["a"]))

    def clave(pid):
        return ia.get(int(pid)) or f"#{pid}"

    def factor(pid, u):
        fa, falta = stock_datos.factor_a_base(pid, u, bases, equiv)
        if falta and (u or "").strip().upper().startswith("TON"):
            return 1000.0
        return fa

    recs = leer_recuentos()
    stock = []
    for r in recs:
        d = defaultdict(float)
        for x in r["renglones"]:
            pid = cat.producto(x["marca"], sug)
            d[clave(pid) if pid else f"? {x['marca']}"] += x["q"] * factor(pid, x["unidad"]) if pid else x["q"]
        stock.append((r["fecha"], r["hoja"], d))

    entradas = []
    for f in fetch_all(
        f"""SELECT c.Fecha f, c.[Nro Documento] nro, co.[Razon Social] prov, d.IdFormulado p, d.[Producto/Servicio] txt,
                   d.Cantidad q, d.Unidad u
            FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra JOIN dbo.Rubros ru ON ru.IdRubro = d.IdRubro
            LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
            WHERE c.Fecha >= '2019-01-01' AND c.[Tipo documento] = 'Factura' AND d.Cantidad > 0 AND ru.Rubro IN ({",".join("?" * len(RUBROS))})""",
        RUBROS,
    ):
        if (f["u"] or "").strip().upper() in MONETARIAS:
            continue
        pid = f["p"] or sug.sugerir(f["txt"])[0]
        if not pid:
            fam = familia_fertilizante(f["txt"])
            if not fam:
                continue
            k = f"FAMILIA {fam}"
            q = float(f["q"]) * (1000.0 if (f["u"] or "").upper().startswith("TON") else 1.0)
        else:
            k, q = clave(pid), float(f["q"]) * factor(pid, f["u"])
        entradas.append((_d(f["f"]), k, q))
    salidas = [(fe, clave(pid), q) for pid, lista in aplicaciones().items() if pid for fe, _, _, q in lista]

    filas, cierra, total = [], 0, 0
    for (f0, h0, s0), (f1, h1, s1) in zip(stock, stock[1:]):
        if f1 <= f0:
            continue
        ent, sal = defaultdict(float), defaultdict(float)
        for fe, k, q in entradas:
            if f0 < fe <= f1:
                ent[k] += q
        for fe, k, q in salidas:
            if f0 < fe <= f1:
                sal[k] += q
        for k in set(s0) | set(s1) | set(ent) | set(sal):
            esperado = s0.get(k, 0) + ent.get(k, 0) - sal.get(k, 0)
            real = s1.get(k, 0)
            if abs(esperado) < 1e-6 and abs(real) < 1e-6:
                continue
            total += 1
            dif = real - esperado
            ok = abs(dif) <= TOL * max(abs(real), abs(esperado), 1)
            cierra += ok
            if not ok:
                filas.append([f0, f1, k, round(s0.get(k, 0), 2), round(ent.get(k, 0), 2), round(sal.get(k, 0), 2),
                              round(esperado, 2), round(real, 2), round(dif, 2),
                              "sobra en el galpón (falta orden o compra anterior)" if dif > 0 else "falta en el galpón (falta factura/remito o recuento)"])

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Tramos producto × par de recuentos", total])
    ws.append(["Cierran (±2%)", cierra])
    ws.append(["No cierran", total - cierra])
    ws.append(["Recuentos leídos", len(stock), stock[0][0], stock[-1][0]])
    w2 = wb.create_sheet("No cierran")
    w2.append(["Desde", "Hasta", "Principio activo / producto", "Recuento anterior", "Facturado", "Aplicado", "Esperado",
               "Recuento siguiente", "Diferencia", "Lectura"])
    for f in sorted(filas, key=lambda r: (r[0], r[2])):
        w2.append(f)
    for w in wb.worksheets:
        for c in w[1]:
            c.font = Font(bold=True)
    destino = SALIDA / f"control-recuentos-{date.today():%Y%m%d}.xlsx"
    wb.save(destino)
    print("tramos", total, "cierran", cierra, f"({cierra / max(total, 1) * 100:.0f}%)", "recuentos", len(stock))
    por_anio = defaultdict(lambda: [0, 0])
    for f in filas:
        por_anio[f[1].year][0] += 1
    print("no cierran por año:", dict(sorted((a, v[0]) for a, v in por_anio.items())))
    print("Excel:", destino)


if __name__ == "__main__":
    main()
