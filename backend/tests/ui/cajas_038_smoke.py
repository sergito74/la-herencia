"""Recorrido UI 038 con TODA API interceptada. No consulta ni escribe WC.

Ejecutar con frontend local en puerto 3100; usa Edge headless ya instalado.
"""

from pathlib import Path
from time import perf_counter
import json
import os
import re
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, expect

URL = os.environ.get("CAJAS_UI_URL", "http://127.0.0.1:3100")
OUT = Path(__file__).resolve().parents[3] / "backups" / "cajas-038-ui"


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    state = {
        "rol": "Administrador",
        "op": None,
        "arqueos": [],
        "requests": [],
        "unexpected": [],
        "errorPreview": False,
        "particular": False,
        "previews": [],
    }
    errors = []
    socio_movs = [{"idMovimiento": 10, "tipo": "AsignacionGasto", "importe":100, "importeUSD":.05,
        "importeKgCarne":.025,"fecha":"2026-10-23","origen":"Manual","idOrigen":None,
        "proveedorOrigen":None,"numeroDocumentoOrigen":None,"medio":"Efectivo","motivo":"Asiento previo",
        "usuario":"prueba","anulada":False,"motivoAnulacion":None,"huerfano":False,"editable":True,"idOperacionCaja":None}]

    doc = {
        "tipoDocumento": "CompraDeuda",
        "idDocumento": 10,
        "fecha": "2026-10-20",
        "numeroDocumento": "FC 0001-00000100",
        "importeTotal": 100,
        "aplicado": 0,
        "saldoPendiente": 100,
    }
    mov = {
        "idMovimiento": 1,
        "fecha": "2026-10-22",
        "concepto": "Movimiento de prueba",
        "detalle": None,
        "importe": -100,
        "cuenta": "A",
        "formaPago": None,
        "numeroDocumento": None,
        "idContactoRelacionado": 17,
        "idOperacion": None,
        "anulada": False,
        "saldoCorridoDecimal": "900.00",
    }
    lote = {
        "idLote": 1,
        "estado": "Preview",
        "libro": "CajasGiamigli",
        "fechaCorte": "2026-10-22",
        "filas": [
            {
                "idFila": 1,
                "hoja": "Caja Efectivo Pesos",
                "fila": 2,
                "estado": "Ambigua",
                "motivo": "Coincidencia manual",
                "datos": {
                    "caja": "giamigli-sa",
                    "fecha": "2026-10-22",
                    "importe": "-100.00",
                    "concepto": "Pago",
                    "cuenta": "A",
                },
                "idMovimiento": None,
                "idOperacion": None,
                "candidatas": [
                    {
                        "idMovimiento": 1,
                        "idOperacion": None,
                        "concepto": "Pago ya cargado",
                        "anulada": False,
                    }
                ],
            }
        ],
        "comparacion": {
            "giamigli-sa": {
                "saldoSistema": "900.00",
                "saldoPlanilla": "900.00",
                "diferencia": "0.00",
                "pendientes": 1,
                "cobertura": "Libro al corte",
                "soloSistema": [1],
                "ambiguas": [1],
                "modificadas": [],
                "excluidas": [],
            }
        },
    }

    def handler(route):
        req = route.request
        path = urlparse(req.url).path
        if "/api/" not in path:
            if req.url.startswith(URL):
                route.continue_()
            else:
                route.abort()
            return
        state["requests"].append((req.method, path))
        data = (
            req.post_data_json
            if req.method in ("POST", "PUT")
            and "application/json" in req.headers.get("content-type", "")
            else None
        )
        status = 200
        if path == "/api/sesion/latido":
            body = {"ok": True}
        elif path == "/api/descarga-peajes/resumen":
            body = {}
        elif path == "/api/auth/me":
            body = {
                "idUsuario": 1,
                "usuario": "prueba",
                "nombre": "Prueba simulada",
                "rol": state["rol"],
            }
        elif path == "/api/contactos":
            body = {
                "items": [
                    {
                        "idContacto": 17,
                        "razonSocial": "Proveedor de prueba",
                        "tipoContacto": "Proveedor",
                        "cuit": None,
                    }
                ],
                "total": 1,
                "page": 1,
                "pageSize": 20,
            }
        elif path == "/api/cuentas-socios/2/movimientos":
            body = {"idSocio":2,"nombre":"Lucy","saldo":100,"saldoUSD":.05,"saldoKgCarne":.025,"actualizada":None,"movimientos":socio_movs}
        elif path == "/api/cuentas-socios/2/asientos":
            m = {**socio_movs[0],"idMovimiento":11,"motivo":data["motivo"],"importe":data["importe"]}
            socio_movs.append(m);body=m
        elif path == "/api/cuentas-socios/movimientos/11" and req.method == "PUT":
            socio_movs[1]["anulada"]=True
            m={**socio_movs[1],"idMovimiento":12,"anulada":False,"motivo":data["motivo"]}
            socio_movs.append(m);body=m
        elif path == "/api/cuentas-socios/movimientos/12/anular":
            socio_movs[2]["anulada"]=True;body={"ok":True}
        elif path == "/api/cuentas-socios":
            body = {
                "socios": [
                    {"idSocio": 1, "nombre": "Sergio", "saldo": 0},
                    {"idSocio": 2, "nombre": "Lucy", "saldo": 0},
                    {"idSocio": 3, "nombre": "Condominio LSC", "saldo": 0},
                ]
            }
        elif path == "/api/cajas-efectivo/particulares/asientos":
            body = {"items": []}
        elif path == "/api/compras/filtros":
            body = {
                "rubros": [{"idRubro": 1, "rubro": "Mantenimiento"}],
                "centrosCosto": [{"idCentroCosto": 1, "centroCosto": "Campo"}],
                "destinos": [],
                "campañas": [],
                "unidadesMedida": [],
            }
        elif path == "/api/cuentas-socios/compras-particulares-candidatas":
            body = {"compras": []}
        elif path == "/api/aplicaciones-pago/documentos-pendientes":
            sale = "tipo=venta" in req.url
            body = [
                {
                    **doc,
                    "tipoDocumento": "VentaHacienda" if sale else "CompraDeuda",
                    "numeroDocumento": "Venta 001" if sale else doc["numeroDocumento"],
                    "esParticular": state["particular"], "importePersonal": 100 if state["particular"] else None,
                }
            ]

        elif path == "/api/remuneraciones":
            body = {"items": [], "total": 0, "page": 1, "pageSize": 200}
        elif path.startswith("/api/tesoreria/") and path.endswith("/movimientos"):
            body = {
                "items": [
                    {
                        "idMovimientoBNA": 7,
                        "fechaHora": "2026-10-22",
                        "concepto": "Extracción de prueba",
                        "importe": -100,
                        "estadoConciliacion": "sin_conciliar",
                    }
                ],
                "total": 1,
                "page": 1,
                "pageSize": 200,
            }

        elif path.endswith("/saldo"):
            body = {"caja": "giamigli-sa", "saldo": 900, "saldoDecimal": "900.00"}
        elif path.endswith("/movimientos"):
            body = {
                "items": [mov],
                "total": 1,
                "page": 1,
                "pageSize": 50,
                "saldoAnteriorDecimal": "0.00",
                "subtotalFiltradoDecimal": "-100.00",
            }
        elif path == "/api/cajas-efectivo/operaciones/previsualizar":
            state["previews"].append(data)
            if state["errorPreview"]:
                body, status = {"detail": "Cambió el contexto. Volvé a previsualizar."}, 409
            else:
                body = {
                    "previewVersion": "0" * 64,
                    "advertencias": [],
                    "contexto": {},
                    "efectosPrevistos": [
                        {"caja": data["caja"], "importe": "100.00" if data["tipo"] in ("aporte", "ingreso_dolares", "cobro", "extraccion_banco") else "-100.00", "saldoResultante": "1100.00" if data["tipo"] in ("aporte", "ingreso_dolares", "cobro", "extraccion_banco") else "900.00"}
                    ],
                }
        elif path == "/api/cajas-efectivo/operaciones":
            state["op"] = {
                "idOperacion": 1,
                "estado": "Vigente",
                "version": 0,
                "operacion": data["operacion"],
                "usuario": "prueba",
                "fechaCarga": "2026-10-22T17:00:00Z",
                "motivoAnulacion": None,
                "usuarioAnulacion": None,
                "fechaAnulacion": None,
                "movimientos": [],
                "efectos": [{"tipo": "PagoEfectivo", "idRegistro": 1, "propio": True}],
            }
            mov["idOperacion"] = 1
            body, status = state["op"], 201
        elif path.endswith("/operaciones/1"):
            body = state["op"]
        elif path.endswith("/operaciones/1/anular"):
            state["op"].update(
                estado="Anulada",
                motivoAnulacion=data["motivo"],
                usuarioAnulacion="prueba",
                fechaAnulacion="2026-10-22T17:10:00Z",
            )
            mov["anulada"] = True
            body = state["op"]
        elif path.endswith("/arqueos") and req.method == "GET":
            body = {
                "items": state["arqueos"],
                "total": len(state["arqueos"]),
                "page": 1,
                "pageSize": 20,
            }
        elif path.endswith("/arqueos") and req.method == "POST":
            a = {
                "idArqueo": 1,
                "caja": "giamigli-sa",
                "fechaCorte": data["fechaCorte"],
                "secuenciaCorte": 1,
                "version": 0,
                "estado": "Borrador",
                "saldoSistema": "750.90",
                "totalContado": "1000.00",
                "diferencia": "249.10",
                "previewVersion": "0" * 64,
                "saldoRecalculadoDecimal": "750.90",
                "diferenciaVigenteDecimal": "249.10",
                "idOperacionAjuste": None,
                "idArqueoAnterior": None,
                "usuario": "prueba",
                "usuarioConfirmacion": None,
                "denominaciones": data["denominaciones"],
                "advertencias": [],
            }
            state["arqueos"] = [a]
            body, status = a, 201
        elif "/arqueos/1/confirmar" in path:
            state["arqueos"][0].update(
                estado="Confirmado", version=1, diferenciaVigenteDecimal="0.00"
            )
            body = state["arqueos"][0]
        elif path.endswith("/importaciones/previsualizar"):
            body = lote
        elif path.endswith("/importaciones/1/confirmar"):
            lote["estado"] = "Confirmado"
            lote["filas"][0].update(estado="Vinculada", idMovimiento=1)
            body = lote
        else:
            state["unexpected"].append((req.method, path))
            body, status = {"detail": "API simulada sin fixture"}, 404
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        context.route("**/*", handler)
        page = context.new_page()
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(
            f"{URL}/finanzas/cajas-efectivo/giamigli-sa", wait_until="networkidle", timeout=60000
        )
        expect(page.get_by_role("heading", name="Caja de efectivo — Giamigli SA")).to_be_visible()
        expect(page.get_by_role("navigation", name="Cajas y cuentas de socios")).to_have_css("display", "flex")
        start = perf_counter()
        page.get_by_role("button", name="+ Nuevo movimiento", exact=True).click()
        page.get_by_label("Concepto", exact=True).fill("Pago de prueba visual")
        page.locator("form").get_by_placeholder("Buscar contacto…").fill("Proveedor")
        page.get_by_role("button", name="Proveedor de prueba").click()
        page.locator("label").filter(has_text="FC 0001-00000100").click()
        page.get_by_role("button", name="Revisar efectos antes de guardar", exact=True).click()
        expect(page.get_by_role("heading", name="Efectos antes de guardar")).to_be_visible()
        page.screenshot(path=str(OUT / "pago-preview.png"), full_page=True)
        page.get_by_role("button", name="Confirmar operación", exact=True).click()
        expect(page.get_by_role("heading", name="Operación 1", exact=True)).to_be_visible()
        elapsed = perf_counter() - start
        assert elapsed < 60, elapsed
        page.get_by_label("Motivo de anulación").fill("Corrección de prueba")
        page.get_by_role("button", name="Confirmar anulación").click()
        expect(page.get_by_text("Anuló prueba", exact=False)).to_be_visible()
        page.get_by_role("button",name="Corregir: cargar de nuevo con estos datos",exact=True).click()
        expect(page.get_by_label("Concepto",exact=True)).to_have_value("Pago de prueba visual")
        page.get_by_role("button",name="Revisar efectos antes de guardar",exact=True).click()
        expect(page.get_by_role("heading",name="Efectos antes de guardar")).to_be_visible()
        assert state["previews"][-1]["aplicaciones"][0]["idDocumento"]==10
        page.get_by_role("button", name="Cerrar detalle").click()
        page.get_by_role("tab", name="Arqueos", exact=True).click()
        page.locator("input[inputmode=numeric]").fill("1")
        page.get_by_role("button", name="Guardar borrador y comparar").click()
        expect(page.get_by_text("diferencia:", exact=False).last).to_be_visible()
        page.get_by_label(
            "Confirmo el recuento y, si corresponde, su diferencia de arqueo."
        ).check()
        page.get_by_role("button", name="Confirmar arqueo", exact=True).click()
        expect(page.get_by_text("Confirmado", exact=False).first).to_be_visible()
        page.screenshot(path=str(OUT / "arqueo.png"), full_page=True)
        page.get_by_role("tab", name="Comparar con la planilla").click()
        page.locator("input[type=file]").set_input_files(
            {
                "name": "caja.xlsx",
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "buffer": b"fixture interceptada",
            }
        )
        page.get_by_role("button", name="Previsualizar archivo").click()
        expect(page.get_by_text("Coincidencia manual", exact=False)).to_be_visible()
        page.locator("tbody select").first.select_option("vincular")
        page.locator("tbody select").nth(1).select_option("1")
        page.get_by_role("button", name="Confirmar decisiones del lote").click()
        expect(page.get_by_text("Vinculada al movimiento 1")).to_be_visible()
        page.screenshot(path=str(OUT / "importacion.png"), full_page=True)
        page.get_by_role("button", name="+ Nuevo movimiento", exact=True).click()
        page.get_by_label("Concepto", exact=True).fill("Conservar borrador ante error")
        page.locator("form").get_by_placeholder("Buscar contacto…").fill("Proveedor")
        page.get_by_role("button", name="Proveedor de prueba").click()
        page.locator("label").filter(has_text="FC 0001-00000100").click()
        state["errorPreview"] = True
        page.get_by_role("button", name="Revisar efectos antes de guardar", exact=True).click()
        expect(page.get_by_role("alert").filter(has_text="Cambió el contexto")).to_be_visible()
        expect(page.get_by_label("Concepto", exact=True)).to_have_value(
            "Conservar borrador ante error"
        )
        state["errorPreview"] = False
        page.get_by_label(re.compile("^Operación")).select_option("aporte")
        page.locator("form").get_by_label(re.compile("^Socio")).select_option("1")
        page.get_by_role("button", name="Revisar efectos antes de guardar", exact=True).click()
        expect(page.get_by_role("heading", name="Efectos antes de guardar")).to_be_visible()
        assert state["previews"][-1]["idSocio"] == 1 and "idContacto" not in state["previews"][-1]
        page.get_by_label(re.compile("^Operación")).select_option("retiro_ganancias")
        page.get_by_role("button", name="Revisar efectos antes de guardar", exact=True).click()
        expect(page.get_by_role("heading", name="Efectos antes de guardar")).to_be_visible()
        assert state["previews"][-1]["tipo"] == "retiro_ganancias"
        page.get_by_label(re.compile("^Operación")).select_option("traspaso_cajas")
        page.get_by_label("Caja de destino").select_option("campo-chica")
        page.get_by_role("button", name="Revisar efectos antes de guardar", exact=True).click()
        expect(page.get_by_role("heading", name="Efectos antes de guardar")).to_be_visible()
        assert state["previews"][-1]["cajaDestino"] == "campo-chica"
        page.get_by_label(re.compile("^Operación")).select_option("extraccion_banco")
        page.get_by_label("Movimiento del extracto (fecha elegida)").select_option("7")
        page.get_by_role("button", name="Revisar efectos antes de guardar", exact=True).click()
        expect(page.get_by_role("heading", name="Efectos antes de guardar")).to_be_visible()
        assert state["previews"][-1]["banco"]["idMovimiento"] == 7
        page.get_by_label(re.compile("^Operación")).select_option("cobro")
        page.locator("label").filter(has_text="Venta 001").click()
        page.get_by_role("button", name="Revisar efectos antes de guardar", exact=True).click()
        expect(page.get_by_role("heading", name="Efectos antes de guardar")).to_be_visible()
        assert state["previews"][-1]["aplicaciones"][0]["tipoDocumento"] == "VentaHacienda"
        page.get_by_label(re.compile("^Operación")).select_option("gasto_sin_comprobante")
        page.get_by_label(re.compile("^Rubro")).select_option("1")
        page.get_by_label(re.compile("^Centro de costos")).select_option("1")
        page.get_by_label("Importe del reparto").fill("100")
        page.get_by_label("Concepto", exact=True).click()
        page.get_by_role("button", name="Revisar efectos antes de guardar", exact=True).click()
        expect(page.get_by_role("heading", name="Efectos antes de guardar")).to_be_visible()
        assert state["previews"][-1]["repartos"][0]["importePesos"] == "100.00"
        state["particular"] = True
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="+ Nuevo movimiento", exact=True).click()
        page.get_by_label("Concepto", exact=True).fill("Compra particular de prueba")
        page.locator("form").get_by_placeholder("Buscar contacto…").fill("Proveedor")
        page.get_by_role("button", name="Proveedor de prueba").click()
        page.get_by_label("Compra particular de un socio", exact=True).check()
        page.locator("select").filter(has=page.locator('option[value="10"]')).select_option("10")
        page.locator("form").get_by_label(re.compile("^Socio")).select_option("1")
        page.get_by_role("button", name="Revisar efectos antes de guardar", exact=True).click()
        expect(page.get_by_role("heading", name="Efectos antes de guardar")).to_be_visible()
        assert state["previews"][-1]["compraParticular"]["idCompra"] == 10
        assert state["previews"][-1]["compraParticular"]["idSocio"] == 1
        page.screenshot(path=str(OUT / "particular-preview.png"), full_page=True)
        # Corrección de caja conserva el formulario en el historial anulado.
        page.get_by_role("button",name="Cerrar",exact=True).click()
        page.goto(f"{URL}/finanzas/cajas",wait_until="networkidle")
        expect(page.get_by_role("heading",name="Caja Giamigli US$",exact=True)).to_be_visible()
        page.screenshot(path=str(OUT / "resumen-cajas-socios.png"),full_page=True)
        page.goto(f"{URL}/finanzas/cajas-efectivo/giamigli-dolares",wait_until="networkidle")
        page.get_by_role("button",name="+ Nuevo movimiento",exact=True).click()
        expect(page.locator("form").get_by_label(re.compile("^Operación"))).to_have_value("ingreso_dolares")
        assert page.locator("form option[value=pago]").count()==0
        page.get_by_label("Concepto",exact=True).fill("Ingreso billetes USD")
        page.get_by_label("Importe",exact=True).fill("100")
        page.get_by_label("Importe",exact=True).press("Tab")
        page.get_by_role("button",name="Revisar efectos antes de guardar",exact=True).click()
        expect(page.get_by_role("heading",name="Efectos antes de guardar")).to_be_visible()
        assert state["previews"][-1]["caja"]=="giamigli-dolares"
        page.screenshot(path=str(OUT / "dolares-preview.png"),full_page=True)
        page.get_by_role("button",name="Cerrar",exact=True).click()
        page.goto(f"{URL}/finanzas/cuentas-socios/2",wait_until="networkidle")
        page.get_by_role("button",name="+ Nuevo asiento",exact=True).click()
        page.get_by_label(re.compile("^Importe en pesos")).fill("100")
        page.get_by_label(re.compile("^Importe en pesos")).press("Tab")
        page.get_by_label("Concepto",exact=True).fill("Asiento nuevo UI")
        page.get_by_role("button",name="Registrar asiento",exact=True).click()
        expect(page.get_by_text("Asiento nuevo UI",exact=True)).to_be_visible()
        page.get_by_role("row").filter(has_text="Asiento nuevo UI").get_by_role("button",name="Editar").click()
        page.get_by_label("Concepto",exact=True).fill("Asiento corregido UI")
        page.get_by_role("button",name="Guardar corrección",exact=True).click()
        expect(page.get_by_text("Asiento corregido UI",exact=True)).to_be_visible()
        page.once("dialog",lambda d:d.accept("Correccion UI"))
        page.get_by_role("row").filter(has_text="Asiento corregido UI").get_by_role("button",name="Anular").click()
        expect(page.get_by_text("Asiento corregido UI",exact=True)).to_have_count(0)
        page.get_by_role("button",name="Aporte / retiro en efectivo…",exact=True).click()
        page.locator("select").filter(has=page.locator('option[value="giamigli-dolares"]')).select_option("giamigli-dolares")
        page.get_by_label("Concepto",exact=True).fill("Aporte Lucy USD")
        page.get_by_label("Importe",exact=True).fill("100")
        page.get_by_label("Importe",exact=True).press("Tab")
        page.get_by_role("button",name="Revisar efectos antes de guardar",exact=True).click()
        expect(page.get_by_role("heading",name="Efectos antes de guardar")).to_be_visible()
        assert state["previews"][-1]["idSocio"]==2 and state["previews"][-1]["caja"]=="giamigli-dolares"
        page.screenshot(path=str(OUT / "socio-aporte-dolares.png"),full_page=True)
        page.goto(f"{URL}/finanzas/cajas-efectivo/giamigli-sa",wait_until="networkidle")
        state["rol"] = "Lectura"
        page.reload(wait_until="networkidle")
        expect(page.get_by_role("button", name="+ Nuevo movimiento", exact=True)).to_have_count(0)
        expect(page.get_by_role("button", name="Previsualizar archivo")).to_have_count(0)
        expect(page.get_by_role("tab", name="Arqueos", exact=True)).to_be_visible()
        page.screenshot(path=str(OUT / "solo-lectura.png"), full_page=True)
        page.goto(f"{URL}/finanzas/cuentas-socios/2",wait_until="networkidle")
        expect(page.get_by_role("button",name="+ Nuevo asiento",exact=True)).to_have_count(0)
        expect(page.get_by_role("button",name="Editar",exact=True)).to_have_count(0)
        expect(page.get_by_role("button",name="Anular",exact=True)).to_have_count(0)
        page.screenshot(path=str(OUT / "socio-solo-lectura.png"),full_page=True)
        assert not errors, errors
        assert not state["unexpected"], state["unexpected"]
        context.close()
        browser.close()
    result = {
        "estado": "PASS",
        "pagoSegundos": round(elapsed, 2),
        "apisInterceptadas": len(state["requests"]),
        "erroresJS": errors,
        "apisSinFixture": state["unexpected"],
        "WC": "sin acceso",
        "escenarios": [
            "pago",
            "anulacion",
            "arqueo",
            "vinculo_importacion",
            "error_con_borrador",
            "aporte",
            "ganancias",
            "traspaso",
            "extraccion_banco",
            "cobro",
            "gasto_sin_comprobante",
                "compra_particular",
            "rol_lectura", "resumen_cajas_socios", "dolares", "asiento_socio", "editar_socio", "anular_socio", "aporte_socio_usd", "corregir_caja_con_aplicaciones",
        ],
    }
    (OUT / "resultado.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    run()
