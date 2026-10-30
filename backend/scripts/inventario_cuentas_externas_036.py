"""036, 30/10/2026: inventario de las cuentas con resumen externo (proveedor, entidad o portal) y su diferencia actual.

Regla de Sergio (30/10/2026): si hay un resumen emitido por el proveedor o la entidad, la verdad está ahí y la cuenta del
sistema lo emula; Access es solo referencia. Fuentes: el último saldo externo registrado en la revisión
(RevisionSaldosExternos, salvo "sin-estado") y la última foto del estado de cuenta de cada portal (Portales_EstadoCuenta).
Compara contra el saldo del sistema a la misma fecha y en la misma moneda. Solo lectura.
Uso (desde backend/): python -m scripts.inventario_cuentas_externas_036 [salida.json]
"""
from __future__ import annotations

import json
import sys

from src.db.connection import fetch_all
from src.features.auditoria_cuentas import bimonetaria


def externos() -> dict[int, dict]:
    out: dict[int, dict] = {}
    for r in fetch_all("SELECT IdContacto c, FechaSaldo f, Saldo s, Moneda m, Fuente fu, Referencia re FROM dbo.RevisionSaldosExternos "
                       "WHERE Anulado = 0 AND Fuente <> 'sin-estado' ORDER BY FechaSaldo", ()):
        out[r["c"]] = {"fecha": str(r["f"])[:10], "saldo": float(r["s"]), "moneda": r["m"], "fuente": r["fu"], "ref": r["re"]}
    for r in fetch_all("SELECT e.IdContacto c, e.FechaCorte f, e.SaldoPortal s, e.Moneda m, p.Nombre n FROM dbo.Portales_EstadoCuenta e "
                       "JOIN dbo.Portales p ON p.IdPortal = e.IdPortal WHERE e.IdContacto IS NOT NULL AND e.Completa = 1 "
                       "ORDER BY e.FechaCorte, e.IdFoto", ()):
        actual = out.get(r["c"])
        if actual is None or str(r["f"])[:10] >= actual["fecha"]:
            out[r["c"]] = {"fecha": str(r["f"])[:10], "saldo": float(r["s"]), "moneda": "Dolares" if r["m"] in ("USD", "Dolares") else "Pesos",
                           "fuente": "portal", "ref": f"Estado de cuenta del portal {r['n']}"}
    return out


def saldo_a(ct: int, fecha: str) -> tuple[float, float]:
    filas = [f for f in bimonetaria.cargar_cuenta(ct, refrescar=True)["filas"] if str(f["fecha"])[:10] <= fecha]
    return (float(filas[-1]["saldoPesos"]), float(filas[-1]["saldoDolares"])) if filas else (0.0, 0.0)


if __name__ == "__main__":
    nombres = {r["i"]: r["n"] for r in fetch_all("SELECT IdContacto i, [Razon Social] n FROM dbo.Contactos", ())}
    fichas = {r["c"]: r["e"] for r in fetch_all("SELECT IdContacto c, Estado e FROM dbo.RevisionFichas", ())}
    salida = []
    for ct, ext in sorted(externos().items()):
        pesos, dolares = saldo_a(ct, ext["fecha"])
        sistema = dolares if ext["moneda"] == "Dolares" else pesos
        # El sistema guarda "saldo = crédito − deuda"; los resúmenes muestran la deuda del cliente en positivo o negativo según
        # el emisor: se compara contra los dos signos y se informa la diferencia menor.
        dif = min(sistema - ext["saldo"], sistema + ext["saldo"], key=abs)
        salida.append({"ct": ct, "razon": nombres.get(ct), "ficha": fichas.get(ct), **ext, "sistema": round(sistema, 2), "diferencia": round(dif, 2)})
    for s in sorted(salida, key=lambda x: -abs(x["diferencia"])):
        marca = "OK " if abs(s["diferencia"]) < 0.01 else "DIF"
        print(f"{marca} {s['ct']:5} {str(s['razon'])[:30]:30} {s['ficha'] or '':22} {s['fecha']} {s['moneda'][:3]} externo {s['saldo']:>16,.2f} "
              f"sistema {s['sistema']:>16,.2f} dif {s['diferencia']:>14,.2f} | {s['fuente']}")
    if len(sys.argv) > 1:
        json.dump(salida, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
