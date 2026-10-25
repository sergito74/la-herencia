"""Foto de solo lectura: cierres reales frente a pendientes antiguos del traspaso."""
import json
from datetime import date, datetime
from pathlib import Path

from src.features.cajas_efectivo.operaciones import read
from src.features.auditoria_cuentas.bimonetaria import cargar_cuentas

IDS = (406, 72, 71, 210, 398, 562, 458, 32, 123, 632, 575, 502, 39, 508, 47, 600, 374, 142, 492, 250, 41, 119)
CUT = date(2026, 9, 30)


def run():
    marks = ",".join("?" for _ in IDS)
    raw = read("SELECT IdContacto,COUNT(*) n,SUM(CASE WHEN Fecha<? THEN Credito-Deuda ELSE 0 END) saldoCorte,"
               "SUM(Credito-Deuda) saldoActual FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto IN (" + marks + ") GROUP BY IdContacto",
               ("2026-10-01", *IDS))
    accounts = {r["IdContacto"]: r for r in raw}
    fichas = {r["IdContacto"]: r for r in read("SELECT * FROM dbo.RevisionFichas WHERE IdContacto IN (" + marks + ")", IDS)}
    nombres = {r["IdContacto"]: r["nombre"] for r in read("SELECT IdContacto,[Razon Social] nombre FROM dbo.Contactos WHERE IdContacto IN (" + marks + ")", IDS)}
    bim = cargar_cuentas(list(IDS))
    for id_, a in accounts.items():
        b = bim[id_]
        a.update(nombre=nombres[id_], ficha=fichas.get(id_), tieneDolares=b["tieneDolares"])
        if b["tieneDolares"]:
            filas = [f for f in b["filas"] if f["fecha"] <= CUT]
            a.update(saldoCorteValuado=filas[-1]["saldoPesos"] if filas else 0,
                     saldoPesos=b["saldoPesos"], saldoDolares=b["saldoDolares"])
        else:
            a.update(saldoCorteValuado=a["saldoCorte"], saldoPesos=a["saldoActual"], saldoDolares=None)
    folder = Path(__file__).resolve().parents[2] / "backups/continuacion-cuentas-20261025"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"cuentas-{datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps({"corte": CUT, "cuentas": list(accounts.values())}, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"archivo": str(path), "cuentas": [{"id": a["IdContacto"], "nombre": a["nombre"],
          "estado": (a["ficha"] or {}).get("Estado"), "saldoCorte": a["saldoCorteValuado"], "saldoActual": a["saldoPesos"],
          "saldoUSD": a["saldoDolares"]} for a in accounts.values()]}, default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
