"""Conectores de ARBA Autogestión (042, T043).

Ingresa con CUIT y clave (sin captcha), abre el panel "Gestionar" y lee, de la
misma API que usa la página, el padrón de objetos del contribuyente y la deuda
de cada uno (`services/objeto/deuda`). Solo consulta: no genera boletas, no
paga, no presenta declaraciones, no adhiere débitos ni cambia datos de
contacto. Relevamiento: specs/042-boveda-portales/relevamientos/arba.md.

Las boletas y la cuenta corriente impresa piden captcha en cada consulta: no se
bajan documentos, solo la foto de deuda por objeto.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DocumentoPortal, EstadoCuentaPortal, MovimientoCuenta, PortalCambio,
    RequiereIntervencion, registrar,
)

LOGIN = ("https://sso.arba.gov.ar/Login/login?service="
         "https%3A//www.arba.gov.ar/Gestionar/PanelAutogestion.asp")
GESTIONAR = ("https://www.arba.gov.ar/DatosContacto/DatosContactoRedirect.asp"
             "?destino=https://app.arba.gov.ar/Gestionar/dist/gestionar")
API = "https://app.arba.gov.ar/Gestionar/services"

# cod_impuesto del padrón → (código de deuda, nombre)
IMPUESTOS = {0: (131, "Inmobiliario"), 1: (551, "Automotor"), 2: (211, "Ingresos Brutos"), 10: (135, "Inmobiliario")}


@dataclass
class _Sesion:
    browser: object
    pagina: object = None
    cuit: str = ""


def _partida(objeto: str) -> str:
    o = objeto.strip()
    return f"{o[:3]}-{o[3:9]}-{o[9:]}" if len(o) == 10 and o.isdigit() else o


class ConectorArba:
    tiene_estado_cuenta = True
    tiene_carga_compras = False
    mapeo_proveedores: dict = {}

    def __init__(self, codigo: str, nombre: str, objetos: set[str] | None = None):
        self.codigo = codigo
        self.nombre = nombre
        self._objetos = objetos  # None = todos los del contribuyente

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        try:
            pagina = browser.new_context().new_page()
            cuit = (credencial.usuario or "").replace("-", "").strip()
            pagina.goto(LOGIN, wait_until="networkidle", timeout=90000)
            pagina.fill("#CUIT", cuit)
            pagina.fill("#clave_Cuit", credencial.clave.valor() if credencial.clave else "")
            pagina.locator("#clave_Cuit").press("Enter")
            pagina.wait_for_load_state("networkidle", timeout=90000)
            if "PanelAutogestion" not in pagina.url:
                texto = pagina.inner_text("body").lower()
                if "captcha" in texto:
                    raise RequiereIntervencion("ARBA pidió una verificación adicional")
                raise CredencialesRechazadas("ARBA rechazó CUIT o clave")
            pagina.goto(GESTIONAR, wait_until="networkidle", timeout=90000)
            return _Sesion(browser=browser, pagina=pagina, cuit=cuit)
        except Exception:
            browser.close()
            raise

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        return []

    def _json(self, sesion: _Sesion, url: str) -> dict:
        r = sesion.pagina.context.request.get(url, timeout=90000)
        if r.status != 200:
            raise PortalCambio(f"ARBA respondió {r.status} al consultar la deuda")
        return r.json()

    def estado_cuenta(self, sesion: _Sesion) -> list[EstadoCuentaPortal]:
        padron = self._json(sesion, f"{API}/padron/objetos/GESTIONAR")
        movimientos: list[MovimientoCuenta] = []
        deuda_total = Decimal(0)
        hoy = date.today()
        for o in padron.get("objetos") or []:
            cod = IMPUESTOS.get(o.get("cod_impuesto"))
            objeto = (o.get("objeto") or "").strip()
            if not cod or (self._objetos is not None and objeto not in self._objetos):
                continue
            d = self._json(sesion, f"{API}/objeto/deuda?impuesto={cod[0]}&objeto={objeto}&cuit={sesion.cuit}"
                                   f"&claveh={o.get('claveh') or ''}")
            deuda = Decimal(str(d.get("deuda_total") or 0))
            a_favor = Decimal(str(d.get("total_excedente") or 0))
            deuda_total += deuda - a_favor
            detalle = f"{cod[1]} {_partida(objeto)}"
            if d.get("deuda_judicial"):
                detalle += " (con deuda judicial)"
            if d.get("existe_plan_pago"):
                detalle += " (en plan de pagos)"
            movimientos.append(MovimientoCuenta(fecha=hoy, comprobante=_partida(objeto), detalle=detalle,
                                                debe=a_favor or None, haber=deuda or None, saldo=deuda - a_favor))
        if not movimientos:
            return []
        # Positivo = deuda nuestra con ARBA; negativo = saldo a favor. Foto informativa por impuesto.
        return [EstadoCuentaPortal(fecha_corte=hoy, moneda="ARS", saldo=deuda_total, completa=False,
                                   movimientos=movimientos)]

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes):
        return None

    def cerrar(self, sesion: _Sesion) -> None:
        sesion.browser.close()


registrar(ConectorArba("arba", "ARBA"))
# Cuenta de Oscar Giamberardini: solo la partida inmobiliaria pedida por Sergio (27/10/2026).
registrar(ConectorArba("arba_oscar", "ARBA (partida 011-007957-5)", objetos={"0110079575"}))
