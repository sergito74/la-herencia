"""036 — grupo 4 (cuentas corrientes con más de 5 facturas): diagnóstico de solo lectura (estrategia 29/10/2026).

Cuentas con más de 5 facturas de compra y algún pago que no es tarjeta, sin las del grupo 1 (proveedores con resumen
en "Resumenes de Cuenta"). Corre el FIFO estricto de cada una, clasifica cada factura como el grupo 3 y marca lo que
pide revisar integridad: pagos sin factura al final (anticipos abiertos), facturas impagas viejas y diferencias ≤1%.
Orden: de mayor a menor movimiento. Uso (desde backend/): python -m scripts.grupo4_diagnostico_036 [salida.json]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date

from scripts.grupo3_diagnostico_036 import EXCLUIDAS, clasificar
from src.db.connection import fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.recalculo_fifo import cambio, entrada, motor

GRUPO_1 = ("%ASP%", "%Agrovet%", "%Baya%Casal%", "%Cargill%", "%Catalpa%", "%Cooperativa Agropecuaria%",
           "%Cooperativa Electrica%", "%Cuatro Vientos%", "EDP%", "%El Paye%", "%FEDEA%", "%Ferias del Centro%",
           "%Gentos%", "%uregui%", "%Lartirigoyen%", "%Madelan%", "%Nidera%", "%Sunanco%")


def cuentas() -> list[tuple[int, str, float]]:
    fuera = {r["ct"] for p in GRUPO_1 for r in fetch_all(
        "SELECT IdContacto AS ct FROM dbo.Contactos WHERE [Razon Social] LIKE ?", (p,))} | EXCLUIDAS
    return [(r["ct"], r["rs"], float(r["mov"])) for r in fetch_all(
        "SELECT IdContacto AS ct, MAX([Razon Social]) AS rs, SUM(ABS(Deuda)) AS mov FROM dbo.vw_MovimientosCuenta_Base "
        "GROUP BY IdContacto "
        "HAVING COUNT(DISTINCT CASE WHEN Origen = 'Compras' AND Deuda > 0 THEN IdOrigen END) > 5 "
        "AND SUM(CASE WHEN Origen IN ('Banco Nacion','Galicia','Pagos efectivo','Pagos Valores Recibidos','Venta Granos',"
        "'Retenciones') AND Credito > 0 THEN 1 ELSE 0 END) > 0 ORDER BY SUM(ABS(Deuda)) DESC", ()) if r["ct"] not in fuera]


def diagnosticar(ct: int, hoy: date, tc) -> dict:
    e = entrada.armar([ct])[ct]
    res = motor.recalcular(e["items"], e["fijos"], tc, hoy)
    clases = Counter(clasificar(res).values())
    abiertos = [i for i in res["items"] if float(i["rem"]) > 0.01]
    s = bimonetaria.cargar_cuenta(ct, refrescar=True)
    return {
        "clases": dict(clases),
        "facturasAbiertas": [(str(i["fecha"]), i["nro"], round(float(i["rem"]), 2)) for i in abiertos if i["lado"] == "D"],
        "pagosAbiertos": [(str(i["fecha"]), i["clave"][0], i["nro"], round(float(i["rem"]), 2)) for i in abiertos if i["lado"] == "C"],
        "saldoPesos": s["saldoPesos"], "saldoDolares": s["saldoDolares"], "gobierna": s["gobierna"],
    }


if __name__ == "__main__":
    hoy = date.today()
    tc = cambio.funcion_tc(hoy)
    salida = []
    for ct, rs, mov in cuentas():
        d = {"ct": ct, "razon": rs, "movimiento": round(mov, 2), **diagnosticar(ct, hoy, tc)}
        salida.append(d)
        print(ct, rs[:30], round(mov), d["clases"], "abiertas", len(d["facturasAbiertas"]), "pagos", len(d["pagosAbiertos"]),
              "saldo", d["saldoPesos"])
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            json.dump(salida, f, ensure_ascii=False, indent=1, default=str)
