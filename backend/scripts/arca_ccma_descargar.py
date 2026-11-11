"""Descarga de solo lectura del CCMA (Cuenta Corriente de Monotributistas y Autónomos) de ARCA, con la clave fiscal de
Sergio (credencial 8) o Lucy (credencial 9). Autorizado por Sergio el 11/11/2026 (solo lectura). Solo navega, filtra por
período, pulsa "Consultar" y guarda la página en PDF: no genera VEP, volantes ni ningún trámite.

uso: python -m scripts.arca_ccma_descargar sergio|lucy SALIDA.pdf [--desde MM/AAAA] [--hasta MM/AAAA] [--explorar DIR]
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.features.boveda.conectores.espera import cargada, ir
from src.features.boveda.servicio import credencial_de

LOGIN = "https://auth.afip.gob.ar/contribuyente_/login.xhtml"
MIS_SERVICIOS = "https://portalcf.cloud.afip.gob.ar/portal/app/mis-servicios"
CREDENCIAL = {"sergio": 8, "lucy": 9}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("quien", choices=CREDENCIAL)
    a.add_argument("salida")
    a.add_argument("--desde", default="09/2024")
    a.add_argument("--hasta", default=None)
    a.add_argument("--explorar", default=None)
    o = a.parse_args()
    cred = credencial_de(CREDENCIAL[o.quien])
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
            if "portalcf" not in p.url:
                raise SystemExit("ARCA no aceptó el ingreso: " + p.url)
            ir(p, MIS_SERVICIOS)
            with p.expect_popup(timeout=90000) as pop:
                p.get_by_text("CCMA", exact=False).first.click()
            q = pop.value
            cargada(q)
            q.wait_for_timeout(2000)
            if q.locator("select[name=selectCuit]").count():
                q.select_option("select[name=selectCuit]", cred.usuario.replace("-", ""))
                with q.expect_navigation(timeout=90000):
                    q.click("input[name=btnEnvia]")
                cargada(q)
            q.wait_for_timeout(4000)
            if o.explorar:
                d = Path(o.explorar)
                q.screenshot(path=str(d / f"{o.quien}-1.png"), full_page=True)
                (d / f"{o.quien}-1.html").write_text(q.content(), encoding="utf-8")
                (d / f"{o.quien}-1.txt").write_text(q.inner_text("body"), encoding="utf-8")
                print("url", q.url)
                return
            # Cálculo de deuda (consulta): período desde/hasta y "CALCULO DE DEUDA".
            if o.desde:
                q.fill("input[name=perdesde2]", o.desde)
            if o.hasta:
                q.fill("input[name=perhasta2]", o.hasta)
            q.on("dialog", lambda d: (print("aviso de ARCA:", d.message), d.accept()))
            with q.expect_navigation(timeout=120000):
                q.click("input[name=CalDeud]")
            cargada(q)
            q.wait_for_timeout(4000)
            # Filtro avanzado: solo Autónomo / AUT (sin el monotributo personal), botón "Consultar". Nunca "VOLANTE DE PAGO".
            q.select_option("select[name=MonoAut]", label="Autonomo")
            q.select_option("select[name=tipoMov]", label="AUT")
            q.click("input[name=Cons]")
            for _ in range(60):
                q.wait_for_timeout(2000)
                try:
                    if "Monot." not in q.inner_text("body"):
                        break
                except Exception:
                    pass
            cargada(q)
            Path(o.salida).with_suffix(".txt").write_text(q.inner_text("body"), encoding="utf-8")
            q.emulate_media(media="print")
            q.pdf(path=o.salida, format="A4", print_background=True)
            print("ok", o.salida)
        finally:
            b.close()


if __name__ == "__main__":
    main()
