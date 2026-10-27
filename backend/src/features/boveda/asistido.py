"""Ingreso asistido a portales que no aceptan un navegador automático (042).

Allianz (código por mail y verificación anti-robots) y Movistar Empresas
(rechaza el navegador automático con "ERROR 777"). El sistema abre una ventana
de Chrome visible en esta computadora, completa usuario y clave y, si el portal
lo pide, el código que llega por mail (leído de Outlook). Las verificaciones
humanas las pasa Sergio. Cada archivo que se descarga en esa ventana se guarda
en la carpeta de Compras del ejercicio y queda registrado en la cuenta, sin
duplicar. La ventana se cierra sola a los 30 minutos.

Solo completa el formulario de ingreso y el del código: no hace clic en ninguna
otra cosa del portal.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

from src.features.boveda import carga, repository

log = logging.getLogger(__name__)

DURACION_MAXIMA = 30 * 60


@dataclass(frozen=True)
class Asistido:
    login: str
    proveedor: str  # parte del nombre AAAAMMDD_Proveedor.pdf
    codigo_remitente: str | None = None
    codigo_patron: str | None = None
    # Movistar rechaza ("ERROR 777") un ingreso tipeado por el sistema: ahí el usuario y la clave los escribe Sergio.
    completar: bool = True


ASISTIDOS = {
    "auth.allianz.com.ar": Asistido("https://auth.allianz.com.ar/login", "Allianz",
                                    "noreply@allianz.com.ar", r"Tu código es (\d{6})"),
    "idp.movistar.com.ar": Asistido("https://idp.movistar.com.ar/convergencia/login_A.html", "Movistar", completar=False),
}

_abiertos: set[int] = set()
_candado = threading.Lock()


class SinCodigo(Exception):
    """No llegó el mail con el código a tiempo."""


def asistido_de(url: str | None) -> Asistido | None:
    return ASISTIDOS.get(urlparse(url or "").hostname or "")


def abierto(id_portal: int) -> bool:
    return id_portal in _abiertos


def esperar_codigo(remitente: str, patron: str, desde: datetime, espera_segundos: int = 180) -> str:
    """Primer grupo de `patron` (en asunto y cuerpo) del mail de `remitente` recibido después de `desde` (hora
    local; pywin32 entrega la hora local de Outlook rotulada UTC). Solo lectura: no marca, mueve ni borra."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        regex = re.compile(patron)
        limite = time.monotonic() + espera_segundos
        desde = desde - timedelta(seconds=30)  # tolerancia de reloj
        while time.monotonic() < limite:
            ns.SendAndReceive(False)  # Gmail en Outlook sincroniza cada varios minutos: se fuerza la descarga
            time.sleep(10)
            for store in ns.Stores:
                try:
                    items = store.GetDefaultFolder(6).Items  # 6 = Bandeja de entrada
                    items.Sort("[ReceivedTime]", True)
                except Exception:
                    continue
                for i, m in enumerate(items):
                    if i >= 20:
                        break
                    try:
                        if m.ReceivedTime.replace(tzinfo=None) < desde:
                            break
                        if (m.SenderEmailAddress or "").lower() != remitente.lower():
                            continue
                        encontrado = regex.search(f"{m.Subject}\n{m.Body}")
                        if encontrado:
                            return encontrado.group(1)
                    except Exception:
                        continue
        raise SinCodigo(f"No llegó el código de {remitente}")
    finally:
        pythoncom.CoUninitialize()


def iniciar(portal: dict, usuario: str | None) -> bool:
    """Abre la ventana asistida en segundo plano. False si ya hay una abierta para ese portal."""
    with _candado:
        if portal["idPortal"] in _abiertos:
            return False
        _abiertos.add(portal["idPortal"])
    threading.Thread(target=_sesion, args=(portal, usuario), daemon=True, name=f"asistido-{portal['idPortal']}").start()
    return True


