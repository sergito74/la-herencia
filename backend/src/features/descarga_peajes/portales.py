"""Acceso a los portales de peaje (037). Solo lectura y descarga, autorizado
por Sergio el 2026-10-16: no se paga, no se modifica nada y no se acepta nada.

Cada portal expone `listar(pw) -> (documentos, contexto, avisos)`, donde cada
documento es un dict con `clave` (identificador estable en el portal, la
misma que usaba el script anterior), `fecha`, `proveedor` (nombre estándar
del archivo), `idContacto` (proveedor en Compras), `detalle` y `bajar()`
(devuelve los bytes del PDF). Relevamiento de los portales en research.md.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from src.features.descarga_peajes.configuracion import credencial

COMPRAS = Path.home() / "Dropbox" / "Giamigli de Bolivar SA" / "Compras"

TP = "https://www.telepeajeplus.com/Login/"
TS = "https://telepase.com.ar/"
CONTRATO_TP = "1345207"
LOGIN_CEAMSE = "https://ceamse.sixon.com.ar/CEAMSE_OFICINA_VIRTUAL_PROD/com.ceamseoficinavirtual.login"
LOGIN_AUBASA = "https://autogestionaubasa.com.ar/AUBASA_OFICINA_VIRTUAL_PROD/servlet/com.aubasaoficinavirtual.login"
TIMEOUT_MS = 60000

# Nombre estándar de archivo → proveedor en Compras (data-model.md).
CONTACTOS = {
    "Telepeaje": 328, "CorredoresViales": 436, "Corresur": 2657, "CV5": 2658, "AutopistasDelSol": 276,
    "GrupoConcesionarioDelOeste": 306, "AUSA": 380, "Ceamse": 314, "AUBASA": 316,
}
# Las 7 concesionarias del filtro de TelePASE (todas se bajan, pedido de Sergio 2026-10-16).
# Rosario-Santa Fe y Del Mercosur no tienen contacto en Compras: se bajan y quedan pendientes.
NOMBRES_TS = {
    "ACCESO NORTE": "AutopistasDelSol", "ACCESO OESTE": "GrupoConcesionarioDelOeste",
    "AUTOPISTAS URBANAS": "AUSA", "ACCESO RICCHERI": "CorredoresViales",
    "AU. BS AS - LA PLATA": "AUBASA", "AU. ROSARIO - SANTA FE": "AutopistaRosarioSantaFe",
    "AU. DEL MERCOSUR": "AutopistaDelMercosur",
}
NOMBRES_TP = [("CVSA", "CorredoresViales"), ("CORRESUR", "Corresur"), ("PENTAVIA", "CV5")]


class ErrorPortal(Exception):
    """Falla legible de un portal (se muestra tal cual en la pantalla)."""


def carpeta_ejercicio(d: date) -> Path:
    inicio = d.year if d.month >= 4 else d.year - 1
    return COMPRAS / f"04 {inicio} - 03 {inicio + 1}"


def destino_libre(d: date, proveedor: str) -> Path:
    """Nombre estándar `AAAAMMDD_Proveedor.pdf`; si existe, " 001", " 002"... Nunca pisa un archivo."""
    carpeta = carpeta_ejercicio(d)
    base = f"{d:%Y%m%d}_{proveedor}"
    ruta = carpeta / f"{base}.pdf"
    if not ruta.exists():
        return ruta
    n = 1
    while (carpeta / f"{base} {n:03d}.pdf").exists():
        n += 1
    return carpeta / f"{base} {n:03d}.pdf"


def _texto(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _esperar_ingreso(pg, patron: str, portal: str) -> None:
    try:
        pg.wait_for_url(patron, timeout=TIMEOUT_MS)
    except Exception as e:
        raise ErrorPortal(
            f"{portal}: no se pudo entrar. El portal requiere ingreso manual (captcha o código), "
            "rechazó el usuario o cambió su página."
        ) from e


def _bajar_url(ctx, url: str):
    def bajar() -> bytes:
        r = ctx.request.get(url, timeout=TIMEOUT_MS)
        if r.status != 200:
            raise ErrorPortal(f"HTTP {r.status}")
        return r.body()
    return bajar


def _doc(clave, fecha, proveedor, detalle, bajar) -> dict:
    return {"clave": clave, "fecha": fecha, "proveedor": proveedor, "idContacto": CONTACTOS.get(proveedor),
            "detalle": detalle, "bajar": bajar}


def listar_telepeajeplus(pw):
    usuario, clave = credencial("TelepeajePlus")
    ctx = pw.chromium.launch(channel="chrome", headless=True).new_context()
    pg = ctx.new_page()
    pg.goto(TP, timeout=TIMEOUT_MS)
    pg.fill("#USW_NOM", usuario)
    pg.fill("#pbPassword", clave)
    pg.keyboard.press("Enter")
    _esperar_ingreso(pg, "**/Login/Inicio**", "TelepeajePlus")
    rq = ctx.request
    actual = re.search(r"idResumen=(\d+)", rq.get(f"{TP}Resumen?contratoId={CONTRATO_TP}").text())
    if not actual:
        raise ErrorPortal("TelepeajePlus: no se encontró el resumen actual; puede haber cambiado la página.")
    lista = _texto(rq.get(f"{TP}ResumenesAnteriores?contratoId={CONTRATO_TP}&idResumen={actual.group(1)}").text())
    docs, avisos = [], []
    for periodo, id_res in re.findall(r"(\d{6}/\d+)\s*\(002-(\d+)\)", lista):
        detalle = _texto(rq.get(f"{TP}ResumenAnterior?contratoId={CONTRATO_TP}&idResumen={id_res}").text())
        cierre = re.search(r"Fecha de cierre\s*(\d{2}/\d{2}/\d{4})", detalle)
        if cierre:
            docs.append(_doc(f"tp-resumen-{id_res}", datetime.strptime(cierre.group(1), "%d/%m/%Y").date(), "Telepeaje",
                             f"Resumen {periodo}",
                             _bajar_url(ctx, f"{TP}DescargarArchivo?idResumen={id_res}&idContrato={CONTRATO_TP}&nombre=Resumen.pdf")))
        html = rq.get(f"{TP}ComprobantesResumen?idResumen={id_res}").text()
        archivos = re.findall(r"nombre=(FA\d+\.pdf)", html)
        filas = re.findall(r"(\d{2}/\d{2}/\d{4}) ([A-Z0-9 .]+?) \$ [\d.,]+ Descargar", _texto(html))
        for archivo, (fecha, concesionario) in zip(archivos, filas):
            proveedor = next((n for k, n in NOMBRES_TP if k in concesionario), None)
            if not proveedor:
                avisos.append(f"Concesionario sin proveedor asignado: {concesionario.strip()} ({archivo})")
                proveedor = "Telepeaje"
            docs.append(_doc(f"tp-{archivo}", datetime.strptime(fecha, "%d/%m/%Y").date(), proveedor,
                             f"{concesionario.strip()} en resumen {periodo}",
                             _bajar_url(ctx, f"{TP}DescargarArchivo?idResumen={id_res}&idContrato={CONTRATO_TP}&nombre={archivo}")))
            if proveedor == "Telepeaje":
                docs[-1]["idContacto"] = None
    return docs, ctx, avisos


def listar_telepase(pw):
    usuario, clave = credencial("TelePASE")
    ctx = pw.chromium.launch(channel="chrome", headless=True).new_context()
    pg = ctx.new_page()
    pg.goto(TS + "login", timeout=TIMEOUT_MS)
    pg.fill("#email", usuario)
    pg.fill("#password", clave)
    pg.keyboard.press("Enter")
    _esperar_ingreso(pg, "**/admin/**", "TelePASE")
    # El filtro va por GET: el formulario arranca en "a_vencida" y no muestra nada (research.md).
    desde = date(date.today().year - 1, 1, 1)
    pg.goto(f"{TS}admin/facturas?filtro-aut=T&filtro-cond=T&filtro-fec-ini={desde}&filtro-fec-fin={date.today()}&aplic=",
            timeout=TIMEOUT_MS)
    docs, avisos, pagina = [], [], 1
    while True:
        for tr in pg.query_selector_all("table tbody tr"):
            celdas = [td.inner_text().strip() for td in tr.query_selector_all("td")]
            enlace = next((a.get_attribute("href") for a in tr.query_selector_all("a")
                           if "descargar-factura" in (a.get_attribute("href") or "")), None)
            if len(celdas) < 3 or not enlace:
                continue
            concesionario = celdas[1]
            proveedor = NOMBRES_TS.get(concesionario)
            if not proveedor:
                avisos.append(f"Concesionario sin proveedor asignado: {concesionario} ({celdas[2]})")
                proveedor = "TelePASE"
            docs.append(_doc(f"ts-{concesionario}-{celdas[2]}", date.fromisoformat(celdas[0]), proveedor,
                             f"{concesionario} {celdas[2]}", _bajar_url(ctx, enlace)))
            if proveedor == "AUBASA":
                # La misma factura se ofrece en el portal propio de AUBASA: la baja el primero que la encuentra.
                docs[-1]["equivalentes"] = [f"aubasa-%-{celdas[2]}"]
        pagina += 1
        siguiente = pg.query_selector(f'a:text-is("{pagina}")')
        if not siguiente:
            break
        siguiente.click()
        pg.wait_for_timeout(2500)
    return docs, ctx, avisos


def _listar_oficina_virtual(pw, portal: str, login: str, proveedor: str, prefijo: str):
    """Oficinas virtuales GLM/Sixon (CEAMSE y AUBASA). Facturas = filas FAPP de la
    cuenta corriente (los REC son recibos y no se guardan); el PDF se baja con
    clic en el primer ícono de la fila."""
    usuario, clave = credencial(portal)
    ctx = pw.chromium.launch(channel="chrome", headless=True).new_context(accept_downloads=True)
    pg = ctx.new_page()
    pg.goto(login, timeout=TIMEOUT_MS)
    pg.fill("#vUSUARIO", usuario)
    pg.fill("#vPASSWORD", clave)
    pg.press("#vPASSWORD", "Enter")
    _esperar_ingreso(pg, "**home**", portal)
    cte = pg.url.replace("wwpbaseobjects.home", "cte")
    pg.goto(cte, timeout=TIMEOUT_MS)
    pg.wait_for_timeout(4000)
    docs, avisos = [], []
    for tr in pg.query_selector_all("table tr"):
        if not tr.query_selector("a[data-gx-evt]"):
            continue
        celdas = [td.inner_text().strip() for td in tr.query_selector_all("td")]
        fecha = next((c for c in celdas if re.fullmatch(r"\d{2}/\d{2}/\d{2}", c)), None)
        if not fecha:
            continue
        i = celdas.index(fecha)
        tipo, pvta, nro = celdas[i + 1], celdas[i + 3], celdas[i + 4]
        if tipo == "REC":
            continue
        if tipo != "FAPP":
            avisos.append(f"{portal}: comprobante tipo {tipo} {pvta}-{nro} del {fecha}; se baja igual")

        def bajar(pvta=pvta, nro=nro) -> bytes:
            pg.goto(cte, timeout=TIMEOUT_MS)
            pg.wait_for_timeout(4000)
            for fila in pg.query_selector_all("table tr"):
                textos = [td.inner_text().strip() for td in fila.query_selector_all("td")]
                if nro in textos and pvta in textos and fila.query_selector("a[data-gx-evt]"):
                    with pg.expect_download(timeout=TIMEOUT_MS) as descarga:
                        fila.query_selector_all("a[data-gx-evt]")[0].click()
                    return Path(descarga.value.path()).read_bytes()
            raise ErrorPortal("no se encontró la fila del comprobante")

        docs.append(_doc(f"{prefijo}-{pvta}-{nro}", datetime.strptime(fecha, "%d/%m/%y").date(), proveedor,
                         f"{proveedor} {tipo} {pvta}-{nro}", bajar))
        if prefijo == "aubasa":
            docs[-1]["equivalentes"] = [f"ts-AU. BS AS - LA PLATA-{nro}"]
    return docs, ctx, avisos


def listar_ceamse(pw):
    return _listar_oficina_virtual(pw, "CEAMSE", LOGIN_CEAMSE, "Ceamse", "ceamse")


def listar_aubasa(pw):
    return _listar_oficina_virtual(pw, "AUBASA", LOGIN_AUBASA, "AUBASA", "aubasa")


PORTALES = (
    ("TelepeajePlus", listar_telepeajeplus),
    ("TelePASE", listar_telepase),
    ("CEAMSE", listar_ceamse),
    ("AUBASA", listar_aubasa),
)
