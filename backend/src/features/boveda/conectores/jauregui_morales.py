"""Conector de Jáuregui y Morales, portal de clientes FocaSoftware (042, T047).

Ingresa con usuario y clave, completa la fecha "Desde" del filtro y ejecuta
"Resumen de Cuenta" con el botón "Enviar datos" (solo corre la consulta; no
envía nada al proveedor). El portal no ofrece los PDF de los comprobantes: solo
se guarda la foto del resumen de cuenta. No usa "Cambiar Password".
Relevamiento: specs/042-boveda-portales/relevamientos/jauregui-morales.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DocumentoPortal, EstadoCuentaPortal, MovimientoCuenta, PortalCambio,
    registrar,
)

INGRESO = "http://45.176.20.244/clientes/"

# Cada celda del resumen es una línea: fecha-hora, comprobante, forma de pago, tipo, débito, crédito, saldo.
_FILA = re.compile(r"^(\d{4}-\d{2}-\d{2}) [\d:.]+\n([A-Z] \d{4}-\d{8})\n(\w+)\n(\w+)\n([^\n]*)\n([^\n]*)\n([^\n]*)$", re.M)
_DEUDA = re.compile(r"\(Deuda:\s*(-?[\d.,]+)\)")
_SALDO_FINAL = re.compile(r"Totales al:[^\n]*\n[^\n]*\n[^\n]*\n\s*(-?[\d.,]+)")


@dataclass
class _Sesion:
    browser: object
    pagina: object = None


def _importe(t: str) -> Decimal | None:
    t = t.strip()
    return Decimal(t.replace(".", "").replace(",", ".")) if t else None


def _inicio_ejercicio(d: date) -> date:
    return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


class ConectorJaureguiMorales:
    codigo = "jauregui_morales"
    nombre = "Jáuregui y Morales"
    tiene_estado_cuenta = True
    tiene_carga_compras = False
    mapeo_proveedores: dict = {}

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        browser = pw.chromium.launch(headless=True)
        try:
            p = browser.new_context().new_page()
            p.goto(INGRESO, wait_until="load", timeout=90000)
            p.fill("#txtUsuario", credencial.usuario or "")
            p.fill("#txtPassword", credencial.clave.valor() if credencial.clave else "")
            p.get_by_role("button", name="Ingresar").click()
            for _ in range(30):
                if "/main" in p.url:
                    return _Sesion(browser=browser, pagina=p)
                p.wait_for_timeout(1000)
            raise CredencialesRechazadas("Jáuregui y Morales rechazó usuario o contraseña")
        except Exception:
            browser.close()
            raise

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        return []

    def estado_cuenta(self, sesion: _Sesion) -> list[EstadoCuentaPortal]:
        p = sesion.pagina
        p.eval_on_selector("#txtDatosDesde", f"e => e.value = '{_inicio_ejercicio(date.today()):%d-%m-%Y}'")
        p.check("input[name=tipoana][value=resumen]")
        p.get_by_role("button", name="Enviar datos").click()
        for _ in range(60):
            if "Totales al:" in p.inner_text("body"):
                break
            p.wait_for_timeout(1000)
        else:
            raise PortalCambio("Jáuregui y Morales no mostró el resumen de cuenta")
        texto = p.inner_text("body")
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

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes):
        return None

    def cerrar(self, sesion: _Sesion) -> None:
        sesion.browser.close()


registrar(ConectorJaureguiMorales())
