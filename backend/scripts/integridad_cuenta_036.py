"""036 — integridad de compras y pagos de una cuenta, antes del FIFO (solo lectura).

Señales: (1) tramos en que el saldo acumulado queda a favor nuestro (pagamos más de lo facturado → falta factura
o sobra pago); (2) pagos duplicados (mismo importe, ±7 días, distinto medio o mismo número); (3) facturas
duplicadas (mismo número); (4) meses con facturas y sin pagos durante mucho tiempo.
Uso (desde backend/): python -m scripts.integridad_cuenta_036 <idContacto>
"""

from __future__ import annotations

import sys
from collections import defaultdict

from src.db.connection import fetch_all


def _p(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


if __name__ == "__main__":
    ct = int(sys.argv[1])
    filas = fetch_all("SELECT Fecha AS f, Documento AS doc, [Nro Documento] AS nro, ISNULL(Deuda,0) AS d, ISNULL(Credito,0) AS c, "
                      "Origen AS o, IdOrigen AS i FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ? ORDER BY Fecha, Origen", (ct,))
    saldo, tramo, tramos = 0.0, None, []
    for f in filas:
        saldo += float(f["d"]) - float(f["c"])
        if saldo < -1 and tramo is None:
            tramo = {"desde": f["f"], "min": saldo}
        elif tramo is not None:
            tramo["min"] = min(tramo["min"], saldo)
            if saldo >= -1:
                tramo["hasta"] = f["f"]
                tramos.append(tramo)
                tramo = None
    if tramo:
        tramo["hasta"] = None
        tramos.append(tramo)
    print(f"Saldo final: {_p(saldo)}")
    print("\n1) Tramos con saldo a favor nuestro (pagamos antes de tener la factura):")
    for t in tramos:
        dias = (t["hasta"] - t["desde"]).days if t["hasta"] else None
        if dias is None or dias > 45:
            print(f"   {t['desde']:%d/%m/%Y} → {t['hasta']:%d/%m/%Y}" if t["hasta"] else f"   {t['desde']:%d/%m/%Y} → hoy",
                  f"({dias} días)" if dias else "", f"llegó a −{_p(-t['min'])}")
    pagos = [f for f in filas if float(f["c"]) > 0 and f["o"] != "Compras"]
    print("\n2) Pagos posiblemente duplicados (mismo importe, ±7 días):")
    for a_i, a in enumerate(pagos):
        for b in pagos[a_i + 1:]:
            if (b["f"] - a["f"]).days > 7:
                break
            if abs(float(a["c"]) - float(b["c"])) < 0.01:
                print(f"   {a['f']:%d/%m/%Y} {a['o']} {a['nro'] or ''} ${_p(float(a['c']))}  |  {b['f']:%d/%m/%Y} {b['o']} {b['nro'] or ''}")
    print("\n3) Facturas con número repetido:")
    por_nro = defaultdict(list)
    for f in filas:
        if f["o"] == "Compras" and f["nro"] and f["nro"] not in ("S/D", "S/N", "0"):
            por_nro[f["nro"]].append(f)
    for nro, fs in por_nro.items():
        if len(fs) > 1:
            print(f"   {nro}: " + ", ".join(f"{x['f']:%d/%m/%Y} {x['doc']} ${_p(float(x['d']) or float(x['c']))}" for x in fs))
    print("\n4) Por año: facturado / pagado / saldo al cierre")
    anual = defaultdict(lambda: [0.0, 0.0])
    for f in filas:
        anual[f["f"].year][0] += float(f["d"])
        anual[f["f"].year][1] += float(f["c"])
    acum = 0.0
    for y in sorted(anual):
        acum += anual[y][0] - anual[y][1]
        print(f"   {y}: deuda {_p(anual[y][0]):>15}  pagos {_p(anual[y][1]):>15}  saldo {_p(acum):>15}")
