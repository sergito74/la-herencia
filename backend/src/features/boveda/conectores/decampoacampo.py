"""Conector de De Campo a Campo, remates de hacienda (043, US3, research R7). Solo lectura y descarga.

La cuenta de Sergio administra dos sociedades: Giamigli De Bolivar SA y Ganadera San Justo. De San Justo no se
registra ni se baja nada (Sergio, 27/10/2026):
- Operaciones (app `react.alb`, API `api.alb/v1/MisOperaciones/...`): se filtran por CUIT de Giamigli
  (`sociedad_vendedora` en ventas, `sociedad_compradora` en compras) antes de armar cualquier documento; de las
  demás no se guarda ni se abre nada.
- Mi Historial de Retenciones: se lee solo con Giamigli elegida en el selector de sociedad; nunca se elige otra.
Se bajan la liquidación y las notas de débito de cada operación y los certificados de retención. Nunca se usa
Programar pago, Ofertar, Comprar, Cotizar ni Consultas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DocumentoPortal, PortalCambio, registrar,
)

INGRESO = "https://www.decampoacampo.com/__dcac/login"
RETENCIONES = "https://www.decampoacampo.com/__dcac/perfil/MiHistorialRetenciones"
GIAMIGLI = "30712114602"
SUBRUTAS = {"venta": ("con-saldo", "cerrado"), "compra": ("con-saldo", "cerrado")}
_API_OPERACIONES = re.compile(r"/v1/MisOperaciones/invernada/(venta|compra)/\w+")


@dataclass
class _Sesion:
    browser: object
    contexto: object
    pagina: object
    enlaces: dict = field(default_factory=dict)


def _cuit(valor) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _fecha(valor) -> date | None:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(valor or "")) or None
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", str(valor or ""))
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def _importe(valor) -> Decimal | None:
    try:
        return Decimal(str(valor)).quantize(Decimal("0.01")) if valor not in (None, "") else None
    except InvalidOperation:
        return None


def operaciones_giamigli(respuestas: list[dict], lado: str) -> list[dict]:
    """Operaciones de Giamigli en las respuestas de la API. `lado`: `venta` (Giamigli vende) o `compra`.
    Todo lo de otra sociedad se descarta acá, antes de mirar sus documentos."""
    clave = "sociedad_vendedora" if lado == "venta" else "sociedad_compradora"
    vistas, propias = set(), []
    for r in respuestas:
        for op in (r.get("data") or []) if isinstance(r.get("data"), list) else []:
            if _cuit((op.get(clave) or {}).get("cuit")) != GIAMIGLI:
                continue
            id_op = op.get("id") or op.get("operacion_id") or op.get("lote_id")
            if id_op is not None and id_op in vistas:
                continue
            vistas.add(id_op)
            propias.append(op)
    return propias


def documentos_de_operacion(op: dict, lado: str) -> list[dict]:
    """Archivos a bajar de una operación de Giamigli: liquidación y notas de débito. Las notas de débito son
    ajustes de la liquidación (Sergio las carga en Ventas de hacienda), así que van como `liquidacion`."""
    id_op = op.get("id") or op.get("operacion_id") or op.get("lote_id")
    liq = op.get("datos_liquidacion") or {}
    pactadas = op.get("condiciones_pactadas") or {}
    sufijo = "vendedor" if lado == "venta" else "comprador"
    docs = []
    for tipo, campo in (("liquidacion", f"liquidacion_{sufijo}"), ("nota_debito", f"nota_debito_{sufijo}")):
        for i, archivo in enumerate(op.get(campo) or []):
            if not archivo.get("url"):
                continue
            docs.append({
                "clave": f"decampoacampo:{lado}:{id_op}:{tipo}:{i}", "tipo": "liquidacion", "url": archivo["url"],
                "fecha": _fecha(archivo.get("fecha_actualizacion")) or _fecha(pactadas.get("fecha_vendida")),
                "numero": liq.get("numero_factura") if tipo == "liquidacion" else None,
                "total": _importe(liq.get("importe_total")) if tipo == "liquidacion" else None,
                "detalle": f"{'Venta' if lado == 'venta' else 'Compra'} #{id_op}: "
                           f"{'liquidación' if tipo == 'liquidacion' else 'nota de débito'}",
            })
    return docs


def completar_desde_texto(doc: DocumentoPortal, texto: str) -> None:
    """Lo que el portal no informa y está en el PDF: número de comprobante de las notas de débito y fecha y
    número de los certificados de retención (el historial no muestra la fecha)."""
    if not doc.numero:
        m = re.search(r"\b(\d{4})-(\d{8})\b", texto)
        if m:
            doc.numero = f"{m.group(1)}-{m.group(2)}"
        m = re.search(r"N[uú]mero:\s*([\d\- ]{10,})", texto)
        if doc.tipo == "certificado" and m:
            doc.numero = re.sub(r"\s", "", m.group(1)).strip("-")
    if doc.tipo == "certificado":
        m = re.search(r"Fecha:\s*(\d{2}/\d{2}/\d{4})", texto)
        doc.fecha = _fecha(m.group(1)) if m else doc.fecha


class OtraSociedad(PortalCambio):
    pass


def _completar(doc: DocumentoPortal, pdf: bytes) -> None:
    """Completa número y fecha, y corta si el PDF es de Ganadera San Justo (segunda barrera: nunca se guarda)."""
    from src.features.documentos_nuevos.clasificador import es_de_san_justo, texto_pdf

    try:
        texto = texto_pdf(pdf, paginas=1)
    except Exception:
        return  # sin texto legible: queda lo que informó el portal
    if es_de_san_justo(texto) and GIAMIGLI not in re.sub(r"\D", "", texto):
        raise OtraSociedad("El portal entregó un documento de otra sociedad: no se guarda")
    completar_desde_texto(doc, texto)


class ConectorDeCampoACampo:
    codigo = "decampoacampo"
    nombre = "De Campo a Campo"
    tiene_estado_cuenta = False
    tiene_carga_compras = False
    mapeo_proveedores: dict = {}

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        browser = pw.chromium.launch(headless=True)
        try:
            ctx = browser.new_context()
            p = ctx.new_page()
            p.goto(INGRESO, wait_until="load", timeout=90000)
            p.click("#btn_login")
            p.fill("#maillog", credencial.usuario or "")
            p.fill("#password", credencial.clave.valor() if credencial.clave else "")
            p.click("#ingresar_login")
            for _ in range(30):
                p.wait_for_timeout(1000)
                try:
                    enlaces = {t: h for t, h in p.eval_on_selector_all(
                        "a", "as => as.map(a => [a.innerText.trim(), a.href])") if t}
                except Exception:  # la página navega mientras ingresa
                    continue
                if "Ventas" in enlaces and "Compras" in enlaces:
                    return _Sesion(browser=browser, contexto=ctx, pagina=p, enlaces=enlaces)
            raise CredencialesRechazadas("De Campo a Campo rechazó usuario o contraseña")
        except Exception:
            browser.close()
            raise

    def _respuestas(self, s: _Sesion, lado: str) -> list[dict]:
        """Lo que la app de operaciones pide a su API al recorrer las pestañas (con saldo y cerradas)."""
        capturadas: list = []

        def guardar(r):
            if _API_OPERACIONES.search(r.url) and r.request.resource_type in ("xhr", "fetch"):
                capturadas.append(r)

        s.contexto.on("response", guardar)
        try:
            inicio = s.enlaces["Ventas" if lado == "venta" else "Compras"]
            p = s.pagina
            p.goto(inicio, wait_until="networkidle", timeout=90000)
            base = re.sub(r"\?.*$", "", p.url)
            base = base.rsplit(f"/{lado}", 1)[0] + f"/{lado}"
            for sub in SUBRUTAS[lado]:
                try:
                    with p.expect_response(lambda r: _API_OPERACIONES.search(r.url) is not None, timeout=30000):
                        p.goto(f"{base}/{sub}", wait_until="networkidle", timeout=90000)
                except Exception:  # pestaña sin operaciones: la app no siempre consulta
                    pass
                p.wait_for_timeout(1500)
        finally:
            s.contexto.remove_listener("response", guardar)
        datos = []
        for r in capturadas:
            try:
                datos.append(r.json())
            except Exception:
                continue
        return datos

    def _bajador(self, s: _Sesion, url: str, doc: DocumentoPortal):
        def bajar() -> bytes:
            r = s.contexto.request.get(url, timeout=90000)
            if not r.ok:
                raise PortalCambio("De Campo a Campo no entregó el archivo")
            pdf = r.body()
            _completar(doc, pdf)
            return pdf
        return bajar

    def _retenciones(self, s: _Sesion) -> list[DocumentoPortal]:
        p = s.pagina
        p.goto(RETENCIONES, wait_until="networkidle", timeout=90000)
        selector = p.query_selector("select")
        if selector is None:
            raise PortalCambio("No se encontró el selector de sociedad en Mi Historial de Retenciones")
        elegida = p.eval_on_selector("select", "e => e.options[e.selectedIndex].text")
        if "GIAMIGLI" not in (elegida or "").upper():
            valor = p.eval_on_selector(
                "select", "e => (Array.from(e.options).find(o => /giamigli/i.test(o.text)) || {}).value")
            if not valor:
                raise PortalCambio("La cuenta no muestra la sociedad Giamigli en retenciones")
            p.select_option("select", valor)
            p.wait_for_load_state("networkidle", timeout=60000)
            p.wait_for_timeout(2000)
            elegida = p.eval_on_selector("select", "e => e.options[e.selectedIndex].text")
            if "GIAMIGLI" not in (elegida or "").upper():
                raise PortalCambio("No se pudo elegir la sociedad Giamigli en retenciones")
        docs = []
        for texto, fecha, url in p.eval_on_selector_all(
                "tbody tr", "trs => trs.map(t => { const c = t.querySelectorAll('td'); const a = t.querySelector('a');"
                " return [c[0] ? c[0].innerText.trim() : '', c[1] ? c[1].innerText.trim() : '', a ? a.href : ''] })"):
            if not url:
                continue
            archivo = url.split("?")[0].rsplit("/", 1)[-1]
            doc = DocumentoPortal(
                clave=f"decampoacampo:retencion:{archivo}", fecha=_fecha(fecha), tipo="certificado",
                proveedor="DeCampoACampo", bajar=lambda: b"", detalle="Certificado de retención")
            doc.bajar = self._bajador(s, url, doc)
            docs.append(doc)
        return docs

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        docs = []
        for lado in ("venta", "compra"):
            for op in operaciones_giamigli(self._respuestas(sesion, lado), lado):
                for d in documentos_de_operacion(op, lado):
                    doc = DocumentoPortal(
                        clave=d["clave"], fecha=d["fecha"], tipo=d["tipo"], proveedor="DeCampoACampo",
                        bajar=lambda: b"", numero=d["numero"], total=d["total"], moneda="ARS", detalle=d["detalle"])
                    doc.bajar = self._bajador(sesion, d["url"], doc)
                    docs.append(doc)
        return docs + self._retenciones(sesion)

    def estado_cuenta(self, sesion: _Sesion) -> list:
        return []

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes):
        return None

    def cerrar(self, sesion: _Sesion) -> None:
        sesion.browser.close()


registrar(ConectorDeCampoACampo())
