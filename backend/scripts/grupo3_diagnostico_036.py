"""036 — grupo 3 (cuentas chicas, 1 a 5 facturas): diagnóstico de solo lectura (estrategia 29/10/2026).

Cuentas con 1 a 5 facturas de compra que no son del grupo 2 (tienen algún pago que no es tarjeta). Corre el FIFO estricto
de cada una y clasifica cada factura: pagada exacta, redondeo ≤0,10% (resto en la factura o aplicación de centavos de
otro pago), diferencia mayor o sin pagar. Uso (desde backend/): python -m scripts.grupo3_diagnostico_036 [salida.json]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date

from src.db.connection import fetch_all
from src.features.recalculo_fifo import cambio, controles, entrada, motor

LIMITE = 0.001
EXCLUIDAS = {97}  # 97: dueño desconocido, sin tocar (Sergio 29/10/2026)
HECHAS = ("%Cargill%", "%Lartirigoyen%", "%uregui%")


def cuentas() -> list[int]:
    hechas = {r["ct"] for p in HECHAS for r in fetch_all(
        "SELECT DISTINCT IdContacto AS ct FROM dbo.vw_MovimientosCuenta_Base WHERE [Razon Social] LIKE ?", (p,))}
    return [r["ct"] for r in fetch_all(
        "SELECT IdContacto AS ct FROM dbo.vw_MovimientosCuenta_Base GROUP BY IdContacto "
        "HAVING COUNT(DISTINCT CASE WHEN Origen = 'Compras' AND Deuda > 0 THEN IdOrigen END) BETWEEN 1 AND 5 "
        "AND SUM(CASE WHEN Origen IN ('Banco Nacion','Galicia','Pagos efectivo','Pagos Valores Recibidos','Venta Granos',"
        "'Retenciones') AND Credito > 0 THEN 1 ELSE 0 END) > 0", ()) if r["ct"] not in EXCLUIDAS | hechas]


def clasificar(res: dict) -> dict[tuple, str]:
    por_doc: dict[tuple, list[float]] = {}
    for a in res["aplicaciones"]:
        por_doc.setdefault(tuple(a["debito"])[:2], []).append(float(a["importeArs"]))
    salida = {}
    for i in res["items"]:
        if i["clave"][0] != "Compras" or i["lado"] != "D" or i["clase"] != "doc":
            continue
        t = float(i["importe"])
        if t <= 0:
            continue
        partes = por_doc.get(tuple(i["clave"])[:2], [])
        resto = float(i["rem"])
        centavos = [x for x in partes if x < t * LIMITE]
        if not partes:
            k = "sin pagar"
        elif resto < 0.005 and not centavos:
            k = "pagada exacta"
        elif resto <= t * LIMITE and len(centavos) <= 1:
            k = "redondeo ≤0,10%"
        elif resto > 0.005:
            k = "pagada en parte"
        else:
            k = "otra"
        salida[tuple(i["clave"])[:2]] = k
    return salida


if __name__ == "__main__":
    ids = cuentas()
    hoy = date.today()
    tc = cambio.funcion_tc(hoy)
    total, por_cuenta, cierran = Counter(), {}, 0
    for ct, e in entrada.armar(ids).items():
        if not e["items"]:
            continue
        res = motor.recalcular(e["items"], e["fijos"], tc, hoy)
        ev = controles.evaluar(e, res, tc)
        k = clasificar(res)
        c = Counter(k.values())
        total.update(c)
        cierran += ev["cierraDespues"]
        por_cuenta[ct] = {"nombre": e["nombre"], "cierra": ev["cierraDespues"], "saldo": ev["saldo"],
                          "controles": [x["codigo"] for x in ev["controles"]], "facturas": dict(c),
                          "redondeos": [list(d) for d, v in k.items() if v == "redondeo ≤0,10%"]}
    print("cuentas:", len(por_cuenta), " cierran con FIFO:", cierran, " facturas:", sum(total.values()))
    print(dict(total))
    limpias = sum(1 for v in por_cuenta.values() if v["cierra"] and set(v["facturas"]) <= {"pagada exacta", "redondeo ≤0,10%"})
    print("cuentas limpias (exactas + redondeos):", limpias)
    if len(sys.argv) > 1:
        json.dump(por_cuenta, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, default=str, indent=1)
