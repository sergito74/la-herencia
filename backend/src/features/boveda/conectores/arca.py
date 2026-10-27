"""Conector de ARCA, Sistema de Cuentas Tributarias (042, T042).

Ingresa con la clave fiscal del representante (CUIT, botón "Siguiente", clave),
abre "Sistema de Cuentas Tributarias" desde Mis servicios, elige el
contribuyente representado y consulta "Estado de Cumplimiento" con los filtros
por defecto (todos los impuestos, año en curso; el botón "Siguiente" solo
ejecuta la consulta). Lee el subtotal de cada impuesto. No entra a pagos,
presentaciones, compensaciones, transferencias, devoluciones ni ningún otro
trámite. Relevamiento: specs/042-boveda-portales/relevamientos/arca.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DocumentoPortal, EstadoCuentaPortal, MovimientoCuenta, PortalCambio,
    RequiereIntervencion, registrar,
)

LOGIN = "https://auth.afip.gob.ar/contribuyente_/login.xhtml"
MIS_SERVICIOS = "https://portalcf.cloud.afip.gob.ar/portal/app/mis-servicios"

_SUBTOTAL = re.compile(
    r"(\d+ - [^\n]+?)\s*\n\s*CSVEXCELPDFIMPRIMIR.*?Subtotal\s+\$\s*([\d.,-]+)\s+\$\s*([\d.,-]+)\s+\$\s*([\d.,-]+)"
    r"\s+\$\s*([\d.,-]+)\s+\$\s*([\d.,-]+)", re.S)


@dataclass
class _Sesion:
    browser: object
    sct: object = None


def _importe(t: str) -> Decimal:
    return Decimal(t.replace(".", "").replace(",", "."))


def _pesos(d: Decimal) -> str:
    return f"$ {d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ConectorArca:
    tiene_estado_cuenta = True
    tiene_carga_compras = False
    mapeo_proveedores: dict = {}

    def __init__(self, codigo: str, nombre: str, cuit_representado: str | None = None):
        self.codigo = codigo
        self.nombre = nombre
        self._cuit = cuit_representado

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        try:
            p = browser.new_context().new_page()
            p.goto(LOGIN, wait_until="networkidle", timeout=90000)
            p.fill("input[id$=username]", (credencial.usuario or "").replace("-", ""))
            p.click("input[id$=btnSiguiente]")
            p.wait_for_load_state("networkidle", timeout=90000)
            if p.locator("img[id*=captcha], div.g-recaptcha, iframe[src*=captcha]").count():
                raise RequiereIntervencion("ARCA pidió un captcha")
            p.fill("input[type=password]", credencial.clave.valor() if credencial.clave else "")
            p.click("input[id$=btnIngresar]")
            p.wait_for_load_state("networkidle", timeout=90000)
            if "portalcf" not in p.url:
                raise CredencialesRechazadas("ARCA rechazó la clave fiscal")
            sct, opciones = self._abrir_cuentas_tributarias(p)
            cuit = self._cuit or (credencial.usuario or "").replace("-", "")  # sin representado: la cuenta propia
            valor = next((v for v, texto in opciones if texto == cuit), None)
            if valor is None:
                raise PortalCambio("La clave fiscal no tiene acceso al contribuyente en Cuentas Tributarias")
            with sct.expect_navigation(wait_until="networkidle", timeout=90000):
                sct.eval_on_selector("select", f"""e => {{ e.value = "{valor}";
                    e.dispatchEvent(new Event("change", {{bubbles: true}})); }}""")
            sct.wait_for_selector("a", state="attached", timeout=90000)
            return _Sesion(browser=browser, sct=sct)
        except Exception:
            browser.close()
            raise

    def _abrir_cuentas_tributarias(self, p):
        """A veces la ventana queda trabada en el ingreso único de ARCA (pasó 2 de 8 veces el 27/10/2026): se cierra
        y se vuelve a abrir desde Mis servicios, hasta 3 veces."""
        for intento in range(3):
            p.goto(MIS_SERVICIOS, wait_until="networkidle", timeout=90000)
            with p.expect_popup(timeout=90000) as popup:
                p.get_by_text("SISTEMA DE CUENTAS TRIBUTARIAS", exact=False).first.click()
            sct = popup.value
            try:
                return sct, self._opciones(sct, intentos=4 if intento < 2 else 10)
            except PortalCambio:
                if intento == 2:
                    raise
                sct.close()

    @staticmethod
    def _opciones(sct, intentos: int = 10) -> list[list[str]]:
        """Contribuyentes del selector. La página se redirige un par de veces al abrir (ingreso único de ARCA)."""
        from playwright.sync_api import Error as ErrorPlaywright

        for _ in range(intentos):
            try:
                sct.wait_for_load_state("networkidle", timeout=90000)
                sct.wait_for_selector("select", state="attached", timeout=30000)
                return sct.eval_on_selector_all("select:first-of-type option",
                                                "e => e.map(x => [x.value, x.innerText.trim()])")
            except ErrorPlaywright:
                sct.wait_for_timeout(2000)
        raise PortalCambio("ARCA no terminó de abrir Cuentas Tributarias (se reintentó)")

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        return []

    def estado_cuenta(self, sesion: _Sesion) -> list[EstadoCuentaPortal]:
        q = sesion.sct
        enlace = q.eval_on_selector_all("a", """e => (e.find(x => (x.innerText || '').trim() === 'Estado de Cumplimiento')
            || {}).href || null""")
        if not enlace:
            raise PortalCambio("No se encontró Estado de Cumplimiento en Cuentas Tributarias")
        q.goto(enlace, wait_until="networkidle", timeout=90000)
        q.locator("[name=functor]").first.click()  # "Siguiente": ejecuta la consulta con los filtros por defecto
        q.wait_for_load_state("networkidle", timeout=90000)
        for _ in range(90):
            if "CARGANDO" not in q.inner_text("body"):
                break
            q.wait_for_timeout(2000)
        else:
            raise PortalCambio("ARCA no terminó de cargar el Estado de Cumplimiento")
        texto = q.inner_text("body").replace("\t", " ")
        hoy = date.today()
        movimientos: list[MovimientoCuenta] = []
        total = Decimal(0)
        for m in _SUBTOTAL.finditer(texto):
            impuesto = m.group(1).strip()
            deuda, sld, tecnico, otros, multas = (_importe(m.group(i)) for i in range(2, 7))
            if not any((deuda, sld, tecnico, otros, multas)):
                continue
            partes = [f"deuda {_pesos(deuda)}"] if deuda else []
            partes += [f"{n} {_pesos(v)}" for n, v in (("saldo de libre disponibilidad", sld), ("saldo técnico", tecnico),
                                                         ("otros créditos", otros), ("multas no firmes", multas)) if v]
            total += deuda + multas
            movimientos.append(MovimientoCuenta(fecha=hoy, comprobante=impuesto[:50], detalle=f"{impuesto}: {', '.join(partes)}"[:200],
                                                debe=sld or None, haber=(deuda + multas) or None, saldo=deuda + multas))
        if not movimientos and "Subtotal" not in texto:
            raise PortalCambio("El Estado de Cumplimiento de ARCA no tiene el formato esperado")
        # Foto informativa: deuda exigible del año por impuesto (los saldos a favor van en el detalle).
        return [EstadoCuentaPortal(fecha_corte=hoy, moneda="ARS", saldo=total, completa=False, movimientos=movimientos)]

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes):
        return None

    def cerrar(self, sesion: _Sesion) -> None:
        sesion.browser.close()


registrar(ConectorArca("arca_giamigli", "ARCA Giamigli", "30712114602"))
registrar(ConectorArca("arca_sergio", "ARCA Sergio"))
registrar(ConectorArca("arca_lucy", "ARCA Lucy"))
