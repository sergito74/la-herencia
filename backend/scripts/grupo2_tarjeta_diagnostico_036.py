"""036 — grupo 2 (cuentas pagadas solo con tarjeta): diagnóstico de solo lectura (estrategia 29/10/2026).

Para cada cuenta cuyos pagos son todos de tarjeta, compara cada factura con lo que le imputan las líneas de resumen
vinculadas (Tarjetas_Resumenes_Lineas_Compras). Clasifica la factura en: cubierta exacta, diferencia ≤0,10% (redondeo),
diferencia mayor (a clasificar por causa) o sin vínculo de tarjeta.
Uso (desde backend/): python -m scripts.grupo2_tarjeta_diagnostico_036 [salida.json]
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

from src.db.connection import fetch_all

if __name__ == "__main__":
    cuentas = [r["ct"] for r in fetch_all(
        "SELECT IdContacto AS ct FROM dbo.vw_MovimientosCuenta_Base GROUP BY IdContacto "
        "HAVING SUM(CASE WHEN Origen IN ('Tarjetas','Tarjeta sin imputar') THEN 1 ELSE 0 END) > 0 "
        "AND SUM(CASE WHEN Origen IN ('Banco Nacion','Galicia','Pagos efectivo','Pagos Valores Recibidos') AND Credito > 0 THEN 1 ELSE 0 END) = 0 "
        "AND SUM(CASE WHEN Origen = 'Compras' AND Deuda > 0 THEN 1 ELSE 0 END) > 0", ())]
    docs = fetch_all(
        "SELECT c.IdContacto AS ct, c.IdDeuda AS i, v.ImporteDocumento AS t, c.Moneda AS m, c.[Tipo documento] AS td "
        f"FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda WHERE c.IdContacto IN ({','.join(map(str, cuentas))})", ())
    vinc = defaultdict(float)
    for r in fetch_all("SELECT IdCompra AS i, ImporteImputado AS x FROM dbo.Tarjetas_Resumenes_Lineas_Compras", ()):
        vinc[r["i"]] += float(r["x"] or 0)
    clase = Counter()
    por_cuenta = defaultdict(Counter)
    for d in docs:
        if d["td"] and "Cr" in d["td"]:
            continue
        t = float(d["t"] or 0)
        if t <= 0:
            continue
        x = vinc.get(d["i"], 0.0)
        if x == 0:
            k = "sin vínculo de tarjeta"
        elif abs(t - x) < 0.005:
            k = "cubierta exacta"
        elif abs(t - x) / t <= 0.001:
            k = "redondeo ≤0,10%"
        else:
            k = "diferencia >0,10%"
        clase[k] += 1
        por_cuenta[d["ct"]][k] += 1
    limpias = sum(1 for c in por_cuenta.values() if set(c) <= {"cubierta exacta", "redondeo ≤0,10%"})
    print("cuentas:", len(cuentas), " facturas:", sum(clase.values()))
    print(dict(clase))
    print("cuentas que quedan resueltas solo con el vínculo (más redondeos):", limpias)
    if len(sys.argv) > 1:
        json.dump({str(k): dict(v) for k, v in por_cuenta.items()}, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False)
