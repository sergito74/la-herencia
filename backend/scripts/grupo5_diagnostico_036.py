"""036 — grupo 5 (cuentas con documentos en US$): control final de solo lectura (estrategia 29/10/2026).

Por cuenta: saldo en pesos y en dólares, moneda que gobierna, ficha de revisión, partidas que el FIFO deja abiertas,
si las aplicaciones grabadas coinciden con el FIFO (las de portal son manuales y se informan aparte) y documentos
en US$ sin TC o sin comprobante en disco. Uso (desde backend/): python -m scripts.grupo5_diagnostico_036 [salida.json]
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date

from src.db.connection import fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.recalculo_fifo import cambio, entrada, motor

COMPRAS = os.path.expanduser(r"~\Dropbox\Giamigli de Bolivar SA\Compras")
PORTAL = {217, 226, 258, 61}  # FEDEA, Bayá Casal, Cargill, Lartirigoyen: imputación copiada del portal


def cuentas() -> list[int]:
    return [r["ct"] for r in fetch_all(
        "SELECT DISTINCT IdContacto AS ct FROM dbo.Compras WHERE Moneda = 'Dolares' AND IdContacto IS NOT NULL "
        "AND IdContacto <> 97 ORDER BY 1", ())]


def _pdf(ruta: str | None) -> bool:
    for p in (ruta or "").split("#"):
        p = p.strip()
        if p and (os.path.exists(p) or os.path.exists(os.path.join(COMPRAS, p))):
            return True
    return False


def diagnosticar(ct: int, hoy: date, tc) -> dict:
    e = entrada.armar([ct])[ct]
    res = motor.recalcular(e["items"], e["fijos"], tc, hoy)
    s = bimonetaria.cargar_cuenta(ct, refrescar=True)
    ficha = fetch_all("SELECT Estado, SaldoAlCierre, Moneda, Corte FROM dbo.RevisionFichas WHERE IdContacto = ?", (ct,))
    docs = fetch_all("SELECT IdDeuda AS i, [Nro Documento] AS n, [Tipo de Cambio] AS tc, [Documento Original] AS d "
                     "FROM dbo.Compras WHERE IdContacto = ? AND Moneda = 'Dolares'", (ct,))
    apl = fetch_all("SELECT a.Origen AS o, COUNT(*) AS n FROM dbo.AplicacionesPago a JOIN dbo.Compras c "
                    "ON c.IdDeuda = a.IdDocumentoAplicado WHERE a.Anulada = 0 AND c.IdContacto = ? GROUP BY a.Origen", (ct,))
    return {
        "ct": ct, "razon": fetch_all("SELECT [Razon Social] AS r FROM dbo.Contactos WHERE IdContacto = ?", (ct,))[0]["r"],
        "gobierna": s["gobierna"], "saldoPesos": s["saldoPesos"], "saldoDolares": s["saldoDolares"],
        "ficha": {k: str(v) for k, v in ficha[0].items()} if ficha else None,
        "abiertos": [(str(i["fecha"]), i["lado"], i["clase"], i["clave"][0], i["nro"], i["moneda"], round(float(i["rem"]), 2))
                     for i in res["items"] if float(i["rem"]) > 0.01],
        "excepcionesDatos": e["excepcionesDatos"], "marcas": sorted(res.get("marcas", [])),
        "docsUsd": len(docs), "sinTc": [d["n"] for d in docs if not d["tc"] or float(d["tc"]) <= 1],
        "sinPdf": [d["n"] for d in docs if not _pdf(d["d"])],
        "aplicaciones": {a["o"]: a["n"] for a in apl}, "portal": ct in PORTAL,
    }


if __name__ == "__main__":
    hoy = date.today()
    tc = cambio.funcion_tc(hoy)
    salida = [diagnosticar(c, hoy, tc) for c in cuentas()]
    for d in salida:
        f = d["ficha"] or {}
        print(d["ct"], d["razon"][:26], d["gobierna"], "$", d["saldoPesos"], "US$", d["saldoDolares"], "ficha",
              f.get("Estado"), f.get("SaldoAlCierre"), f.get("Moneda"), "abiertos", len(d["abiertos"]),
              "sinTC", len(d["sinTc"]), "sinPDF", len(d["sinPdf"]), d["aplicaciones"])
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as fh:
            json.dump(salida, fh, ensure_ascii=False, indent=1, default=str)
