"""Casas Particulares de ARCA (Irma Miranda), solo lectura (autorizado por Sergio 11/11/2026). Ingresa con la clave
fiscal de Lucy (credencial 9) o Sergio (8), abre el servicio y navega/guarda páginas. No genera VEP ni pagos ni altas.

uso: python -m scripts.arca_casas_particulares lucy DIR [--paso clic1 --paso clic2 ...] [--pdf nombre]
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.features.boveda.conectores.espera import cargada, ir
from src.features.boveda.servicio import credencial_de

LOGIN = "https://auth.afip.gob.ar/contribuyente_/login.xhtml"
MIS_SERVICIOS = "https://portalcf.cloud.afip.gob.ar/portal/app/mis-servicios"
PROHIBIDO = ("generar", "pagar", "vep", "alta", "baja", "modific", "eliminar", "confirmar", "registrar")


def volcar(q, d: Path, n: str):
    q.screenshot(path=str(d / f"{n}.png"), full_page=True)
    (d / f"{n}.txt").write_text(q.inner_text("body"), encoding="utf-8")
    (d / f"{n}.html").write_text(q.content(), encoding="utf-8")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("quien", choices=("lucy", "sergio"))
    a.add_argument("dir")
    a.add_argument("--paso", action="append", default=[])
    a.add_argument("--pdf", default=None)
    a.add_argument("--ver-recibo-nuevo", action="store_true")
    a.add_argument("--detalle", type=int, action="append", default=[], help="n-ésimo 'DETALLE DE PAGO' (0 = el más nuevo)")
    o = a.parse_args()
    d = Path(o.dir)
    cred = credencial_de({"sergio": 8, "lucy": 9}[o.quien])
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome", headless=True)
        try:
            p = b.new_context(viewport={"width": 1400, "height": 1000}).new_page()
            ir(p, LOGIN)
            p.fill("input[id$=username]", cred.usuario.replace("-", ""))
            p.click("input[id$=btnSiguiente]")
            cargada(p)
            p.fill("input[type=password]", cred.clave.valor())
            p.click("input[id$=btnIngresar]")
            cargada(p)
            ir(p, MIS_SERVICIOS)
            p.wait_for_timeout(3000)
            volcar(p, d, "0-servicios")
            with p.expect_popup(timeout=90000) as pop:
                p.get_by_text("CASAS PARTICULARES", exact=False).first.click()
            q = pop.value
            cargada(q)
            q.wait_for_timeout(5000)
            volcar(q, d, "1")
            for i, paso in enumerate(o.paso, 2):
                if any(x in paso.lower() for x in PROHIBIDO):
                    raise SystemExit(f"paso no permitido (solo lectura): {paso}")
                q.get_by_text(paso, exact=False).first.click()
                q.wait_for_timeout(6000)
                cargada(q)
                volcar(q, d, str(i))
            hrefs = q.eval_on_selector_all("a[href*='DetalleRup.aspx']", "e => e.map(x => x.href)")
            for n in o.detalle:
                ir(q, hrefs[n])
                q.wait_for_timeout(4000)
                volcar(q, d, f"detalle-{n}")
                q.emulate_media(media="print")
                q.pdf(path=str(d / f"detalle-{n}.pdf"), format="A4", print_background=True)
                q.emulate_media(media="screen")
                print("detalle", n)
            if o.ver_recibo_nuevo:
                # Solo abre el formulario del período en curso para leerlo: no completa ni envía nada.
                h = q.eval_on_selector_all("a[href*='GenerarRecibos.aspx']", "e => e.map(x => x.href)")
                if h:
                    ir(q, h[0])
                    q.wait_for_timeout(4000)
                    volcar(q, d, "recibo-en-curso")
            if o.pdf:
                q.emulate_media(media="print")
                q.pdf(path=str(d / o.pdf), format="A4", print_background=True)
            print("url", q.url)
        finally:
            b.close()


if __name__ == "__main__":
    main()
