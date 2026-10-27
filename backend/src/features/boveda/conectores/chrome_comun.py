"""Conectores de Allianz y Movistar Empresas, con Chrome común (042).

Los dos rechazan un Chrome abierto en modo automatizado (Allianz con la
verificación de Cloudflare, Movistar con "ERROR 777"). Por eso se abre Chrome
como un programa común, con un perfil propio por cuenta guardado solo en esta
computadora, y el sistema se conecta después. La ventana queda visible mientras
dura la corrida.

Allianz: usuario, clave y el código que llega por mail (leído de Outlook, solo
lectura); cierra el aviso "Allianz con vos" con Cancelar (nunca acepta) y baja
la FACTURA de los endosos recientes con la API del propio portal. Movistar:
usuario y clave; baja la última factura con "Descargar factura" del inicio.
Ninguno usa pagar, débito automático ni otros trámites.
"""

from __future__ import annotations

import base64
import io
import os
import re
import socket
import subprocess
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DatosCompra, DocumentoPortal, PortalCambio, RequiereIntervencion, registrar,
)

# Perfiles de Chrome: solo en esta computadora (fuera del repositorio y de Dropbox). La carpeta de cada cuenta
# conserva el dispositivo reconocido, así el portal deja de pedir el código.
PERFILES = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LaHerencia" / "boveda-perfiles"
# Solo las facturas recientes: las anteriores ya se cargaron a mano.
DIAS_ATRAS = 60


@dataclass
class _Sesion:
    proceso: subprocess.Popen
    pagina: object
    datos: dict = field(default_factory=dict)


