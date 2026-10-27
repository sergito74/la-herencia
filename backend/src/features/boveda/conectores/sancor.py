"""Conector de Sancor Seguros, Autogestión (042, T045).

Ingresa por el login de Grupo Sancor (usuario → Continuar → clave → Continuar)
y usa la API de la propia página: pólizas vigentes (`MyPolicies/PostCardsList`),
movimientos de cada póliza (`PolicyPayment/GetCertificateMovementsDetails`) y
descarga de la factura (`DocumentationDownload/PostDownloadDocument`, devuelve
el PDF en base64). No usa "Pagar ahora", débito automático, póliza electrónica,
denuncias ni adjuntar documentación. Relevamiento:
specs/042-boveda-portales/relevamientos/sancor.md.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DocumentoPortal, EstadoCuentaPortal, MovimientoCuenta, PortalCambio,
    RequiereIntervencion, registrar,
)
from src.features.descarga_peajes import lectores

INGRESO = "https://www.sancorseguros.com.ar/autogestion/ingresar"
APP = "https://autogestion.sancorseguros.com.ar"
ID_CONTACTO = 171
_NUMERO = re.compile(r"FACTURA N\S*\s*:\s*(\d{5})\s*-\s*(\d{8})")


@dataclass
class _Sesion:
    browser: object
    pagina: object = None


def _fecha(t: str | None) -> date | None:
    try:
        return datetime.fromisoformat(t[:19]).date() if t else None
    except ValueError:
        return None


def _inicio_ejercicio(d: date) -> date:
    return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


class ConectorSancor:
    tiene_estado_cuenta = True
    tiene_carga_compras = False
    mapeo_proveedores: dict = {}

    def __init__(self, codigo: str = "sancor", nombre: str = "Sancor Seguros"):
        self.codigo = codigo
        self.nombre = nombre

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        try:
            p = browser.new_context().new_page()
            p.goto(INGRESO, wait_until="networkidle", timeout=90000)
            p.fill("input[name=username]", credencial.usuario or "")
            p.locator("button[type=submit][name=action]").first.click()
            p.wait_for_load_state("networkidle", timeout=90000)
            if p.locator("input[name=code], iframe[src*=captcha]").count():
                raise RequiereIntervencion("Sancor pidió una verificación adicional")
            p.fill("input[name=password]", credencial.clave.valor() if credencial.clave else "")
            p.locator("button[type=submit][name=action]").first.click()
            p.wait_for_load_state("load", timeout=90000)
            for _ in range(30):
                if p.url.startswith(APP):
                    # La pantalla de documentación deja lista la sesión de pólizas que usa la API.
                    with p.expect_response(lambda r: "PostCardsList" in r.url, timeout=90000):
                        p.goto(APP + "/DocumentationDownload", wait_until="load", timeout=90000)
                    return _Sesion(browser=browser, pagina=p)
                if p.locator("input[name=password]").count() and "incorrect" in p.inner_text("body").lower():
                    raise CredencialesRechazadas("Sancor rechazó usuario o contraseña")
                p.wait_for_timeout(1000)
            raise PortalCambio("No se pudo completar el ingreso a Sancor")
        except Exception:
            browser.close()
            raise

    def _api(self, sesion: _Sesion, metodo: str, ruta: str, cuerpo: dict | None = None) -> dict:
        r = sesion.pagina.evaluate(
            """async ([metodo, url, cuerpo]) => {
                const r = await fetch(url, {method: metodo, credentials: 'include',
                    headers: {'Content-Type': 'application/json; charset=UTF-8', 'Accept': '*/*',
                        'X-Requested-With': 'XMLHttpRequest', 'Authorization': 'Bearer'},
                    body: cuerpo === null ? undefined : JSON.stringify(cuerpo)});
                return {status: r.status, texto: await r.text()};
            }""", [metodo, APP + ruta, cuerpo])
        if r["status"] != 200:
            raise PortalCambio(f"Sancor respondió {r['status']}")
        import json

        return json.loads(r["texto"]).get("data") or {}

    def _polizas(self, sesion: _Sesion) -> list[dict]:
        data = self._api(sesion, "POST", "/api/v1/MyPolicies/PostCardsList",
                         {"policy": {"client": {"bupId": 0}, "isVigent": True}})
        return data.get("policies") or []

    def _movimientos(self, sesion: _Sesion, pol: dict) -> list[dict]:
        data = self._api(sesion, "GET", f"/api/v1/PolicyPayment/GetCertificateMovementsDetails?certificateId={pol['certificateId']}")
        return data.get("certificateMovements") or []

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        """Una factura por fecha de emisión: el PDF trae juntas las facturas de todas las pólizas del mes."""
        desde = _inicio_ejercicio(date.today())
        docs: dict[str, DocumentoPortal] = {}
        sesion.movimientos = {}
        for pol in self._polizas(sesion):
            cert = pol.get("policyCertificate") or {}
            ref, oficial = str(pol.get("referenceNumber") or cert.get("referenceNumber")), str(cert.get("officialNumber") or "")
            ramo = pol.get("branchName") or ""
            movs = self._movimientos(sesion, pol)
            sesion.movimientos[ref] = (ramo, movs)
            for m in movs:
                impreso = m.get("printDate")
                fecha = _fecha(impreso)
                if not fecha or fecha < desde or impreso[:10] in docs:
                    continue
                cuerpo = {"did_gss": "INVOICE", "core_id": pol.get("coreId") or 1,
                          "policy": {"numberRef": ref, "numberOf": oficial, "branchNumber": int(pol.get("branchCode") or 0),
                                     "date": impreso, "receipt": 0, "certificateNumber": str(pol.get("certificateNumber") or 0)}}
                doc = DocumentoPortal(clave=f"sancor:{impreso[:10]}", fecha=fecha, tipo="factura", proveedor="SancorSeguros",
                                      bajar=lambda: b"", moneda="ARS", detalle=f"Facturas de pólizas {fecha:%m/%Y}",
                                      id_contacto=ID_CONTACTO)
                doc.bajar = self._bajador(sesion, cuerpo, doc)
                docs[impreso[:10]] = doc
        disponibles = []
        for doc in docs.values():
            # Las facturas viejas figuran en los movimientos pero el portal no tiene su PDF: se descartan
            # al listar (se bajan una sola vez acá y se guardan para no pedirlas de nuevo).
            try:
                pdf = doc.bajar()
            except PortalCambio:
                continue
            doc.bajar = lambda pdf=pdf: pdf
            disponibles.append(doc)
        return disponibles

    def _bajador(self, sesion: _Sesion, cuerpo: dict, doc: DocumentoPortal):
        def bajar() -> bytes:
            data = self._api(sesion, "POST", "/api/v1/DocumentationDownload/PostDownloadDocument", cuerpo)
            if not data.get("stream"):
                raise PortalCambio("Sancor no devolvió la factura")
            pdf = base64.b64decode(data["stream"])
            # Número de la primera factura del PDF, para reconocer la compra ya cargada.
            texto = lectores.texto_pdf(pdf)
            m = _NUMERO.search(texto)
            if m:
                doc.numero = f"{m.group(1)}-{m.group(2)}"
                f = re.search(r"(\d{2}/\d{2}/\d{4})", texto[m.end():])
                if f:  # fecha de emisión impresa (el portal informa la de impresión del lote)
                    doc.fecha = datetime.strptime(f.group(1), "%d/%m/%Y").date()
            return pdf
        return bajar

    def estado_cuenta(self, sesion: _Sesion) -> list[EstadoCuentaPortal]:
        """Recibos pendientes de pago de cada póliza (lo que el portal muestra en "Pólizas a pagar")."""
        if not getattr(sesion, "movimientos", None):
            sesion.movimientos = {str(p.get("referenceNumber")): (p.get("branchName") or "", self._movimientos(sesion, p))
                                  for p in self._polizas(sesion)}
        hoy = date.today()
        movimientos, total = [], Decimal(0)
        for ref, (ramo, movs) in sesion.movimientos.items():
            for m in movs:
                prima = m.get("premium") or {}
                if prima.get("statusName") != "Pendiente" or not prima.get("amount"):
                    continue
                importe = Decimal(str(prima["amount"])).quantize(Decimal("0.01"))
                total += importe
                vence = _fecha(prima.get("expirationPayDate"))
                movimientos.append(MovimientoCuenta(
                    fecha=vence, comprobante=str(prima.get("number") or ""),
                    detalle=f"{ramo} póliza {ref}: recibo pendiente" + (f", vence {vence:%d/%m/%Y}" if vence else ""),
                    debe=None, haber=importe, saldo=None))
        return [EstadoCuentaPortal(fecha_corte=hoy, moneda="ARS", saldo=total, completa=False, movimientos=movimientos)]

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes):
        return None

    def cerrar(self, sesion: _Sesion) -> None:
        sesion.browser.close()


registrar(ConectorSancor())
registrar(ConectorSancor("sancor_giamigli", "Sancor Seguros Giamigli"))
