"""Solo lectura (autorizado por Sergio 10/11/2026): por cada usuario de Sancor (Irma / Giamigli) baja pólizas y movimientos
completos del portal con el conector de la bóveda y los guarda en JSON. No paga ni cambia nada en Sancor.
Uso: python -m scripts.sancor_relevar_cuentas <carpeta_salida>
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.features.boveda.conectores.sancor import ConectorSancor
from src.features.boveda.servicio import credencial_de

CREDENCIALES = {15: "irma", 16: "giamigli"}


def main(salida: str):
    out = Path(salida)
    con = ConectorSancor()
    with sync_playwright() as pw:
        for idc, nombre in CREDENCIALES.items():
            ses = con.ingresar(pw, credencial_de(idc))
            try:
                vig = con._polizas(ses)
                todas = con._api(ses, "POST", "/api/v1/MyPolicies/PostCardsList",
                                 {"policy": {"client": {"bupId": 0}, "isVigent": False}}).get("policies") or []
                pols = {str(p.get("certificateId")): p for p in vig + todas}
                data = [{"poliza": p, "movimientos": con._movimientos(ses, p)} for p in pols.values()]
                (out / f"{nombre}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
                print(nombre, "pólizas", len(data), "movimientos", sum(len(d["movimientos"]) for d in data))
            finally:
                con.cerrar(ses)


if __name__ == "__main__":
    main(sys.argv[1])
