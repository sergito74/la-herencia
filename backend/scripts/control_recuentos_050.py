"""Control (solo lectura) del kardex contra los recuentos de Sergio desde 2019 (050, 15/11/2026).

Entre dos recuentos seguidos de la planilla Stock Insumos.xlsx, por principio activo (o familia de fertilizante):
    recuento anterior + facturado (facturas; las NC/ND no entran mercadería) − aplicado (órdenes) = recuento siguiente.
Lo que no cierra es un faltante concreto (mes + producto): factura o remito que falta, orden sin cargar, o un
recuento que no se hizo. Hay meses sin recuento porque no se contó; el tramo entonces es más largo, no un error.
Nada se escribe en la base.

Uso (desde backend/):  python -m scripts.control_recuentos_050
"""

from __future__ import annotations

from collections import Counter, defaultdict
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
        ia[int(f["i"])] = f"FAMILIA {fam}" if fam else (f["n"] if f["t"] in ("Semilla", "Fertilizante") else " ".join(_ia_norm(f["a"]).replace("EQUIVALENTE", "").split()[:4]))

    def clave(pid):
        return ia.get(int(pid)) or f"#{pid}"

    def factor(pid, u):
        fa, falta = stock_datos.factor_a_base(pid, u, bases, equiv)
        if (u or "").strip().upper().startswith("TON") and (falta or fa == 1.0):
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
            q = float(f["q"]) * (1000.0 if (f["u"] or "").upper().startswith("TON") or float(f["q"]) < 100 else 1.0)
        else:
            k, q = clave(pid), float(f["q"]) * factor(pid, f["u"])
        entradas.append((_d(f["f"]), k, q))
    salidas = [(fe, clave(pid), q) for pid, lista in aplicaciones().items() if pid for fe, _, _, q in lista]

    # Saldo acumulado por producto: lo comprado − lo aplicado = galpón (recuento) + en el proveedor / directo al campo.
    # · Si el galpón tiene MÁS de lo que se compró: falta una factura o un remito (o el recuento contó de más) → faltante.
    # · Si lo comprado sin usar queda "en el proveedor" más de 12 meses sin bajar: falta una orden (o se perdió) → faltante.
    # Cada faltante se informa una vez y el saldo se re-ancla al recuento (no arrastra el error a los tramos siguientes).
    filas, total, cierra = [], 0, 0
    claves = set().union(*(d for _, _, d in stock)) | {k for _, k, _ in entradas} | {k for _, k, _ in salidas}
    en_prov_final = {}
    for k in claves:
        ent = sorted((fe, q) for fe, kk, q in entradas if kk == k)
        sal = sorted((fe, q) for fe, kk, q in salidas if kk == k)
        f_prev, h_prev, d_prev = stock[0]
        propio = d_prev.get(k, 0.0)          # lo propio (galpón + proveedor) arranca igual al primer recuento
        desde = None                         # desde cuándo hay saldo en el proveedor sin bajar
        for f1, h1, d1 in stock[1:]:
            if f1 <= f_prev:
                continue
            e = sum(q for fe, q in ent if f_prev < fe <= f1)
            a = sum(q for fe, q in sal if f_prev < fe <= f1)
            antes = propio
            propio += e - a
            galpon = d1.get(k, 0.0)
            prov = propio - galpon
            if abs(antes) < 1e-6 and abs(propio) < 1e-6 and abs(galpon) < 1e-6:
                f_prev = f1
                continue
            total += 1
            tol = TOL * max(abs(galpon), abs(propio), 1)
            signo = 1 if prov > tol else -1 if prov < -tol else 0
            if signo == 0:
                cierra += 1
                desde = None
            else:
                # Saldo transitorio: el proveedor guarda lo comprado (+) o se retiró y se factura después (−).
                if desde is None or desde[1] != signo:
                    desde = (f1, signo)
                mov = a if signo > 0 else e
                if (f1 - desde[0]).days > 365 and mov <= 1e-6:
                    filas.append([desde[0], f1, k, round(e, 2), round(a, 2), round(propio, 2), round(galpon, 2), round(prov, 2),
                                  "comprado sin uso hace más de un año: falta una orden (o no está en el proveedor)" if signo > 0
                                  else "en el galpón sin factura hace más de un año: falta factura/remito (o se contó de más)"])
                    propio, desde = galpon, None
                else:
                    cierra += 1
            f_prev = f1
        en_prov_final[k] = propio - stock[-1][2].get(k, 0.0)

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Tramos producto × par de recuentos", total])
    ws.append(["Cierran (±2%, contando lo que guarda el proveedor)", cierra])
    ws.append(["No cierran", total - cierra])
    ws.append(["Recuentos leídos", len(stock), stock[0][0], stock[-1][0]])
    w2 = wb.create_sheet("No cierran")
    w2.append(["Desde", "Hasta", "Principio activo / producto", "Facturado en el tramo", "Aplicado en el tramo",
               "Propio (comprado − aplicado)", "Galpón (recuento)", "En el proveedor (propio − galpón)", "Lectura"])
    for f in sorted(filas, key=lambda r: (r[0], r[2])):
        w2.append(f)
    w3 = wb.create_sheet("En el proveedor hoy")
    w3.append(["Producto", "Comprado sin aplicar que no está en el galpón (último recuento)"])
    for k, v in sorted(en_prov_final.items(), key=lambda x: -abs(x[1])):
        if abs(v) > 1e-6:
            w3.append([k, round(v, 2)])
    for w in wb.worksheets:
        for c in w[1]:
            c.font = Font(bold=True)
    destino = SALIDA / f"control-recuentos-{date.today():%Y%m%d}.xlsx"
    wb.save(destino)
    print("tramos", total, "cierran", cierra, f"({cierra / max(total, 1) * 100:.0f}%)", "recuentos", len(stock))
    por_anio = defaultdict(lambda: [0, 0])
    for f in filas:
        por_anio[f[1].year][0] += 1
    print("faltantes por tipo:", dict(Counter(f[8][:30] for f in filas)))
    print("no cierran por año:", dict(sorted((a, v[0]) for a, v in por_anio.items())))
    print("Excel:", destino)


if __name__ == "__main__":
    main()
