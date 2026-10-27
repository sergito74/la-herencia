"""Conector de la Cooperativa Eléctrica de Bolívar, Oficina Virtual (CEBOL).

Ingresa con usuario y clave en ofv2.cebol.com.ar y usa la API de la propia página con el token del ingreso:
suministros (`nservicioasociado/index`), comprobantes del suministro (`getDeuda`, impagos y pagos), saldo
(`getDeudaResumida`) y el PDF de cada factura (`getPdfDeuda`). No usa "Pagar", medios de pago, alta o baja de
suministros, perfil ni notificaciones. Relevamiento: specs/042-boveda-portales/relevamientos/cebol.md.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import quote

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DocumentoPortal, EstadoCuentaPortal, MovimientoCuenta, PortalCambio,
    registrar,
)

OFV = "https://ofv2.cebol.com.ar"
ID_CONTACTO = 23
_COMPROBANTE = re.compile(r"^FC([ABC]) (\d{4})-0*(\d{1,8})$")
_EMISION = re.compile(r"(?:FECHA DE EMISI[OÓ]N|EMISI[OÓ]N|Fecha Emisi[oó]n)\s*:?\s*(\d{2})/(\d{2})/(\d{4})", re.I)


@dataclass
class _Sesion:
    browser: object
    api: object = None
    token: str = ""


def _fecha(t: str | None) -> date | None:
    try:
        return datetime.fromisoformat(t[:19]).date() if t else None
    except ValueError:
        return None


def _fecha_emision(pdf: bytes) -> date | None:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf)) as d:
        m = _EMISION.search(d.pages[0].extract_text() or "")
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


class ConectorCebol:
    codigo = "cebol"
    nombre = "Cooperativa Eléctrica de Bolívar"
    tiene_estado_cuenta = True
    tiene_carga_compras = False
    mapeo_proveedores: dict = {}

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        try:
            p = browser.new_context().new_page()
            p.goto(OFV, wait_until="networkidle", timeout=90000)
            p.fill("#login-username", credencial.usuario or "")
            p.fill("#login-password", credencial.clave.valor() if credencial.clave else "")
            with p.expect_response(lambda r: r.url.endswith("/api/auth/login"), timeout=60000) as resp:
                p.click("button[type=submit]")
            token = (resp.value.json() or {}).get("token") if resp.value.ok else None
            if not token:
                raise CredencialesRechazadas("La Cooperativa Eléctrica rechazó usuario o contraseña")
            return _Sesion(browser=browser, api=p.context.request, token=token)
        except Exception:
            browser.close()
            raise

    def _get(self, sesion: _Sesion, ruta: str):
        r = sesion.api.get(f"{OFV}/api/{ruta}", headers={"Authorization": f"Bearer {sesion.token}"}, timeout=90000)
        if not r.ok:
            raise PortalCambio(f"La oficina virtual no respondió ({r.status})")
        return r

    def _suministros(self, sesion: _Sesion) -> list[dict]:
        return self._get(sesion, "nservicioasociado/index?limit=100").json().get("records") or []

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        docs = []
        for s in self._suministros(sesion):
            socio, conexion = s["n_socio"], s["n_conexion"]
            for c in self._get(sesion, f"nservicioasociado/getDeuda/{socio}&{conexion}").json() or []:
                m = _COMPROBANTE.match(c.get("comprobanteFormat") or "")
                if not m:
                    continue
                ruta = (f"nservicioasociado/getPdfDeuda/{quote(c['comprobanteFormat'])}&{c['sistema']}"
                        f"?periodo={c['periodo']}&nroSocio={socio}&conexion={conexion}&interno=0")
                doc = DocumentoPortal(
                    clave=f"cebol:{c['comprobanteFormat']}", fecha=_fecha(c.get("fechaVto")), tipo="factura",
                    proveedor="CooperativaElectrica", bajar=lambda: b"", numero=f"{m.group(2)}-{int(m.group(3)):08d}",
                    total=Decimal(str(c["importe"])).quantize(Decimal("0.01")), moneda="ARS",
                    detalle=f"{c.get('servicioTIpo') or ''} período {c['periodo']}, suministro {socio}-{conexion}".strip(),
                    id_contacto=ID_CONTACTO)
                doc.bajar = self._bajador(sesion, ruta, doc)
                docs.append(doc)
        return docs

    def _bajador(self, sesion: _Sesion, ruta: str, doc: DocumentoPortal):
        def bajar() -> bytes:
            pdf = self._get(sesion, ruta).body()
            if not pdf.startswith(b"%PDF"):
                raise PortalCambio("La Cooperativa Eléctrica no entregó la factura")
            doc.fecha = _fecha_emision(pdf) or doc.fecha
            return pdf
        return bajar

    def estado_cuenta(self, sesion: _Sesion) -> list[EstadoCuentaPortal]:
        hoy, total, movimientos = date.today(), Decimal(0), []
        for s in self._suministros(sesion):
            socio, conexion = s["n_socio"], s["n_conexion"]
            r = self._get(sesion, f"nservicioasociado/getDeudaResumida/{socio}&{conexion}").json() or {}
            deuda = sum(Decimal(str(r.get(k) or 0)) for k in (
                "deudaVencidaEnergia", "deudaAVencerEnergia", "deudaVencidaServiciosSociales",
                "deudaAVencerServiciosSociales"))
            a_favor = Decimal(str(r.get("dineroAFavor") or 0))
            total += deuda - a_favor
            for c in self._get(sesion, f"nservicioasociado/getDeuda/{socio}&{conexion}").json() or []:
                if c.get("grupo") != "impaga":
                    continue
                vence = _fecha(c.get("fechaVto"))
                movimientos.append(MovimientoCuenta(
                    fecha=vence, comprobante=c.get("comprobanteFormat"),
                    detalle=f"{c.get('servicioTIpo') or ''} {c['periodo']} impaga, vence {vence:%d/%m/%Y}"[:200] if vence else None,
                    debe=None, haber=Decimal(str(c.get("saldo") or 0)), saldo=None))
            if a_favor:
                movimientos.append(MovimientoCuenta(fecha=hoy, comprobante=None, detalle=f"Dinero a favor, suministro {socio}-{conexion}",
                                                    debe=a_favor, haber=None, saldo=None))
        # Saldo positivo = le debemos a la Cooperativa (deuda menos dinero a favor).
        return [EstadoCuentaPortal(fecha_corte=hoy, moneda="ARS", saldo=total.quantize(Decimal("0.01")), completa=False,
                                   movimientos=movimientos)]

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes):
        return None

    def cerrar(self, sesion: _Sesion) -> None:
        sesion.browser.close()


registrar(ConectorCebol())
