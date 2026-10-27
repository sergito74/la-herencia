"""Conector del portal GPS de Cargill (042, T041).

Ingresa por el login Okta de mycargill.com y usa la misma API que la página
(api.cglcloud.com) con el token de la sesión. Solo consulta y descarga:
`GET /invoices` (documentos del ejercicio), `POST /userDocuments/download`
(PDF de un documento; es una descarga, no envía nada) y `POST
/accountbalance/currency` (libro de cuenta corriente). Nunca usa
`sendAccountBalance` ni ninguna opción que mande mails, firme contratos o
acepte documentos. Relevamiento: specs/042-boveda-portales/relevamientos/cargill.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DocumentoPortal, EstadoCuentaPortal, MovimientoCuenta, PortalCambio,
    RequiereIntervencion, registrar,
)

LOGIN = "https://www.mycargill.com/cascsa/v2/login"
API = "https://api.cglcloud.com/api/dxo/gps/v1"
PARAMS = "source=JDEAR&role=DXP_GPS_Role_Client"
CUSTOMER_ID = "35192801"
ID_CONTACTO = 258

TIPOS = {"RI": "factura", "RM": "nota_credito", "RT": "nota_debito", "L#": "liquidacion", "H7": "liquidacion", "$I": "certificado",
         "$B": "certificado"}


@dataclass
class _Sesion:
    browser: object
    ctx: object = None
    token: str | None = field(default=None, repr=False)


def _fecha(texto: str | None) -> date | None:
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date() if texto else None
    except ValueError:
        return None


def _inicio_ejercicio(d: date) -> date:
    return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


def _trimestres(desde: date, hasta: date):
    """El portal responde hasta ~3 meses por consulta."""
    while desde <= hasta:
        fin = min(date(desde.year + (desde.month + 2) // 12, (desde.month + 2) % 12 + 1, 1) - timedelta(days=1), hasta)
        yield desde, fin
        desde = fin + timedelta(days=1)


def _numero_fiscal(x: dict) -> str | None:
    """Número legal con que se carga en Compras (punto de venta-número, ej. 7050-00077233); el
    `invoiceNumber` del portal (51240-RT-…) es interno de Cargill."""
    ref = (x.get("externalDocumentReference") or "").strip()
    if x.get("invoiceTypeCode") in ("RI", "RM", "RT") and len(ref) == 12 and ref.isdigit():
        return f"{ref[:4]}-{ref[4:]}"
    if x.get("invoiceTypeCode") == "L#" and ref.isdigit():
        return ref  # COE de la liquidación
    return x.get("invoiceNumber") or None


def _dec(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


class ConectorCargill:
    codigo = "cargill"
    nombre = "Cargill"
    tiene_estado_cuenta = True
    tiene_carga_compras = False
    mapeo_proveedores: dict = {}

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        sesion = _Sesion(browser=browser)
        try:
            sesion.ctx = browser.new_context()
            pagina = sesion.ctx.new_page()

            def capturar(req):
                if sesion.token is None and "api.cglcloud.com" in req.url and req.headers.get("authorization"):
                    sesion.token = req.headers["authorization"]

            pagina.on("request", capturar)
            pagina.goto(LOGIN, wait_until="networkidle", timeout=90000)
            pagina.fill('input[name="username"], #okta-signin-username', credencial.usuario or "")
            pagina.fill('input[type="password"]', credencial.clave.valor() if credencial.clave else "")
            pagina.click('#okta-signin-submit, input[type="submit"]')
            for _ in range(30):
                if sesion.token:
                    break
                texto = pagina.inner_text("body").lower()
                if "incorrect" in texto or "incorrecto" in texto or "unable to sign in" in texto:
                    raise CredencialesRechazadas("Cargill rechazó usuario o contraseña")
                pagina.wait_for_timeout(1000)
            if not sesion.token:
                if "verif" in pagina.inner_text("body").lower():
                    raise RequiereIntervencion("Cargill pidió una verificación adicional")
                raise PortalCambio("No se pudo completar el ingreso a Cargill")
            return sesion
        except Exception:
            browser.close()
            raise

    def _get(self, sesion: _Sesion, ruta: str) -> dict:
        r = sesion.ctx.request.get(f"{API}/{ruta}", headers={"authorization": sesion.token}, timeout=120000)
        if r.status != 200:
            raise PortalCambio(f"Cargill respondió {r.status} al consultar documentos")
        return r.json().get("data") or {}

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        hoy = date.today()
        docs: list[DocumentoPortal] = []
        for desde, hasta in _trimestres(_inicio_ejercicio(hoy), hoy):
            offset = 0
            while True:
                data = self._get(sesion, f"invoices?{PARAMS}&invoiceFromDate={desde:%m/%d/%Y}&invoiceToDate={hasta:%m/%d/%Y}"
                                         f"&sortBy=invoiceDate&sort=asc&offset={offset}&limit=100")
                items = data.get("invoices") or []
                for x in items:
                    ids = [str(i) for i in (x.get("documentIds") or [])]
                    if not ids:  # sin PDF en el portal (ej. A/R drafts)
                        continue
                    docs.append(self._documento(sesion, x, ids))
                offset += len(items)
                if not items or offset >= (data.get("metadata") or {}).get("totalCount", 0):
                    break
        return docs

    def _documento(self, sesion: _Sesion, x: dict, ids: list[str]) -> DocumentoPortal:
        def bajar() -> bytes:
            r = sesion.ctx.request.post(
                f"{API}/userDocuments/download?{PARAMS}",
                headers={"authorization": sesion.token, "accept": "application/octet-stream",
                         "content-type": "application/json"},
                data={"documentIds": ids}, timeout=120000)
            if r.status != 200:
                raise PortalCambio(f"Cargill respondió {r.status} al bajar el documento")
            return r.body()

        moneda = "USD" if (x.get("localCurrencyCode") or "").lower().startswith("dolar") else "ARS"
        return DocumentoPortal(
            clave=f"cargill:{'-'.join(ids)}", fecha=_fecha(x.get("documentCreationDate")),
            tipo=TIPOS.get(x.get("invoiceTypeCode"), "otro"), proveedor="Cargill", bajar=bajar,
            numero=_numero_fiscal(x), total=_dec(x.get("amountLocalCurrency")), moneda=moneda,
            detalle=f"{(x.get('invoiceType') or '').strip().title()} {x.get('invoiceNumber') or ''}".strip(),
            id_contacto=ID_CONTACTO,
        )

    def estado_cuenta(self, sesion: _Sesion) -> list[EstadoCuentaPortal]:
        """Libro en pesos del último trimestre con movimientos (un trimestre sin movimientos viene vacío, sin
        saldo inicial). Queda como foto informativa (no completa): la cuenta de Cargill se lleva en dólares al
        TC de cada comprobante, así que el saldo en pesos del portal no se compara."""
        hoy = date.today()
        data: dict = {}
        for desde, hasta in reversed(list(_trimestres(_inicio_ejercicio(hoy) - timedelta(days=365), hoy))):
            r = sesion.ctx.request.post(
                f"{API}/accountbalance/currency?{PARAMS}&customerId={CUSTOMER_ID}&fromDate={desde:%m/%d/%Y}"
                f"&toDate={hasta:%m/%d/%Y}&isBlnCmpReq=false&sortBy=documentDate&sort=asc",
                headers={"authorization": sesion.token, "content-type": "application/json"}, data={}, timeout=120000)
            if r.status != 200:
                raise PortalCambio(f"Cargill respondió {r.status} al leer la cuenta corriente")
            data = r.json().get("data") or {}
            if data.get("balances"):
                break
        if not data.get("balances"):
            return []
        resumen = data.get("financialSummary") or {}
        movimientos = [
            MovimientoCuenta(
                fecha=_fecha(m.get("documentDate")), comprobante=m.get("invoiceNumber") or m.get("legalDocument"),
                detalle=(m.get("concepts") or m.get("documentType") or "").strip()[:200],
                # Del lado nuestro: lo que Cargill nos acredita es haber; lo que nos debita, debe.
                debe=_dec(m.get("cargillBalance")) or None, haber=_dec(m.get("customerBalance")) or None,
                saldo=-_dec(m.get("totalBalanceAccumulated") or 0),
            )
            for m in data.get("balances") or []
        ]
        # En el portal, negativo = le debemos a Cargill; en la bóveda, positivo = deuda nuestra.
        saldo = -Decimal(str(resumen.get("currentAccountBalance") or 0))
        return [EstadoCuentaPortal(fecha_corte=hoy, moneda="ARS", saldo=saldo, completa=False, movimientos=movimientos)]

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes):
        return None

    def cerrar(self, sesion: _Sesion) -> None:
        sesion.browser.close()


registrar(ConectorCargill())