def _abrir_chrome(pw, perfil: Path, url: str) -> _Sesion:
    """Abre Chrome como un programa común (sin modo automatizado) y se conecta a él."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    chrome = next((r for r in (
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ) if r.is_file()), None)
    if not chrome:
        raise PortalCambio("Chrome no está instalado en esta computadora")
    perfil.mkdir(parents=True, exist_ok=True)
    proceso = subprocess.Popen([str(chrome), f"--user-data-dir={perfil}", f"--remote-debugging-port={puerto}",
                                "--remote-debugging-address=127.0.0.1", "--no-first-run",
                                "--no-default-browser-check", url])
    try:
        for _ in range(30):
            try:
                ctx = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{puerto}").contexts[0]
                break
            except Exception:
                time.sleep(1)
        else:
            raise PortalCambio("No se pudo abrir Chrome")
        for _ in range(30):
            if ctx.pages:
                return _Sesion(proceso=proceso, pagina=ctx.pages[0])
            time.sleep(1)
        raise PortalCambio("No se pudo abrir Chrome")
    except Exception:
        proceso.terminate()
        raise


def _verificando(p) -> bool:
    """Verificación anti-robots (Cloudflare) en pantalla."""
    try:
        return "challenges.cloudflare.com" in p.content() or "just a moment" in p.title().lower()
    except Exception:
        return True  # página cambiando


def _esperar(p, condicion, segundos: int, motivo: str) -> None:
    for _ in range(segundos):
        if condicion():
            return
        p.wait_for_timeout(1000)
    if _verificando(p):
        raise RequiereIntervencion("verificación anti-robots")
    raise PortalCambio(motivo)


def _completar_ingreso(p, cred: Credencial) -> None:
    usuario = p.locator("input[name=username]").first
    usuario.wait_for(timeout=60000)
    # Se tipea como una persona (Movistar valida al escribir). Antes se vacía: el perfil puede traer los campos
    # completos y se escribiría dos veces.
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
        try:
            if boton.count() and boton.is_visible() and boton.is_enabled():
                boton.click(timeout=5000)
        except Exception:
            pass  # el ingreso ya estaba en curso
    else:
        clave.press("Enter")


def _fecha_emision(pdf: bytes) -> date | None:
    """Fecha de emisión impresa en la factura (en Allianz el endoso trae la fecha de vigencia)."""
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(pdf)) as d:
            m = re.search(r"Fecha (?:de )?[Ee]misi[oó]n:?\s*(\d{2}/\d{2}/\d{4})", d.pages[0].extract_text() or "")
        return datetime.strptime(m.group(1), "%d/%m/%Y").date() if m else None
    except Exception:
        return None


def _importe(t: str) -> Decimal:
    return Decimal(t.replace(".", "").replace(",", "."))


def _texto(pdf: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf)) as d:
        return "\n".join(p.extract_text() or "" for p in d.pages)


# Imputación igual a la de las facturas cargadas a mano.
CENTRO_COSTO = 3
DESTINO = 1
CAMPANIA = "No Aplica"


def _cabecera(id_contacto: int, fecha: date, numero: str, **importes) -> dict:
    from src.features.compras import repository as compras

    cabecera = {"idContacto": id_contacto, "fecha": fecha.isoformat(), "tipo": "A", "tipoDocumento": "Factura",
                "numeroDocumento": numero, "moneda": "Pesos", "tipoDeCambio": 1.0, "ajustaTipoCambio": False}
    for campo in compras.CAMPOS_IMPORTE_CABECERA:
        cabecera[campo] = float(importes.get(campo, 0))
    return cabecera


def _linea(descripcion: str, precio: Decimal, iva: float, id_rubro: int, unidad: str = "UNIDAD") -> dict:
    return {"productoServicio": descripcion[:50], "cantidad": 1.0, "precioUnitario": float(precio), "iva": iva,
            "unidad": unidad, "idCentroCosto": CENTRO_COSTO, "idDestino": DESTINO, "idRubro": id_rubro,
            "campaña": CAMPANIA, "ajusteFinanciero": False}


class _ChromeComun:
    tiene_estado_cuenta = False
    tiene_carga_compras = True
    mapeo_proveedores: dict = {}
    id_portal: int

    def estado_cuenta(self, sesion: _Sesion) -> list:
        return []

    def cerrar(self, sesion: _Sesion) -> None:
        if sesion.proceso.poll() is None:
            sesion.proceso.terminate()


# ---------------------------------------------------------------- Allianz

ALLIANZ = "https://www.miallianz.com.ar/priv"  # el login directo deja en la página pública
ALLIANZ_CONTACTO = 515
ALLIANZ_RUBRO = 2047893444


def _monto(texto: str, concepto: str) -> Decimal:
    m = re.search(concepto + r"[ .]*\.{3,}\s*([\d.]+,\d{2})", texto)
    return _importe(m.group(1)) if m else Decimal(0)


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


class ConectorAllianz(_ChromeComun):
    codigo = "allianz"
    nombre = "Allianz"
    id_portal = 11

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        from src.features.boveda.mails import esperar_codigo

        s = _abrir_chrome(pw, PERFILES / str(self.id_portal), ALLIANZ)
        try:
            p = s.pagina
            pedido = datetime.now()
            adentro = lambda: "miallianz.com.ar/priv" in p.url and not _verificando(p)
            formulario = lambda: p.locator("input[type=password]").count() > 0 and not _verificando(p)
            _esperar(p, lambda: adentro() or formulario(), 120, "No apareció el ingreso de Allianz")
            if not adentro():
                _completar_ingreso(p, credencial)
                codigo = lambda: p.locator("input[name=code]").count() > 0
                _esperar(p, lambda: codigo() or "auth.allianz" not in p.url, 120, "Allianz no respondió al ingreso")
                if codigo():
                    p.fill("input[name=code]", esperar_codigo("noreply@allianz.com.ar", r"Tu código es (\d{6})",
                                                              pedido))
                    p.locator("button[type=submit], #btnConfirm").first.click()
                _esperar(p, lambda: "auth.allianz" not in p.url, 120, "Allianz no completó el ingreso")
                if "/login" in p.url or p.locator("input[type=password]").count():
                    raise CredencialesRechazadas("Allianz rechazó usuario o contraseña")
                if "miallianz.com.ar/priv" not in p.url:
                    p.goto(ALLIANZ, wait_until="load", timeout=90000)
            for _ in range(20):  # el aviso aparece varios segundos después de cargar la página
                if _cancelar_aviso(p):
                    break
                p.wait_for_timeout(1000)
            return s
        except Exception:
            self.cerrar(s)
            raise

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        p = sesion.pagina
        usuario = p.evaluate("fetch('/private/user').then(r => r.json())")
        docu = usuario["result"]["user"]["details"]["identityDocuments"][0]
        nro_doc = docu["documentType"]["documentTypeCode"] + docu["documentNumber"]
        res = p.evaluate("u => fetch(u).then(r => r.json())",
                         f"/api/mi-allianz/private/policies?docNumber={nro_doc}&validity=S&pageLines=50&currentPage=1")
        desde = date.today() - timedelta(days=DIAS_ATRAS)
        docs = []
        for bloque in res.get("PolizaAseguradoOut") or []:
            for pol in bloque.get("polizas") or []:
                for e in pol.get("polizasEndosos") or []:
                    vigencia = datetime.strptime(e["fecha"][:10], "%Y-%m-%d").date()
                    if e.get("tieneFactura") != "S" or vigencia < desde:
                        continue
                    url = (f"/api/mi-allianz/private/pdf/parte?nroPoliza={e['poliza']}&endoso={e['endoso']}"
                           f"&partePoliza=FACTURA&item={pol.get('item') or 1}")
                    doc = DocumentoPortal(
                        clave=f"allianz:{e['poliza']}:{e['endoso']}", fecha=vigencia, tipo="factura",
                        proveedor="Allianz", bajar=lambda: b"",
                        numero=f"{e['poliza']} {e['endoso']}",  # como se cargan a mano en Compras
                        moneda="ARS", id_contacto=ALLIANZ_CONTACTO,
                        detalle=f"Póliza {e['poliza']} endoso {e['endoso']} - {pol.get('detalleSecundario') or ''}")
                    doc.bajar = self._bajador(p, url, doc)
                    docs.append(doc)
        return docs

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes) -> DatosCompra | None:
        """Como se cargan a mano: Prima con IVA 21%, OSSEG, Tasa SSN y Contribución Vial sin IVA, percepción de
        IVA y sellos en la cabecera, y "Seguro particular" en negativo por el total (la TAOS es de uso
        particular: la factura queda en cero)."""
        t = _texto(pdf)
        m = re.search(r"FACTURA A:\s*(\d{4}-\d{8})", t)
        fecha = _fecha_emision(pdf)
        premio = _monto(t, "Premio")
        if not (m and fecha and premio):
            return None
        prima = _monto(t, "Prima")
        sin_iva = [(c, _monto(t, patron)) for c, patron in
                   (("OSSEG", "OSSEG"), ("Tasa SSN", "Tasa SSN"), ("Contribucion Vial", "Contribuci[oó]n Vial"),
                    ("Recargo Financiero", "Recargo Financiero"), ("Impuestos Internos", "Impuestos Internos"))]
        percepcion_iva = _monto(t, r"I\.V\.A\. Percepci[oó]n \(\d+%\)")
        ingresos_brutos = _monto(t, r"II\.BB\. Percepci[oó]n \(seg[uú]n detalle\)")
        sellos = _monto(t, "Sellos")
        lineas = [_linea("Prima", prima, 21.0, ALLIANZ_RUBRO, "POLIZA")]
        lineas += [_linea(c, v, 0.0, ALLIANZ_RUBRO) for c, v in sin_iva if v]
        lineas.append(_linea("Seguro particular", -premio, 0.0, ALLIANZ_RUBRO))
        cabecera = _cabecera(ALLIANZ_CONTACTO, fecha, documento.numero, percepcionIva=percepcion_iva,
                             ingresosBrutos=ingresos_brutos, leyDeSellos=sellos)
        return DatosCompra(cabecera=cabecera, lineas=lineas, numero=documento.numero, total_impreso=Decimal(0))

    @staticmethod
    def _bajador(p, url: str, doc: DocumentoPortal):
        def bajar() -> bytes:
            b64 = p.evaluate("""u => fetch(u).then(r => r.ok ? r.arrayBuffer() : null).then(b => {
                if (!b) return null;
                let s = ''; const a = new Uint8Array(b);
                for (let i = 0; i < a.length; i += 32768) s += String.fromCharCode(...a.subarray(i, i + 32768));
                return btoa(s);
            })""", url)
            if not b64:
                raise PortalCambio("Allianz no entregó la factura")
            pdf = base64.b64decode(b64)
            doc.fecha = _fecha_emision(pdf) or doc.fecha
            return pdf
        return bajar


# ---------------------------------------------------------------- Movistar

MOVISTAR_LOGIN = "https://idp.movistar.com.ar/convergencia/login_A.html"
MOVISTAR = "mimovistarempresas.movistar.com.ar"
MOVISTAR_CONTACTO = 71
MOVISTAR_RUBRO = 21


class ConectorMovistar(_ChromeComun):
    codigo = "movistar"
    nombre = "Movistar Empresas"
    id_portal = 19

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        s = _abrir_chrome(pw, PERFILES / str(self.id_portal), MOVISTAR_LOGIN)
        try:
            p = s.pagina
            formulario = lambda: p.locator("input[type=password]").count() > 0
            _esperar(p, lambda: MOVISTAR in p.url or formulario(), 90, "No apareció el ingreso de Movistar")
            if MOVISTAR not in p.url:
                _completar_ingreso(p, credencial)
                for _ in range(60):
                    if MOVISTAR in p.url:
                        break
                    if re.search(r"ERROR\s*777", p.inner_text("body")):
                        raise RequiereIntervencion("Movistar rechazó el ingreso automático (ERROR 777)")
                    # Elección de "Movistar Empresas" después del ingreso, cuando el portal la pide.
                    opcion = p.get_by_text("Movistar Empresas", exact=True)
                    if opcion.count() and opcion.first.is_visible():
                        opcion.first.click()
                    p.wait_for_timeout(1000)
                else:
                    if formulario():
                        raise CredencialesRechazadas("Movistar rechazó usuario o contraseña")
                    raise PortalCambio("Movistar no completó el ingreso")
            return s
        except Exception:
            self.cerrar(s)
            raise

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        """La última factura del inicio. El número recién se conoce al pedirla, así que se baja acá."""
        p = sesion.pagina
        boton = p.get_by_text("Descargar factura", exact=True).first
        boton.wait_for(timeout=60000)
        ids: list[str] = []
        p.on("request", lambda r: ids.extend(re.findall(r"factura-digital/pdf/.*[?&]id=FA-([\d-]+)", r.url)))
        with p.expect_download(timeout=60000) as espera:
            boton.evaluate("e => (e.closest('button,a') || e).click()")
        pdf = Path(espera.value.path()).read_bytes()
        if not ids:
            raise PortalCambio("No se encontró el número de la factura de Movistar")
        return [DocumentoPortal(clave=f"movistar:{ids[-1]}", fecha=_fecha_emision(pdf), tipo="factura",
                                proveedor="Movistar", bajar=lambda: pdf, numero=ids[-1], moneda="ARS",
                                id_contacto=MOVISTAR_CONTACTO, detalle=f"Factura {ids[-1]}")]

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes) -> DatosCompra | None:
        """Como se cargan a mano: un renglón por línea ("Tel. movil <línea> - <período>") con su total sin
        impuestos e IVA 27%, y la percepción de IVA en la cabecera."""
        t = _texto(pdf)
        numero = re.search(r"Factura (\d{4}-\d{8})", t)
        fecha = _fecha_emision(pdf)
        total = re.search(r"Total a Pagar \$([\d.]+,\d{2})", t)
        periodo = re.search(r"PLANES Y SERVICIOS (\d{2})/(\d{2}) al (\d{2})/(\d{2})", t)
        if not (numero and fecha and total and periodo):
            return None
        d1, m1, d2, m2 = periodo.groups()
        anio_fin = fecha.year + (1 if int(m2) < int(m1) else 0)
        texto_periodo = f"{d1}/{m1} al {d2}/{m2}/{anio_fin}"
        lineas = [_linea(f"Tel. movil {linea} - {texto_periodo}", _importe(importe), 27.0, MOVISTAR_RUBRO)
                  for linea, importe in re.findall(
                      r"Anexo: Linea \((\d+)\).*?Total TELEFONIA MOVIL ([\d.]+,\d{2})", t, re.S)]
        if not lineas:
            return None
        percepcion = re.search(r"Percepci[oó]n I\.V\.A\. [\d.]+,\d{2} [\d,]+ ([\d.]+,\d{2})", t)
        cabecera = _cabecera(MOVISTAR_CONTACTO, fecha, numero.group(1),
                             percepcionIva=_importe(percepcion.group(1)) if percepcion else 0)
        return DatosCompra(cabecera=cabecera, lineas=lineas, numero=numero.group(1),
                           total_impreso=_importe(total.group(1)))


registrar(ConectorAllianz())
registrar(ConectorMovistar())
