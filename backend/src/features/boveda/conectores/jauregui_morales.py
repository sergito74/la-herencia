"""Conector de Jáuregui y Morales, portal de clientes FocaSoftware (042, T047).

Ingresa con usuario y clave, completa la fecha "Desde" del filtro y ejecuta
"Resumen de Cuenta" con el botón "Enviar datos" (solo corre la consulta; no
envía nada al proveedor). No usa "Cambiar Password".
Relevamiento: specs/042-boveda-portales/relevamientos/jauregui-morales.md.

Documentos comerciales (03/11/2026): el portal no tiene PDF, pero cada comprobante del resumen abre su detalle
(`resumen_cuenta/x_get_detalle`: JSON con artículos, neto, IVA, impuestos internos, percepción y total). Con ese
detalle se pide el PDF que imprime el propio portal (botón "Imprimir", `x_imprimir_datos`) y la compra se carga
sola: combustibles al rubro de combustibles, el resto (lubricantes, insumos) al de lubricantes, como se venía
cargando a mano.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DatosCompra, DocumentoPortal, EstadoCuentaPortal, MovimientoCuenta,
    PortalCambio, registrar,
)

INGRESO = "http://45.176.20.244/clientes/"
ID_CONTACTO = 48
RUBRO_COMBUSTIBLE = 1768231871
RUBRO_LUBRICANTES = 13
CENTRO_COSTO = 3
DESTINO = 1

# Cada celda del resumen es una línea: fecha-hora, comprobante, forma de pago, tipo, débito, crédito, saldo.
_FILA = re.compile(r"^(\d{4}-\d{2}-\d{2}) [\d:.]+\n([A-Z] \d{4}-\d{8})\n(\w+)\n(\w+)\n([^\n]*)\n([^\n]*)\n([^\n]*)$", re.M)
_DEUDA = re.compile(r"\(Deuda:\s*(-?[\d.,]+)\)")
_SALDO_FINAL = re.compile(r"Totales al:[^\n]*\n[^\n]*\n[^\n]*\n\s*(-?[\d.,]+)")
_COMBUSTIBLE = re.compile(r"\b(SUPER|NAFTA|GASOIL|GAS OIL|DIESEL|INFINIA|EURO|PREMIUM|ULTRA)\b", re.I)
_TIPO_DOC = {"FT": ("factura", "Factura"), "NC": ("nota_credito", "Nota de Crédito"),
             "ND": ("nota_debito", "Nota de Débito")}


@dataclass
class _Sesion:
    browser: object
    pagina: object = None
    usuario: str = ""
    detalles: dict = field(default_factory=dict)
    texto_resumen: str | None = None


def _importe(t) -> Decimal | None:
    t = str(t if t is not None else "").replace("&nbsp;", "").strip()
    return Decimal(t.replace(".", "").replace(",", ".")) if t else None


def _inicio_ejercicio(d: date) -> date:
    return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


class ConectorJaureguiMorales:
    codigo = "jauregui_morales"
    nombre = "Jáuregui y Morales"
    tiene_estado_cuenta = True
    tiene_carga_compras = True
    mapeo_proveedores: dict = {}

    def __init__(self):
        self._ultima_sesion: _Sesion | None = None

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        try:
            p = browser.new_context().new_page()
            p.goto(INGRESO, wait_until="load", timeout=90000)
            p.fill("#txtUsuario", credencial.usuario or "")
            p.fill("#txtPassword", credencial.clave.valor() if credencial.clave else "")
            p.get_by_role("button", name="Ingresar").click()
            for _ in range(30):
                if "/main" in p.url:
                    self._ultima_sesion = _Sesion(browser=browser, pagina=p, usuario=(credencial.usuario or "").strip())
                    return self._ultima_sesion
                p.wait_for_timeout(1000)
            raise CredencialesRechazadas("Jáuregui y Morales rechazó usuario o contraseña")
        except Exception:
            browser.close()
            raise

    # --- Resumen de cuenta ---------------------------------------------------------------------------------

    def _resumen(self, sesion: _Sesion) -> str:
        """Texto del "Resumen de Cuenta" desde el inicio del ejercicio (se consulta una vez por sesión)."""
        if sesion.texto_resumen:
            return sesion.texto_resumen
        p = sesion.pagina
        # La página principal a veces llega incompleta o lenta (03/11/2026, "#txtDatosDesde" no encontrado): se
        # espera el formulario y, si no aparece, se recarga una vez.
        for intento in (1, 2):
            try:
                p.wait_for_selector("#txtDatosDesde", state="attached", timeout=60000)
                break
            except Exception:
                if intento == 2:
                    raise PortalCambio("Jáuregui y Morales no mostró el formulario del resumen")
                p.reload(wait_until="load", timeout=90000)
        p.eval_on_selector("#txtDatosDesde", f"e => e.value = '{_inicio_ejercicio(date.today()):%d-%m-%Y}'")
        p.check("input[name=tipoana][value=resumen]")
        p.get_by_role("button", name="Enviar datos").click()
        for _ in range(60):
            if "Totales al:" in p.inner_text("body"):
                break
            p.wait_for_timeout(1000)
        else:
            raise PortalCambio("Jáuregui y Morales no mostró el resumen de cuenta")
        sesion.texto_resumen = p.inner_text("body")
        return sesion.texto_resumen

    # --- Documentos comerciales ----------------------------------------------------------------------------

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        """Facturas, NC y ND del ejercicio: el detalle del portal da el PDF y los datos para la carga."""
        p = sesion.pagina
        docs = []
        for m in _FILA.finditer(self._resumen(sesion)):
            tco = m.group(4).upper()[:2]
            if tco not in _TIPO_DOC:
                continue  # recibos y otros movimientos: van por el estado de cuenta
            letra, suc, nco = re.match(r"([A-Z]) (\d{4})-(\d{8})", m.group(2)).groups()
            r = p.request.post(INGRESO + "resumen_cuenta/x_get_detalle", timeout=60000,
                               form={"cod": sesion.usuario, "tco": tco, "tip": letra, "suc": str(int(suc)),
                                     "nco": str(int(nco))})
            datos = r.json()
            det = (datos.get("data") or {}).get("detalle") or {}
            numero = f"{suc}-{nco}"
            sesion.detalles[numero] = (tco, letra, det)
            pie = det.get("arr_pie") or {}
            doc = DocumentoPortal(clave=f"jauregui:{tco}:{letra}:{numero}",
                                  fecha=datetime.strptime(m.group(1), "%Y-%m-%d").date(), tipo=_TIPO_DOC[tco][0],
                                  proveedor="JaureguiYMorales", bajar=lambda: b"", numero=numero,
                                  total=_importe(pie.get("latot")), moneda="ARS",
                                  detalle=f"{_TIPO_DOC[tco][1]} {letra} {numero}", id_contacto=ID_CONTACTO)
            doc.bajar = self._pdf(sesion, datos.get("data") or {"detalle": det})
            docs.append(doc)
        return docs

    @staticmethod
    def _pdf(sesion: _Sesion, comprobante: dict):
        """PDF del propio portal (botón "Imprimir" → `resumen_cuenta/x_imprimir_datos`). El portal antepone un salto
        de línea al encabezado %PDF: se quita para que el archivo sea un PDF válido."""
        def bajar() -> bytes:
            r = sesion.pagina.request.post(INGRESO + "resumen_cuenta/x_imprimir_datos", timeout=90000,
                                           form={"factura": json.dumps(comprobante)})
            cuerpo = r.body().lstrip()
            if not cuerpo.startswith(b"%PDF"):
                raise PortalCambio("Jáuregui y Morales no devolvió el PDF del comprobante")
            return cuerpo
        return bajar

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes) -> DatosCompra | None:
        sesion = self._ultima_sesion
        if not sesion or documento.numero not in sesion.detalles:
            return None
        tco, letra, det = sesion.detalles[documento.numero]
        pie = det.get("arr_pie") or {}
        num = lambda v: _importe(v) or Decimal("0")
        neto, iva, total = num(pie.get("langr")), num(pie.get("lairi")), num(pie.get("latot"))
        internos, percep = num(pie.get("laiin")), num(pie.get("lapiv"))
        items = det.get("arr_detalle") or []
        if not items or not neto or not total:
            return None
        bruto = sum(num(i.get("imp")) for i in items) or Decimal("1")
        alicuota = 10.5 if abs(iva / neto - Decimal("0.105")) < Decimal("0.01") else 21.0
        # El neto del portal viene redondeado y neto × (1 + IVA) puede no dar el total al centavo (27/10/2026:
        # 87.933,88 × 1,21 = 106.399,99): el gravado se toma del total impreso menos internos y percepción.
        neto = (total - internos - percep) / (Decimal(1) + Decimal(str(alicuota)) / 100)
        lineas = []
        for i in items:
            desc = (i.get("det") or "").strip()
            cant = float(num(i.get("can")) or 1)
            combustible = bool(_COMBUSTIBLE.search(desc))
            lineas.append({"productoServicio": desc[:50], "cantidad": cant,
                           "precioUnitario": float(neto * num(i.get("imp")) / bruto) / cant, "iva": alicuota,
                           "unidad": "LITRO" if combustible else "UNIDAD", "idCentroCosto": CENTRO_COSTO,
                           "idDestino": DESTINO, "idRubro": RUBRO_COMBUSTIBLE if combustible else RUBRO_LUBRICANTES,
                           "campaña": "No Aplica", "ajusteFinanciero": False})
        from src.features.compras import repository as compras

        cabecera = {"idContacto": ID_CONTACTO, "fecha": documento.fecha.isoformat(), "tipo": letra,
                    "tipoDocumento": _TIPO_DOC[tco][1], "numeroDocumento": documento.numero, "moneda": "Pesos",
                    "tipoDeCambio": 1.0, "ajustaTipoCambio": False}
        for campo in compras.CAMPOS_IMPORTE_CABECERA:
            cabecera[campo] = 0.0
        cabecera["conceptosNoGravados"] = float(internos)  # impuestos internos de combustibles (como se cargaba)
        cabecera["percepcionIva"] = float(percep)
        return DatosCompra(cabecera=cabecera, lineas=lineas, numero=documento.numero, total_impreso=total)

    # --- Estado de cuenta ----------------------------------------------------------------------------------

    def estado_cuenta(self, sesion: _Sesion) -> list[EstadoCuentaPortal]:
        texto = self._resumen(sesion)
        movimientos = [
            MovimientoCuenta(fecha=datetime.strptime(m.group(1), "%Y-%m-%d").date(), comprobante=m.group(2),
                             detalle=f"{m.group(4)} {m.group(2)}", debe=_importe(m.group(6)), haber=_importe(m.group(5)),
                             saldo=_importe(m.group(7)))
            for m in _FILA.finditer(texto)
        ]
        deuda = _SALDO_FINAL.search(texto) or _DEUDA.search(texto)
        if not deuda:
            raise PortalCambio("No se encontró el saldo en el resumen de Jáuregui y Morales")
        # Saldo positivo = le debemos al proveedor (débitos = facturas, créditos = recibos).
        return [EstadoCuentaPortal(fecha_corte=date.today(), moneda="ARS", saldo=_importe(deuda.group(1)),
                                   completa=False, movimientos=movimientos)]

    def cerrar(self, sesion: _Sesion) -> None:
        sesion.browser.close()


registrar(ConectorJaureguiMorales())
