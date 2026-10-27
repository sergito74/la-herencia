"""Ingreso asistido a portales que no aceptan un navegador automático (042).

Allianz (código por mail y verificación anti-robots) y Movistar Empresas
(rechaza el navegador automático con "ERROR 777"). El sistema abre una ventana
de Chrome visible en esta computadora, completa usuario y clave y, si el portal
lo pide, el código que llega por mail (leído de Outlook). Las verificaciones
humanas las pasa Sergio. Cada archivo que se descarga en esa ventana se guarda
en la carpeta de Compras del ejercicio y queda registrado en la cuenta, sin
duplicar. La ventana se cierra sola a los 30 minutos.

Solo completa el formulario de ingreso y el del código, y en Allianz cierra el
aviso de marketing con "Cancelar": no hace clic en ninguna otra cosa del portal.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from src.features.boveda import carga, repository

log = logging.getLogger(__name__)

DURACION_MAXIMA = 30 * 60
# Perfiles de Chrome de las ventanas asistidas: solo en esta computadora (fuera del repositorio y de Dropbox).
PERFILES = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LaHerencia" / "boveda-perfiles"


@dataclass(frozen=True)
class Asistido:
    login: str
    proveedor: str  # parte del nombre AAAAMMDD_Proveedor.pdf
    codigo_remitente: str | None = None
    codigo_patron: str | None = None
    # False: el usuario y la clave los escribe Sergio (Movistar daba "ERROR 777" en modo automatizado; con chrome_comun
    # se vuelve a probar el ingreso completo).
    completar: bool = True
    # Página de clientes donde aparece un aviso de marketing que se descarta con "Cancelar".
    inicio: str | None = None
    # Allianz (Cloudflare) devuelve siempre a la verificación si Chrome se abre en modo automatizado: se abre un
    # Chrome común y el sistema se conecta después, cuando Sergio ya pasó la verificación.
    chrome_comun: bool = False
    # Ya adentro, baja solo los documentos nuevos: (página, portal, datos).
    bajar: object = None


ASISTIDOS = {
    # Se entra por la página de clientes: el login directo deja en la página pública (www.allianz.com.ar).
    "auth.allianz.com.ar": Asistido("https://www.miallianz.com.ar/priv", "Allianz",
                                    "noreply@allianz.com.ar", r"Tu código es (\d{6})",
                                    inicio="miallianz.com.ar/priv", chrome_comun=True,
                                    bajar=lambda *a: _bajar_allianz(*a)),
    "idp.movistar.com.ar": Asistido("https://idp.movistar.com.ar/convergencia/login_A.html", "Movistar", chrome_comun=True,
                                    bajar=lambda *a: _bajar_movistar(*a)),
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
    proceso = None
    try:
        cred = servicio.credencial_de(portal["idCredencial"])
        with sync_playwright() as pw:
            # Perfil propio y persistente por cuenta: el portal reconoce el dispositivo después del primer
            # ingreso (como el Chrome de Sergio) y deja de pedir el código.
            perfil = PERFILES / str(id_portal)
            perfil.mkdir(parents=True, exist_ok=True)
            if datos.chrome_comun:
                proceso, ctx = _chrome_comun(pw, perfil, datos.login)
                p = ctx.pages[0]
            else:
                ctx = pw.chromium.launch_persistent_context(str(perfil), channel="chrome", headless=False,
                                                            accept_downloads=True, no_viewport=True)
                p = ctx.pages[0] if ctx.pages else ctx.new_page()
                p.goto(datos.login, wait_until="load", timeout=90000)
            ctx.on("download", lambda d: _guardar_descarga(portal, datos, d))
            pedido = datetime.now()
            if datos.completar and _esperar_formulario(p):
                _completar_ingreso(p, cred)
                if datos.codigo_remitente and _pide_codigo(p):
                    p.fill("input[name=code]", esperar_codigo(datos.codigo_remitente, datos.codigo_patron, pedido))
                    p.locator("button[type=submit], #btnConfirm").first.click()
            if datos.inicio:  # también si la sesión ya estaba abierta
                _rechazar_aviso(p, datos.inicio)
            if datos.bajar:
                try:
                    datos.bajar(p, portal, datos)
                except Exception:
                    log.warning("Bóveda, descarga automática portal %s", id_portal, exc_info=True)
            limite = time.monotonic() + DURACION_MAXIMA
            while ctx.pages and time.monotonic() < limite:
                ctx.pages[0].wait_for_timeout(2000)
                if datos.inicio:
                    _cancelar_aviso(ctx.pages[0])  # el aviso aparece tarde o al volver a la página de clientes
            ctx.close()
    except Exception:
        log.warning("Bóveda, ingreso asistido portal %s", id_portal, exc_info=True)
    finally:
        if proceso and proceso.poll() is None:
            proceso.terminate()
        _abiertos.discard(id_portal)
        repository.auditar("ingreso_asistido", usuario, id_portal=id_portal, detalle="cierre")


def _chrome_comun(pw, perfil: Path, url: str):
    """Abre Chrome como un programa común (sin modo automatizado) y se conecta a él."""
    import socket
    import subprocess

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    chrome = next((r for r in (
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ) if r.is_file()), None)
    if not chrome:
        raise FileNotFoundError("Chrome no está instalado")
    proceso = subprocess.Popen([str(chrome), f"--user-data-dir={perfil}", f"--remote-debugging-port={puerto}",
                                "--remote-debugging-address=127.0.0.1", "--no-first-run",
                                "--no-default-browser-check", url])
    for _ in range(30):
        try:
            navegador = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{puerto}")
            break
        except Exception:
            time.sleep(1)
    else:
        raise TimeoutError("No se pudo conectar con Chrome")
    ctx = navegador.contexts[0]
    for _ in range(30):
        if ctx.pages:
            break
        time.sleep(1)
    return proceso, ctx


def _verificando(p) -> bool:
    """Verificación anti-robots (Cloudflare) en pantalla: la pasa Sergio, el sistema solo espera."""
    try:
        return "challenges.cloudflare.com" in p.content() or "just a moment" in p.title().lower()
    except Exception:
        return True  # página cambiando


def _esperar_formulario(p, espera_segundos: int = 300) -> bool:
    """Espera el formulario de ingreso, dando tiempo a que Sergio pase la verificación si aparece."""
    for _ in range(espera_segundos):
        if p.locator("input[type=password]").count() and not _verificando(p):
            return True
        p.wait_for_timeout(1000)
    return False


def _pide_codigo(p, espera_segundos: int = 300) -> bool:
    """Después del ingreso, el portal pide el código o entra directo (dispositivo ya conocido)."""
    for _ in range(espera_segundos):
        if p.locator("input[name=code]").count():
            return True
        if _verificando(p):
            p.wait_for_timeout(1000)
            continue
        if "/login" not in p.url and "/2fa" not in p.url:
            return False
        p.wait_for_timeout(1000)
    return False


def _rechazar_aviso(p, inicio: str, espera_segundos: int = 300) -> None:
    """Al llegar a la página de clientes, cierra el aviso de marketing con "Cancelar" (nunca acepta)."""
    try:
        p.wait_for_url(lambda u: "auth.allianz" not in u, timeout=espera_segundos * 1000)
        if inicio not in p.url:  # quedó en otro lugar del portal
            p.goto(f"https://www.{inicio}", wait_until="load", timeout=90000)
        # El aviso aparece varios segundos después de cargar la página.
        for _ in range(30):
            if _cancelar_aviso(p):
                return
            p.wait_for_timeout(1000)
    except Exception:
        pass  # sin aviso: Sergio sigue normalmente


def _cancelar_aviso(p) -> bool:
    """Si el aviso de marketing está en pantalla, lo cierra con "Cancelar" (nunca acepta)."""
    try:
        return bool(p.evaluate("""() => {
            const b = [...document.querySelectorAll('.cdk-overlay-container button')]
                .find(b => b.innerText.trim() === 'Cancelar');
            if (b) b.click();
            return !!b;
        }"""))
    except Exception:
        return False


def _completar_ingreso(p, cred) -> None:
    usuario = p.locator("input[name=username]").first
    usuario.wait_for(timeout=60000)
    # Se tipea como una persona: algunos portales (Movistar) validan los campos al escribir.
    # Antes se vacía: el perfil persistente puede traer los campos ya completos y se escribiría dos veces.
    usuario.clear()
    usuario.press_sequentially(cred.usuario or "", delay=50)
    clave = p.locator("input[type=password]").first
    clave.clear()
    clave.press_sequentially(cred.clave.valor() if cred.clave else "", delay=50)
    boton = p.locator("#btn-enviar")
    if boton.count():
        boton.click()
        # Movistar a veces ignora el primer clic (la página todavía está terminando de cargar).
        p.wait_for_timeout(8000)
        if boton.count() and boton.is_visible():
            boton.click()
    else:
        clave.press("Enter")


def _guardar_descarga(portal: dict, datos: Asistido, descarga) -> None:
    """Guarda lo que Sergio baja en la ventana: carpeta de Compras del ejercicio y registro en la cuenta."""
    if portal["idPortal"] in _automaticas:
        return
    try:
        contenido = open(descarga.path(), "rb").read()
        _registrar(portal, datos, contenido, f"asistido:{hashlib.sha256(contenido).hexdigest()}", date.today(),
                   descarga.suggested_filename)
    except Exception:
        log.warning("Bóveda, descarga asistida portal %s", portal["idPortal"], exc_info=True)


def _registrar(portal: dict, datos: Asistido, contenido: bytes, clave: str, fecha: date, detalle: str,
               numero: str | None = None) -> None:
    from src.features.boveda import servicio

    sha = hashlib.sha256(contenido).hexdigest()
    if repository.existe_documento(portal["idPortal"], clave) or \
            repository.existe_documento(portal["idPortal"], f"asistido:{sha}"):
        return
    carpeta = servicio._carpeta("factura", fecha)
    ruta = repository.existe_sha(sha) or servicio._archivo_igual(carpeta, sha, {})
    if not ruta:
        destino = servicio._destino(carpeta, fecha, datos.proveedor)
        if not contenido.startswith(b"%PDF"):
            destino = destino.with_suffix(f".{detalle.rsplit('.', 1)[-1][:5]}")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
        ruta = str(destino)
    doc = _Doc(clave=clave, fecha=fecha, tipo="factura", proveedor=datos.proveedor,
               detalle=detalle[:200], id_contacto=portal["idContacto"], numero=numero)
    r = carga.cargar(_SinLector(), doc, contenido, ruta)
    repository.insertar_documento({"idPortal": portal["idPortal"], "clave": clave, "tipo": "factura",
                                   "proveedor": datos.proveedor, "idContacto": portal["idContacto"], "fecha": fecha,
                                   "moneda": "ARS", "ruta": ruta, "sha256": sha, **r})


# Solo las facturas recientes: las anteriores ya se cargaron a mano.
DIAS_ATRAS = 60


def _bajar_allianz(p, portal: dict, datos: Asistido) -> None:
    """Facturas de los endosos recientes de las pólizas vigentes (API del propio portal, con la sesión abierta)."""
    import base64

    usuario = p.evaluate("fetch('/private/user').then(r => r.json())")
    docu = usuario["result"]["user"]["details"]["identityDocuments"][0]
    nro_doc = docu["documentType"]["documentTypeCode"] + docu["documentNumber"]
    res = p.evaluate("u => fetch(u).then(r => r.json())",
                     f"/api/mi-allianz/private/policies?docNumber={nro_doc}&validity=S&pageLines=50&currentPage=1")
    desde = date.today() - timedelta(days=DIAS_ATRAS)
    for bloque in res.get("PolizaAseguradoOut") or []:
        for pol in bloque.get("polizas") or []:
            for e in pol.get("polizasEndosos") or []:
                fecha = datetime.strptime(e["fecha"][:10], "%Y-%m-%d").date()
                if e.get("tieneFactura") != "S" or fecha < desde:
                    continue
                clave = f"allianz:{e['poliza']}:{e['endoso']}"
                numero = f"{e['poliza']} {e['endoso']}"  # como se cargan a mano en Compras
                if repository.existe_documento(portal["idPortal"], clave) or \
                        repository.compra_existente(portal["idContacto"], numero, None):
                    continue
                url = (f"/api/mi-allianz/private/pdf/parte?nroPoliza={e['poliza']}&endoso={e['endoso']}"
                       f"&partePoliza=FACTURA&item={pol.get('item') or 1}")
                b64 = p.evaluate("""u => fetch(u).then(r => r.ok ? r.arrayBuffer() : null).then(b => {
                    if (!b) return null;
                    let s = ''; const a = new Uint8Array(b);
                    for (let i = 0; i < a.length; i += 32768) s += String.fromCharCode(...a.subarray(i, i + 32768));
                    return btoa(s);
                })""", url)
                if b64:
                    pdf = base64.b64decode(b64)
                    _registrar(portal, datos, pdf, clave, _fecha_emision(pdf) or fecha,
                               f"Póliza {e['poliza']} endoso {e['endoso']} - {pol.get('detalleSecundario') or ''}",
                               numero)


MOVISTAR = "mimovistarempresas.movistar.com.ar"


def _bajar_movistar(p, portal: dict, datos: Asistido) -> None:
    """Última factura del inicio de Mi Movistar Empresas ("Descargar factura"), si no está cargada en Compras."""
    if MOVISTAR not in p.url:
        # Elección de "Movistar Empresas" después del ingreso, cuando el portal la pide.
        for _ in range(30):
            if MOVISTAR in p.url:
                break
            opcion = p.get_by_text("Movistar Empresas", exact=True)
            if opcion.count():
                opcion.first.click()
            p.wait_for_timeout(1000)
    boton = p.get_by_text("Descargar factura", exact=True).first
    boton.wait_for(timeout=60000)
    ids: list[str] = []
    p.on("request", lambda r: ids.extend(re.findall(r"factura-digital/pdf/.*[?&]id=FA-([\d-]+)", r.url)))
    _automaticas.add(portal["idPortal"])  # la descarga la registra esta función, no la de la ventana
    try:
        with p.expect_download(timeout=60000) as espera:
            boton.evaluate("e => (e.closest('button,a') || e).click()")
        contenido = open(espera.value.path(), "rb").read()
    finally:
        _automaticas.discard(portal["idPortal"])
    numero = ids[-1] if ids else None
    if numero and repository.compra_existente(portal["idContacto"], numero, None):
        return
    _registrar(portal, datos, contenido, f"movistar:{numero or hashlib.sha256(contenido).hexdigest()}",
               _fecha_emision(contenido) or date.today(), espera.value.suggested_filename, numero)


_automaticas: set[int] = set()


def _fecha_emision(pdf: bytes) -> date | None:
    """Fecha de emisión impresa en la factura (Allianz: el endoso trae la fecha de vigencia, no la de emisión)."""
    import io

    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(pdf)) as d:
            m = re.search(r"Fecha (?:de )?[Ee]misi[oó]n:?\s*(\d{2}/\d{2}/\d{4})", d.pages[0].extract_text() or "")
        return datetime.strptime(m.group(1), "%d/%m/%Y").date() if m else None
    except Exception:
        return None


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