def _sesion(portal: dict, usuario: str | None) -> None:
    from playwright.sync_api import sync_playwright

    from src.features.boveda import servicio

    id_portal = portal["idPortal"]
    datos = asistido_de(portal["url"])
    repository.auditar("ingreso_asistido", usuario, id_portal=id_portal, detalle="apertura")
    try:
        cred = servicio.credencial_de(portal["idCredencial"])
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=False)
            ctx = browser.new_context(accept_downloads=True, no_viewport=True)
            ctx.on("download", lambda d: _guardar_descarga(portal, datos, d))
            p = ctx.new_page()
            p.goto(datos.login, wait_until="load", timeout=90000)
            pedido = datetime.now()
            if datos.completar:
                _completar_ingreso(p, cred)
            if datos.codigo_remitente:
                p.wait_for_selector("input[name=code]", timeout=60000)
                p.fill("input[name=code]", esperar_codigo(datos.codigo_remitente, datos.codigo_patron, pedido))
                p.locator("button[type=submit], #btnConfirm").first.click()
            limite = time.monotonic() + DURACION_MAXIMA
            while browser.is_connected() and ctx.pages and time.monotonic() < limite:
                ctx.pages[0].wait_for_timeout(2000)
            if browser.is_connected():
                browser.close()
    except Exception:
        log.warning("Bóveda, ingreso asistido portal %s", id_portal, exc_info=True)
    finally:
        _abiertos.discard(id_portal)
        repository.auditar("ingreso_asistido", usuario, id_portal=id_portal, detalle="cierre")


def _completar_ingreso(p, cred) -> None:
    usuario = p.locator("input[name=username]").first
    usuario.wait_for(timeout=60000)
    # Se tipea como una persona: algunos portales (Movistar) validan los campos al escribir.
    usuario.press_sequentially(cred.usuario or "", delay=50)
    clave = p.locator("input[type=password]").first
    clave.press_sequentially(cred.clave.valor() if cred.clave else "", delay=50)
    boton = p.locator("#btn-enviar")
    if boton.count():
        boton.click()
    else:
        clave.press("Enter")


def _guardar_descarga(portal: dict, datos: Asistido, descarga) -> None:
    """Guarda lo que Sergio baja en la ventana: carpeta de Compras del ejercicio y registro en la cuenta."""
    from src.features.boveda import servicio

    try:
        contenido = open(descarga.path(), "rb").read()
        sha = hashlib.sha256(contenido).hexdigest()
        clave = f"asistido:{sha}"
        if repository.existe_documento(portal["idPortal"], clave):
            return
        hoy = date.today()
        carpeta = servicio._carpeta("factura", hoy)
        ruta = repository.existe_sha(sha) or servicio._archivo_igual(carpeta, sha, {})
        if not ruta:
            destino = servicio._destino(carpeta, hoy, datos.proveedor)
            if not contenido.startswith(b"%PDF"):
                destino = destino.with_suffix(f".{descarga.suggested_filename.rsplit('.', 1)[-1][:5]}")
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(contenido)
            ruta = str(destino)
        doc = _Doc(clave=clave, fecha=hoy, tipo="factura", proveedor=datos.proveedor,
                   detalle=descarga.suggested_filename[:200], id_contacto=portal["idContacto"])
        r = carga.cargar(_SinLector(), doc, contenido, ruta)
        repository.insertar_documento({"idPortal": portal["idPortal"], "clave": clave, "tipo": "factura",
                                       "proveedor": datos.proveedor, "idContacto": portal["idContacto"], "fecha": hoy,
                                       "moneda": "ARS", "ruta": ruta, "sha256": sha, **r})
    except Exception:
        log.warning("Bóveda, descarga asistida portal %s", portal["idPortal"], exc_info=True)


@dataclass
class _Doc:
    clave: str
    fecha: date
    tipo: str
    proveedor: str
    detalle: str
    id_contacto: int | None
    numero: str | None = None
    total: object = None
    moneda: str = "ARS"


class _SinLector:
    tiene_carga_compras = False
