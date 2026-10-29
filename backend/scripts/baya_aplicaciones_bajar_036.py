"""036 — grupo 1: baja de la extranet de Bayá Casal la cuenta corriente con aplicaciones y los PDF de cada
aplicación (CA) y recibo (RI), para copiar sus imputaciones (regla de oro del 28/10/2026).

Solo lectura: autorización permanente de Sergio del 20/10/2026 (portal 5, bóveda 042). Usa el conector existente;
no toca nada del portal fuera del filtro de consulta. Guarda todo en backups/ (no se sube a git).
Uso (desde backend/): python -m scripts.baya_aplicaciones_bajar_036 <carpeta>
"""

from __future__ import annotations

import base64
import json
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.db.connection import fetch_all
from src.features.boveda import repository, servicio
from src.features.boveda.conectores.baya_casal import ConectorBayaCasal

PORTAL = 5

if __name__ == "__main__":
    destino = Path(sys.argv[1])
    destino.mkdir(parents=True, exist_ok=True)
    if repository.autorizacion_vigente(PORTAL) is None:
        raise SystemExit("Sin autorización vigente para Bayá Casal.")
    id_cred = fetch_all("SELECT IdCredencial AS c FROM dbo.Portales WHERE IdPortal = ?", (PORTAL,))[0]["c"]
    cred = servicio.credencial_de(id_cred)
    conector = ConectorBayaCasal()
    with sync_playwright() as pw:
        sesion = conector.ingresar(pw, cred)
        try:
            filas = conector._cuenta(sesion, date(2010, 1, 1), aplicaciones=True)
            (destino / "cuenta-con-aplicaciones.json").write_text(json.dumps(filas, ensure_ascii=False, indent=0), encoding="utf-8")
            hrefs = {}
            for f in filas:
                if len(f) > 9 and f[9].startswith("PDF:"):
                    clave = base64.b64decode(f[9][4:].split("file=")[1]).decode("latin-1")
                    if clave.split(";")[1] in ("AP", "RI"):
                        hrefs[clave] = f[9][4:]
            print(len(filas), "filas;", len(hrefs), "comprobantes de aplicación/recibo")
            sin_pdf = []
            for clave, href in hrefs.items():
                _, tipo, pv, nro, _f = clave.split(";")
                archivo = destino / f"{'CA' if tipo == 'AP' else 'RI'}_{int(pv):04d}_{int(nro):08d}.pdf"
                if archivo.exists():
                    continue
                try:
                    archivo.write_bytes(conector._bajador(sesion, href)())
                except Exception as e:  # los CA viejos no tienen PDF en el portal
                    sin_pdf.append(clave)
            (destino / "sin-pdf.json").write_text(json.dumps(sin_pdf), encoding="utf-8")
            print("sin PDF:", len(sin_pdf))
        finally:
            sesion.browser.close()
