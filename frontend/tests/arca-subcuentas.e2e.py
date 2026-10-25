"""Recorrido UI ARCA con API simulada: jamás escribe WC. Servidor Next en 3100."""
import json
import re
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
BASE = os.environ.get("ARCA_UI_BASE", "http://127.0.0.1:3100")
out = ROOT / "backups/arca-analisis-20261025"
out.mkdir(parents=True, exist_ok=True)
catalogo = {"iva":"IVA — retenciones, pagos y devoluciones", "ganancias":"Ganancias y anticipos",
            "sicore-ganancias":"Retenciones de Ganancias efectuadas — SICORE", "por-identificar":"Por identificar"}
mov = {"fecha":"2026-09-01","documento":"VEP","numeroDocumento":"123", "origen":"Galicia", "idOrigen":101,
       "detalle":"VEP sin concepto", "deuda":"0", "credito":"100.0001", "deudaOriginal":"0", "creditoOriginal":"100.0001",
       "saldo":"100.0001", "partes":[{"subcuenta":"por-identificar","deuda":"0","credito":"100.0001"}],
       "version":0,"manual":False,"revisarReparto":False,"motivo":None}
historia = []
rol = "Administrador"
errores = []
CORS = {"access-control-allow-origin":BASE, "access-control-allow-credentials":"true",
        "access-control-allow-headers":"content-type", "access-control-allow-methods":"GET,PUT,OPTIONS"}


def route_handler(route):
    from urllib.parse import urlparse, parse_qs
    req=route.request
    u=urlparse(req.url)
    p=u.path
    def reply(value, status=200):
        route.fulfill(status=status,headers=CORS,content_type="application/json",body=json.dumps(value))
    if req.method == "OPTIONS":
        return route.fulfill(status=204,headers=CORS)
    if p == "/api/auth/me":
        return reply({"idUsuario":1,"usuario":"fixture","nombre":"Fixture","rol":rol})
    if p.endswith("/119/saldo"):
        return reply({"idContacto":119,"saldoParcial":100.0001,"saldoDolares":None})
    if p == "/api/arca/historial":
        return reply(historia)
    if p == "/api/arca/clasificacion":
        b=req.post_data_json
        from decimal import Decimal as D
        if b["partes"] and sum(D(x["credito"]) for x in b["partes"]) != D(mov["creditoOriginal"]):
            return reply({"detail":"El reparto debe sumar exactamente la deuda y el crédito del movimiento original"},422)
        assert b["idOrigen"] == 101 and b["version"] == mov["version"]
        mov["version"] += 1
        mov["partes"] = b["partes"] or [{"subcuenta":"por-identificar","deuda":"0","credito":"100.0001"}]
        mov["manual"] = bool(b["partes"])
        historia.insert(0,{"version":mov["version"],"reparto":json.dumps(b["partes"]),"motivo":b["motivo"],"usuario":"fixture","fecha":"2026-10-25"})
        return reply({"version":mov["version"]})
    if p == "/api/arca/cuenta":
        sub=parse_qs(u.query).get("subcuenta",[None])[0]
        resumen=[]
        from decimal import Decimal as D
        for clave,nombre in catalogo.items():
            partes=[x for x in mov["partes"] if x["subcuenta"]==clave]
            total=sum((D(x["credito"])-D(x["deuda"]) for x in partes),D(0))
            resumen.append({"clave":clave,"nombre":nombre,"deuda":"0","credito":str(total),"saldo":str(total),"cantidad":len(partes)})
        visible=not sub or any(x["subcuenta"]==sub for x in mov["partes"])
        return reply({"resumen":resumen,"saldoTotal":"100.0001","apertura":"0", "saldoSeleccion": "100.0001" if visible else "0",
                      "items":[mov] if visible else [],"total":int(visible),"page":1,"pageSize":50})
    reply({"items":[]})


with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    page=browser.new_page(viewport={"width":1440,"height":1000})
    page.on("pageerror",lambda e: errores.append(str(e)))
    page.route("**/api/**",route_handler)
    page.goto(BASE+"/finanzas/cuentas-corrientes?idContacto=119&razonSocial=ARCA&tipoContacto=Organismo")
    expect(page.get_by_role("heading",name="Subcuentas de ARCA")).to_be_visible()
    page.get_by_role("button",name=re.compile("Retenciones de Ganancias efectuadas")).click()
    expect(page.get_by_text("Sin movimientos para este período y subcuenta.")).to_be_visible()
    page.get_by_role("button",name=re.compile("Toda ARCA")).click()
    page.get_by_role("button",name="Clasificar / repartir",exact=True).click()
    dialog=page.get_by_role("dialog")
    dialog.get_by_label("Subcuenta 1",exact=True).select_option("iva")
    dialog.get_by_label("Créditos 1",exact=True).fill("99")
    dialog.get_by_label("Motivo de clasificación").fill("Prueba con API simulada")
    dialog.get_by_role("button",name="Guardar clasificación",exact=True).click()
    expect(dialog.get_by_role("alert")).to_contain_text("sumar exactamente")
    dialog.get_by_label("Créditos 1",exact=True).fill("60.0001")
    dialog.get_by_role("button",name="+ Agregar parte",exact=True).click()
    dialog.get_by_label("Subcuenta 2",exact=True).select_option("ganancias")
    dialog.get_by_label("Créditos 2",exact=True).fill("40")
    dialog.get_by_role("button",name="Guardar clasificación",exact=True).click()
    expect(dialog).not_to_be_visible()
    expect(page.get_by_text("Clasificación registrada")).to_be_visible()
    page.screenshot(path=str(out/"subcuentas-ui.png"),full_page=True)
    page.get_by_role("button",name="Clasificar / repartir",exact=True).click()
    dialog=page.get_by_role("dialog")
    dialog.get_by_text("Historial de clasificación",exact=True).click()
    expect(dialog.get_by_text("Versión 1",exact=True)).to_be_visible()
    dialog.get_by_label("Motivo de clasificación").fill("Volver al original, prueba simulada")
    dialog.get_by_role("button",name="Volver al criterio automático",exact=True).click()
    expect(dialog).not_to_be_visible()
    assert mov["version"] == 2 and len(historia)==2 and not mov["manual"]
    rol="Lectura"
    page.reload()
    expect(page.get_by_role("heading",name="Subcuentas de ARCA")).to_be_visible()
    expect(page.get_by_role("button",name="Clasificar / repartir",exact=True)).to_have_count(0)
    assert not errores, errores
    browser.close()
print("ARCA UI: resumen, selección vacía, validación, reparto, historial, reversión y rol Lectura: OK; sin escrituras WC")
