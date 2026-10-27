"""Conector de la extranet de Bayá Casal (042, T040).

Ingresa con usuario y clave, abre la cuenta corriente bimonetaria (`/ctacteA/`)
con el filtro por fecha de emisión e incluyendo aplicaciones (se completa el
formulario de filtro, que solo consulta) y baja el PDF de cada comprobante con
`obtenerPDF.php`, que lo devuelve embebido en base64. No usa "Cambiar
contraseña", mensajes ni ninguna otra opción. Relevamiento:
specs/042-boveda-portales/relevamientos/baya-casal.md.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DocumentoPortal, EstadoCuentaPortal, MovimientoCuenta, PortalCambio,
    registrar,
)

BASE = "https://extranet.ebayacasal.com.ar/"
ID_CONTACTO = 226
PROVEEDOR = "BayaCasal"

TIPOS = {"FC": "factura", "NC": "nota_credito", "ND": "nota_debito", "RI": "otro", "CA": "otro", "RG": "otro"}

_FILAS_JS = """e => e.map(r => [...r.querySelectorAll('td')].map(c => {
    const a = c.querySelector('a[href*="obtenerPDF"]');
    return a ? 'PDF:' + a.getAttribute('href') : c.innerText.trim();
}))"""


@dataclass
class _Sesion:
    browser: object
    pagina: object = None


def _fecha(texto: str) -> date | None:
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _importe(texto: str) -> Decimal | None:
    t = texto.replace("\xa0", "").strip()
    if not t:
        return None
    try:
        return Decimal(t.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def _inicio_ejercicio(d: date) -> date:
    return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


class ConectorBayaCasal:
    codigo = "baya_casal"
    nombre = "Bayá Casal"
    tiene_estado_cuenta = True
    tiene_carga_compras = False
    mapeo_proveedores: dict = {}

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        browser = pw.chromium.launch(headless=True)
        try:
            pagina = browser.new_context().new_page()
            pagina.goto(BASE, wait_until="networkidle", timeout=90000)
            pagina.fill("[name=usuario]", credencial.usuario or "")
            pagina.fill("[name=password]", credencial.clave.valor() if credencial.clave else "")
            pagina.click("button[type=submit]")
            pagina.wait_for_load_state("networkidle", timeout=90000)
            if "/home" not in pagina.url:
                if pagina.locator("[name=password]").count():
                    raise CredencialesRechazadas("Bayá Casal rechazó usuario o contraseña")
                raise PortalCambio("No se pudo completar el ingreso a Bayá Casal")
            return _Sesion(browser=browser, pagina=pagina)
        except Exception:
            browser.close()
            raise

    def _cuenta(self, sesion: _Sesion, desde: date, aplicaciones: bool) -> list[list[str]]:
        p = sesion.pagina
        p.goto(BASE + "ctacteA/", wait_until="networkidle", timeout=90000)
        if not p.locator("form[name=form1]").count():
            raise PortalCambio("La cuenta corriente de Bayá Casal no tiene el filtro esperado")
        # Solo completa el filtro de consulta (fecha de emisión, con aplicaciones) y lo aplica.
        with p.expect_navigation(wait_until="networkidle", timeout=90000):
            p.evaluate("""([desde, apl]) => { const f = document.form1; f.desde.value = desde;
                f.tipofecha.value = 'FC'; f.aplicaciones.value = apl; f.submit(); }""",
                       [desde.isoformat(), "SI" if aplicaciones else "NO"])
        return [f for f in p.eval_on_selector_all("table tr", _FILAS_JS) if len(f) >= 10]

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        docs: dict[str, DocumentoPortal] = {}
        for f in self._cuenta(sesion, _inicio_ejercicio(date.today()), aplicaciones=True):
            if not f[9].startswith("PDF:"):
                continue
            href = f[9][4:]
            clave = "baya:" + base64.b64decode(href.split("file=")[1]).decode("latin-1")
            if clave in docs:  # una aplicación repite el enlace en varias filas
                continue
            partes = f[1].split()
            numero = f"{partes[1]}-{partes[2]}" if len(partes) == 3 else f[1]
            docs[clave] = DocumentoPortal(
                clave=clave, fecha=_fecha(f[3]) or _fecha(f[0]), tipo=TIPOS.get(partes[0] if partes else "", "otro"),
                proveedor=PROVEEDOR, bajar=self._bajador(sesion, href), numero=numero,
                detalle=f"{f[1]} {f[2]}".strip()[:200], id_contacto=ID_CONTACTO,
                moneda="USD" if (_importe(f[6]) or 0) else "ARS",
                total=_importe(f[6]) or _importe(f[5]),
            )
        return list(docs.values())

    def _bajador(self, sesion: _Sesion, href: str):
        def bajar() -> bytes:
            r = sesion.pagina.context.request.get(BASE + href.replace("../", ""), timeout=120000)
            html = r.body()
            m = re.search(rb"data:application/pdf;base64,([A-Za-z0-9+/=\s]+)", html)
            if not m:
                raise PortalCambio("El portal no tiene el PDF de este comprobante")
            return base64.b64decode(re.sub(rb"\s", b"", m.group(1)))
        return bajar

    def estado_cuenta(self, sesion: _Sesion) -> list[EstadoCuentaPortal]:
        """Cuenta bimonetaria completa (desde 2010, sin aplicaciones). Fotos informativas: la deuda con Bayá
        incluye compras firmes todavía no facturadas que el portal no muestra, así que no se compara saldo."""
        filas = self._cuenta(sesion, date(2010, 1, 1), aplicaciones=False)
        if not filas:
            return []
        ultima = filas[-1]
        hoy = date.today()
        fotos = []
        for moneda, col_imp, col_saldo in (("ARS", 5, 7), ("USD", 6, 8)):
            movs = [
                MovimientoCuenta(fecha=_fecha(f[3]) or _fecha(f[0]), comprobante=f[1] or None, detalle=f[2][:200] or None,
                                 debe=None if (_importe(f[col_imp]) or 0) >= 0 else -_importe(f[col_imp]),
                                 haber=_importe(f[col_imp]) if (_importe(f[col_imp]) or 0) > 0 else None,
                                 saldo=_importe(f[col_saldo]))
                for f in filas if _importe(f[col_imp])
            ]
            # En el portal, saldo positivo = le debemos a Bayá Casal (igual que en la bóveda).
            fotos.append(EstadoCuentaPortal(fecha_corte=hoy, moneda=moneda, saldo=_importe(ultima[col_saldo]) or Decimal(0),
                                            completa=False, movimientos=movs))
        return fotos

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes):
        return None

    def cerrar(self, sesion: _Sesion) -> None:
        sesion.browser.close()


registrar(ConectorBayaCasal())
