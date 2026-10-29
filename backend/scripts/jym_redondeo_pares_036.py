"""036 — Jáuregui y Morales (48): redondeo de facturas a lo pagado en los pares 1 a 1 (regla 29/10/2026, ≤0,10%).

Par = factura y pago de casi el mismo importe (diferencia ≤0,10%), del mismo proveedor, pagado entre 5 días antes y
120 días después, sin otro pago exacto. Se empareja por la menor diferencia de importe. No se toca (salvo diferencia ≤0,01%) una factura de
pesos enteros pagada con un importe que no lo es (la diferencia no es redondeo). Método `grupo3_redondeo_036`:
escalar renglones o ajustar Gastos Varios. Idempotente. Uso (desde backend/): python -m scripts.jym_redondeo_pares_036 [idContacto] [--aplicar]
"""

from __future__ import annotations

import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.recalculo_fifo import entrada
from src.features.vinculos.backup import backup_verificado

C = next((int(a) for a in sys.argv[1:] if a.isdigit()), 48)


def pares() -> list[tuple]:
    e = entrada.armar([C])[C]
    facs = [i for i in e["items"] if i["clave"][0] == "Compras" and i["lado"] == "D" and i["importe"] > 0 and i["moneda"] == "ARS"]
    pagos = [i for i in e["items"] if i["lado"] == "C" and i["clase"] == "dinero"]
    cand = []
    for f in facs:
        t = float(f["importe"])
        cerca = lambda p: -5 <= (p["fecha"] - f["fecha"]).days <= 120
        if any(abs(float(p["importe"]) - t) < 0.004 and cerca(p) for p in pagos):
            continue
        for p in pagos:
            x = float(p["importe"])
            if 0.004 < abs(x - t) <= t * 0.001 and cerca(p) and not (round(t, 2) == round(t) and round(x, 2) != round(x) and abs(x - t) > t * 0.0001):
                cand.append((abs(x - t) / t, f, p))
    usados_f, usados_p, salida = set(), set(), []
    for _, f, p in sorted(cand, key=lambda c: c[0]):
        if f["clave"] in usados_f or p["clave"] in usados_p:
            continue
        usados_f.add(f["clave"])
        usados_p.add(p["clave"])
        salida.append((f["clave"][1], f["nro"], float(f["importe"]), round(float(p["importe"]), 2)))
    return salida


if __name__ == "__main__":
    _assert_target_is_wc()
    filas = pares()
    for f in filas:
        print(f)
    print(len(filas), "facturas; ajuste", round(sum(x[3] - x[2] for x in filas), 2))
    if "--aplicar" not in sys.argv or not filas:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    tot = {r["i"]: r for r in fetch_all(
        f"SELECT IdDeuda AS i, GranTotal AS g, TotalDetalleCompra AS d FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda IN ({','.join(str(x[0]) for x in filas)})", ())}
    respaldo = backup_verificado(f"redondeo-pares-{C}-036")
    stmts = []
    for i, _, total, nuevo in filas:
        g, d = float(tot[i]["g"]), float(tot[i]["d"] or 0)
        stmts.append(("UPDATE dbo.Det_Compras SET [Precio Unitario] = [Precio Unitario] * ? WHERE IdCompra = ?", ((nuevo - (g - d)) / d, i))
                     if abs(d) > 1e-6 else
                     ("UPDATE dbo.Compras SET [Gastos Varios] = ISNULL([Gastos Varios], 0) + ? WHERE IdDeuda = ?", (nuevo - total, i)))
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('jym-redondeo-pares-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps({str(x[0]): [x[2], x[3]] for x in filas}), respaldo,
                   f"Cuenta {C}: {len(filas)} facturas redondeadas a su pago 1 a 1 (≤0,10%, regla 29/10/2026).")))
    execute_write_transaction(stmts)
    print("Aplicado. Respaldo:", respaldo, " quedan:", len(pares()))
