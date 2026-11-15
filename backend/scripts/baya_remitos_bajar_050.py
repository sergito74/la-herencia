"""050 — baja de la extranet de Bayá Casal (Insumos → mercadería remitida) los remitos: fecha, número, artículo y
cantidad, para tener la fecha de ingreso de cada insumo (Sergio 15/11/2026: "los remitos están en el portal").

Solo lectura (autorización permanente del 20/10/2026, portal 5). Guarda en backups/ (no se sube a git).
Uso (desde backend/): python -m scripts.baya_remitos_bajar_050 <carpeta>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.db.connection import fetch_all
from src.features.boveda import repository, servicio
from src.features.boveda.conectores.baya_casal import ConectorBayaCasal

PORTAL = 5
BASE = "https://extranet.ebayacasal.com.ar"


def bajar(p, seccion: str, desde: str, hasta: str) -> list[list[str]]:
    p.goto(f"{BASE}/{seccion}/")
    p.wait_for_load_state("networkidle")
    if p.query_selector("[name=desde]") is None:
        return [[td.inner_text().strip() for td in tr.query_selector_all("td, th")] for tr in p.query_selector_all("table tbody tr")]
    with p.expect_navigation(timeout=120000):
        p.evaluate("""([d, h]) => { document.querySelector('[name=desde]').value = d; document.querySelector('[name=hasta]').value = h;
                  const f = document.querySelector('[name=desde]').form; f.submit(); }""", [desde, hasta])
    p.wait_for_load_state("networkidle")
    filas = []
    fecha = None
    for tr in p.query_selector_all("table tbody tr"):
        celdas = [td.inner_text().strip() for td in tr.query_selector_all("td, th")]
        if not celdas or len(celdas) < 3:
            continue
        # La tabla agrupa: la fecha y el comprobante van solo en el primer renglón de cada remito.
        if celdas[0][:2].isdigit() and "/" in celdas[0]:
            fecha = celdas[0]
        filas.append(celdas)
    if p.query_selector("[name=desde]") is None:
        pass
    return filas


if __name__ == "__main__":
    destino = Path(sys.argv[1])
    destino.mkdir(parents=True, exist_ok=True)
    if repository.autorizacion_vigente(PORTAL) is None:
        raise SystemExit("Sin autorización vigente para Bayá Casal.")
    cred = servicio.credencial_de(fetch_all("SELECT IdCredencial AS c FROM dbo.Portales WHERE IdPortal = ?", (PORTAL,))[0]["c"])
    with sync_playwright() as pw:
        s = ConectorBayaCasal().ingresar(pw, cred)
        try:
            for sec in ("merrem", "merfac", "merpenfac", "merpenrem"):
                filas = []
                for anio in range(2015, 2027):
                    f_ = bajar(s.pagina, sec, f"{anio}-01-01", f"{anio}-12-31")
                    print(sec, anio, len(f_))
                    filas += f_
                    if sec in ("merpenfac", "merpenrem"):
                        break
                (destino / f"{sec}.json").write_text(json.dumps(filas, ensure_ascii=False, indent=0), encoding="utf-8")
                print(sec, len(filas), "filas", filas[:1], filas[-1:])
        finally:
            s.browser.close()
