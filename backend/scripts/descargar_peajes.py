"""Descarga semanal de resúmenes y facturas de peaje (pedido de Sergio, 2026-10-16).

Portales:
- TelepeajePlus (https://www.telepeajeplus.com): resúmenes quincenales de
  Telepeaje y las facturas de las concesionarias que vienen adentro de cada
  resumen (Corredores Viales, Corresur, Pentavia/CV5).
- TelePASE (https://telepase.com.ar): facturas de Autopistas del Sol (Acceso
  Norte), Grupo Concesionario del Oeste, AUSA y Corredores Viales/Riccheri.
- Oficinas virtuales de CEAMSE y AUBASA (agregadas 2026-10-16): facturas
  "AAAAMMDD_Ceamse" y "AAAAMMDD_AUBASA".

Guarda cada PDF en Dropbox\\Giamigli de Bolivar SA\\Compras\\<ejercicio> con
el nombre estándar AAAAMMDD_Proveedor.pdf (si ya existe ese nombre, agrega
" 001", " 002"...). El ejercicio va de abril a marzo ("04 2026 - 03 2027").

Es idempotente: `_descargas_portales.json` (en la carpeta Compras) registra la
clave de cada documento ya bajado. Solo descarga; no carga nada en WC.

Credenciales: Administrador de credenciales de Windows (módulo keyring),
servicio "LaHerencia-Peajes", entradas "telepeajeplus", "telepase", "ceamse"
y "aubasa" (cada una con su "<cuenta>-usuario"). Nunca en este archivo.

Uso:  python -m scripts.descargar_peajes [--dry-run] [--sembrar]
  --dry-run  lista lo que bajaría, sin escribir.
  --sembrar  marca como ya descargado todo lo que hoy ofrecen los portales
             (se usó una vez, cuando la carpeta estaba completa).
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

import keyring
from playwright.sync_api import sync_playwright

COMPRAS = Path.home() / "Dropbox" / "Giamigli de Bolivar SA" / "Compras"
MANIFIESTO = COMPRAS / "_descargas_portales.json"
LOG = COMPRAS / "_descargas_portales.log"
SERVICIO = "LaHerencia-Peajes"

TP = "https://www.telepeajeplus.com/Login/"
TS = "https://telepase.com.ar/"
CONTRATO_TP = "1345207"

# Concesionario → nombre de archivo estándar (los que ya usa la carpeta).
NOMBRES_TS = {
    "ACCESO NORTE": "AutopistasDelSol",
    "ACCESO OESTE": "GrupoConcesionarioDelOeste",
    "AUTOPISTAS URBANAS": "AUSA",
    "ACCESO RICCHERI": "CorredoresViales",
}
NOMBRES_TP = [("CVSA", "CorredoresViales"), ("CORRESUR", "Corresur"), ("PENTAVIA", "CV5")]


def log(msg: str) -> None:
    linea = f"{datetime.now():%Y-%m-%d %H:%M} {msg}"
    print(linea)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(linea + "\n")


def carpeta_ejercicio(d: date) -> Path:
    inicio = d.year if d.month >= 4 else d.year - 1
    return COMPRAS / f"04 {inicio} - 03 {inicio + 1}"


def destino_libre(d: date, proveedor: str) -> Path:
    carpeta = carpeta_ejercicio(d)
    base = f"{d:%Y%m%d}_{proveedor}"
    ruta = carpeta / f"{base}.pdf"
    if not ruta.exists():
        return ruta
    n = 1
    while (carpeta / f"{base} {n:03d}.pdf").exists():
        n += 1
    return carpeta / f"{base} {n:03d}.pdf"


def credencial(cuenta: str) -> tuple[str, str]:
    usuario = keyring.get_password(SERVICIO, f"{cuenta}-usuario")
    clave = keyring.get_password(SERVICIO, cuenta)
    if not usuario or not clave:
        raise SystemExit(f"Faltan credenciales '{cuenta}' en el Administrador de credenciales ({SERVICIO}).")
    return usuario, clave


def texto(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def pendientes_telepeajeplus(pw) -> list[dict]:
    usuario, clave = credencial("telepeajeplus")
    ctx = pw.chromium.launch(channel="chrome", headless=True).new_context()
    pg = ctx.new_page()
    pg.goto(TP, timeout=60000)
    pg.fill("#USW_NOM", usuario)
    pg.fill("#pbPassword", clave)
    pg.keyboard.press("Enter")
    pg.wait_for_url("**/Login/Inicio**", timeout=60000)
    rq = ctx.request

    actual = re.search(r"idResumen=(\d+)", rq.get(f"{TP}Resumen?contratoId={CONTRATO_TP}").text()).group(1)
    lista = texto(rq.get(f"{TP}ResumenesAnteriores?contratoId={CONTRATO_TP}&idResumen={actual}").text())
    docs = []
    for periodo, id_res in re.findall(r"(\d{6}/\d+)\s*\(002-(\d+)\)", lista):
        detalle = texto(rq.get(f"{TP}ResumenAnterior?contratoId={CONTRATO_TP}&idResumen={id_res}").text())
        cierre = re.search(r"Fecha de cierre\s*(\d{2}/\d{2}/\d{4})", detalle)
        if cierre:
            docs.append({
                "clave": f"tp-resumen-{id_res}", "fecha": datetime.strptime(cierre.group(1), "%d/%m/%Y").date(),
                "proveedor": "Telepeaje", "url": f"{TP}DescargarArchivo?idResumen={id_res}&idContrato={CONTRATO_TP}&nombre=Resumen.pdf",
                "detalle": f"Resumen {periodo}",
            })
        html = rq.get(f"{TP}ComprobantesResumen?idResumen={id_res}").text()
        t = texto(html)
        archivos = re.findall(r"nombre=(FA\d+\.pdf)", html)
        filas = re.findall(r"(\d{2}/\d{2}/\d{4}) ([A-Z0-9 .]+?) \$ [\d.,]+ Descargar", t)
        for archivo, (fecha, concesionario) in zip(archivos, filas):
            proveedor = next((n for k, n in NOMBRES_TP if k in concesionario), None)
            if not proveedor:
                log(f"AVISO concesionario sin nombre estándar: {concesionario} ({archivo}); se baja como Telepeaje")
                proveedor = "Telepeaje"
            docs.append({
                "clave": f"tp-{archivo}", "fecha": datetime.strptime(fecha, "%d/%m/%Y").date(), "proveedor": proveedor,
                "url": f"{TP}DescargarArchivo?idResumen={id_res}&idContrato={CONTRATO_TP}&nombre={archivo}",
                "detalle": f"{concesionario.strip()} en resumen {periodo}",
            })
    return docs, ctx


def pendientes_telepase(pw) -> list[dict]:
    usuario, clave = credencial("telepase")
    ctx = pw.chromium.launch(channel="chrome", headless=True).new_context()
    pg = ctx.new_page()
    pg.goto(TS + "login", timeout=60000)
    pg.fill("#email", usuario)
    pg.fill("#password", clave)
    pg.keyboard.press("Enter")
    pg.wait_for_url("**/admin/**", timeout=60000)
    desde = date(date.today().year - 1, 1, 1)
    pg.goto(f"{TS}admin/facturas?filtro-aut=T&filtro-cond=T&filtro-fec-ini={desde}&filtro-fec-fin={date.today()}&aplic=", timeout=60000)
    docs, pagina = [], 1
    while True:
        for tr in pg.query_selector_all("table tbody tr"):
            celdas = [td.inner_text().strip() for td in tr.query_selector_all("td")]
            enlace = next((a.get_attribute("href") for a in tr.query_selector_all("a")
                           if "descargar-factura" in (a.get_attribute("href") or "")), None)
            if len(celdas) < 3 or not enlace:
                continue
            concesionario = celdas[1]
            docs.append({
                "clave": f"ts-{concesionario}-{celdas[2]}", "fecha": date.fromisoformat(celdas[0]),
                "proveedor": NOMBRES_TS.get(concesionario, "TelePASE"), "url": enlace,
                "detalle": f"{concesionario} {celdas[2]}",
            })
        pagina += 1
        siguiente = pg.query_selector(f'a:text-is("{pagina}")')
        if not siguiente:
            break
        siguiente.click()
        pg.wait_for_timeout(2500)
    return docs, ctx


def pendientes_oficina_virtual(pw, cuenta: str, login: str, proveedor: str) -> list[dict]:
    """Oficinas virtuales de GLM/Sixon (CEAMSE y AUBASA, mismo sistema GeneXus).
    La cuenta corriente lista los últimos 12 meses; las facturas son las filas
    tipo FAPP (los REC son recibos de pago y no se guardan). El PDF no tiene
    URL propia: se baja haciendo clic en el primer ícono de la fila."""
    usuario, clave = credencial(cuenta)
    ctx = pw.chromium.launch(channel="chrome", headless=True).new_context(accept_downloads=True)
    pg = ctx.new_page()
    pg.goto(login, timeout=60000)
    pg.fill("#vUSUARIO", usuario)
    pg.fill("#vPASSWORD", clave)
    pg.press("#vPASSWORD", "Enter")
    pg.wait_for_url("**home**", timeout=60000)
    cte = pg.url.replace("wwpbaseobjects.home", "cte")
    pg.goto(cte, timeout=60000)
    pg.wait_for_timeout(4000)
    docs = []
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
            log(f"AVISO {proveedor}: comprobante tipo {tipo} {pvta}-{nro} del {fecha}; se baja igual")

        def bajar(pvta=pvta, nro=nro):
            pg.goto(cte, timeout=60000)
            pg.wait_for_timeout(4000)
            for fila in pg.query_selector_all("table tr"):
                textos = [td.inner_text().strip() for td in fila.query_selector_all("td")]
                if nro in textos and pvta in textos and fila.query_selector("a[data-gx-evt]"):
                    with pg.expect_download(timeout=60000) as descarga:
                        fila.query_selector_all("a[data-gx-evt]")[0].click()
                    return Path(descarga.value.path()).read_bytes()
            raise RuntimeError("no se encontró la fila")

        docs.append({
            "clave": f"{cuenta}-{pvta}-{nro}", "fecha": datetime.strptime(fecha, "%d/%m/%y").date(),
            "proveedor": proveedor, "bajar": bajar, "detalle": f"{proveedor} {tipo} {pvta}-{nro}",
        })
    return docs, ctx


PORTALES = (
    ("TelepeajePlus", pendientes_telepeajeplus),
    ("TelePASE", pendientes_telepase),
    ("CEAMSE", lambda pw: pendientes_oficina_virtual(
        pw, "ceamse", "https://ceamse.sixon.com.ar/CEAMSE_OFICINA_VIRTUAL_PROD/com.ceamseoficinavirtual.login", "Ceamse")),
    ("AUBASA", lambda pw: pendientes_oficina_virtual(
        pw, "aubasa", "https://autogestionaubasa.com.ar/AUBASA_OFICINA_VIRTUAL_PROD/servlet/com.aubasaoficinavirtual.login", "AUBASA")),
)


def main() -> None:
    dry = "--dry-run" in sys.argv
    sembrar = "--sembrar" in sys.argv
    hechos = set(json.loads(MANIFIESTO.read_text(encoding="utf-8"))) if MANIFIESTO.exists() else set()
    nuevos = 0
    with sync_playwright() as pw:
        for nombre, fuente in PORTALES:
            try:
                docs, ctx = fuente(pw)
            except Exception as e:  # un portal caído no frena al otro
                log(f"ERROR {nombre}: {e}")
                continue
            for d in docs:
                if d["clave"] in hechos:
                    continue
                if sembrar:
                    hechos.add(d["clave"])
                    continue
                ruta = destino_libre(d["fecha"], d["proveedor"])
                if dry:
                    log(f"[dry-run] bajaría {d['detalle']} -> {ruta.name}")
                    continue
                try:
                    if "bajar" in d:
                        cuerpo, estado = d["bajar"](), 200
                    else:
                        r = ctx.request.get(d["url"])
                        cuerpo, estado = r.body(), r.status
                except Exception as e:
                    log(f"ERROR al bajar {d['detalle']}: {e}")
                    continue
                if estado != 200 or not cuerpo.startswith(b"%PDF"):
                    log(f"ERROR al bajar {d['detalle']}: HTTP {estado}")
                    continue
                ruta.parent.mkdir(exist_ok=True)
                ruta.write_bytes(cuerpo)
                hechos.add(d["clave"])
                nuevos += 1
                log(f"bajado {d['detalle']} -> {ruta}")
    if not dry:
        MANIFIESTO.write_text(json.dumps(sorted(hechos), ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"fin: {nuevos} documento(s) nuevo(s){' (sembrado)' if sembrar else ''}")


if __name__ == "__main__":
    main()
