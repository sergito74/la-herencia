"""Verificación externa semanal de los costos (050, 17/11/2026).

Corre sola una vez por semana mientras la aplicación está abierta (y se puede forzar). Solo lectura en los portales
(Bayá Casal: autorización permanente del 20/10/2026; ARCA Mis Comprobantes con la clave de Lucy: autorizado el
17/11/2026 para este cruce semanal):
  1. Bayá Casal → mercadería remitida pendiente de facturar: actualiza el precio de cada renglón de remito sin
     factura (dbo.RemitoValorProveedor) y avisa los remitos que el portal muestra y el sistema no tiene.
  2. ARCA → comprobantes recibidos de los últimos 120 días contra Compras: los que faltan en el sistema y los que
     tienen otro total o moneda (solo los que cargan costo de cultivo o stock; los particulares no).
El resultado queda en dbo.VerificacionExterna y lo muestra el control de integridad.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import tempfile
import threading
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from src.db.connection import execute_write, fetch_all

_log = logging.getLogger(__name__)
_CADA = timedelta(days=7)
_lock = threading.Lock()
_corriendo = {"si": False}
PORTAL_ARCA = 15
NOTAS_CREDITO = {3, 8, 13, 53, 113, 203, 208, 213}


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", ".")) if s else 0.0


def leer_csv_arca(texto: str) -> list[dict]:
    """Pura: filas del CSV de Mis Comprobantes (recibidos)."""
    out = []
    for r in csv.reader(io.StringIO(texto), delimiter=";"):
        if not r or not re.match(r"\d{4}-\d{2}-\d{2}", r[0]):
            continue
        tipo = int(r[1])
        out.append({"fecha": r[0], "tipo": tipo, "pv": int(r[2]), "nro": int(r[3]), "cuit": r[7], "emisor": r[8],
                    "moneda": r[12], "total": _num(r[-1]) * (-1 if tipo in NOTAS_CREDITO else 1)})
    return out


def cruzar(arca: list[dict], sistema: list[dict], en_costo: set[int]) -> list[dict]:
    """Pura: compara cada comprobante de ARCA con el del sistema (punto de venta y número; si hay varios, el CUIT).
    Devuelve las diferencias: faltantes y, para los que cargan costo, total o moneda distintos."""
    por_numero: dict[tuple, list[dict]] = defaultdict(list)
    for w in sistema:
        m = re.findall(r"\d+", w["nro"] or "")
        if len(m) >= 2:
            por_numero[(int(m[-2]), int(m[-1]))].append(w)
    out = []
    # Factura y nota de crédito del mismo emisor por el mismo importe (comprobante anulado): no es un faltante.
    importes: dict[tuple, int] = defaultdict(int)
    for a in arca:
        importes[(a["cuit"], round(a["total"], 2))] += 1
    anulados = {k for k in importes if importes.get((k[0], -k[1]))}
    for a in arca:
        if (a["cuit"], round(a["total"], 2)) in anulados:
            continue
        cands =[w for w in por_numero.get((a["pv"], a["nro"]), []) if abs(float(w["tot"] or 0)) > 0.005] or por_numero.get((a["pv"], a["nro"]), [])
        propios = [w for w in cands if w["cuit"] == a["cuit"]] or (cands if len(cands) == 1 else [])
        doc = f"{a['emisor']} · {a['pv']:04d}-{a['nro']:08d} del {a['fecha'][8:10]}/{a['fecha'][5:7]}/{a['fecha'][:4]}"
        if not propios:
            if abs(a["total"]) > 0.005:
                out.append({"tipo": "Comprobante de ARCA que no está cargado", "documento": doc,
                            "detalle": f"total {a['moneda']} {a['total']:,.2f}"})
            continue
        w = propios[0]
        if w["idCompra"] not in en_costo:
            continue
        if (a["moneda"] in ("$", "PES")) != (w["moneda"] == "Pesos"):
            out.append({"tipo": "Moneda distinta a la de ARCA", "documento": doc,
                        "detalle": f"ARCA {a['moneda']}, sistema {w['moneda']}", "idCompra": w["idCompra"]})
        elif abs(abs(float(w["tot"] or 0)) - abs(a["total"])) > 1.0:
            out.append({"tipo": "Total distinto al de ARCA", "documento": doc, "idCompra": w["idCompra"],
                        "detalle": f"ARCA {a['total']:,.2f}, sistema {float(w['tot'] or 0):,.2f}"})
    return out


def _arca(desde: date, hasta: date) -> list[dict]:
    from playwright.sync_api import sync_playwright

    from src.features.boveda import repository, servicio
    from src.features.boveda.conectores import arca as A
    from src.features.boveda.conectores.espera import cargada, ir

    if repository.autorizacion_vigente(PORTAL_ARCA) is None:
        raise RuntimeError("Sin autorización vigente para ARCA (clave de Lucy)")
    cred = servicio.credencial_de(fetch_all("SELECT IdCredencial AS c FROM dbo.Portales WHERE IdPortal = ?", (PORTAL_ARCA,))[0]["c"])
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome", headless=True)
        try:
            p = b.new_context(accept_downloads=True).new_page()
            ir(p, A.LOGIN, timeout=90000)
            p.fill("input[id$=username]", (cred.usuario or "").replace("-", ""))
            p.click("input[id$=btnSiguiente]")
            cargada(p, timeout=90000)
            p.fill("input[type=password]", cred.clave.valor() if cred.clave else "")
            p.click("input[id$=btnIngresar]")
            cargada(p, timeout=90000)
            if "portalcf" not in p.url:
                raise RuntimeError("ARCA rechazó el ingreso")
            ir(p, A.MIS_SERVICIOS, timeout=90000)
            with p.expect_popup(timeout=90000) as pop:
                p.get_by_text("MIS COMPROBANTES", exact=False).first.click()
            m = pop.value
            cargada(m, timeout=90000)
            m.wait_for_timeout(4000)
            m.get_by_text("Recibidos", exact=False).first.click()
            cargada(m, timeout=90000)
            m.wait_for_selector("#fechaEmision", timeout=90000)
            m.evaluate("""v => { const e = document.querySelector('#fechaEmision'); e.value = v;
                           e.dispatchEvent(new Event('change', {bubbles: true})); }""", f"{desde:%d/%m/%Y} - {hasta:%d/%m/%Y}")
            m.click("#buscarComprobantes")
            m.wait_for_timeout(15000)
            with m.expect_download(timeout=180000) as dl:
                m.locator("button:has-text('CSV'), a:has-text('CSV')").first.click()
            with tempfile.TemporaryDirectory() as d:
                destino = Path(d) / "recibidos.zip"
                dl.value.save_as(str(destino))
                with zipfile.ZipFile(destino) as zf:
                    texto = zf.read(zf.namelist()[0]).decode("utf-8", "replace")
            return leer_csv_arca(texto)
        finally:
            b.close()


def correr() -> dict:
    resultado: dict = {"fecha": datetime.now().isoformat(timespec="seconds"), "problemas": [], "errores": []}
    try:
        from scripts import baya_valor_remitos_050 as baya

        asignados, avisos = baya.emparejar(baya.bajar_pendientes())
        baya.guardar(asignados)
        resultado["bayaValorizados"] = len(asignados)
        resultado["problemas"] += [{"tipo": "Remito de Bayá Casal que no está cargado", "documento": "", "detalle": a} for a in avisos]
    except Exception as exc:  # noqa: BLE001
        _log.exception("Verificación externa: Bayá Casal")
        resultado["errores"].append(f"Bayá Casal: {exc}")
    try:
        hasta = date.today()
        arca = _arca(hasta - timedelta(days=120), hasta)
        sistema = fetch_all(
            "SELECT c.IdDeuda AS idCompra, c.[Nro Documento] AS nro, c.Moneda AS moneda, v.ImporteDocumento AS tot, "
            "REPLACE(REPLACE(ISNULL(co.[CUIT/CUIL], ''), '-', ''), ' ', '') AS cuit FROM dbo.Compras c "
            "JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto "
            "WHERE c.Fecha >= ?", (hasta - timedelta(days=200),))
        en_costo = {f["c"] for f in fetch_all(
            "SELECT DISTINCT d.IdCompra AS c FROM dbo.TamizRenglones tz JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra "
            "WHERE tz.Vigente = 1 AND tz.Destino IN ('Cultivo', 'CultivoStock')")}
        resultado["arcaComprobantes"] = len(arca)
        resultado["problemas"] += cruzar(arca, sistema, en_costo)
    except Exception as exc:  # noqa: BLE001
        _log.exception("Verificación externa: ARCA")
        resultado["errores"].append(f"ARCA: {exc}")
    execute_write("INSERT INTO dbo.VerificacionExterna (Resultado) VALUES (?)", (json.dumps(resultado, ensure_ascii=False),))
    return resultado


def ultima() -> dict | None:
    f = fetch_all("SELECT TOP 1 Fecha AS fecha, Resultado AS r FROM dbo.VerificacionExterna ORDER BY IdVerificacion DESC")
    return json.loads(f[0]["r"]) if f else None


def _vencida() -> bool:
    u = ultima()
    return u is None or datetime.now() - datetime.fromisoformat(u["fecha"]) > _CADA


def lanzar(forzar: bool = False) -> None:
    with _lock:
        if _corriendo["si"] or not (forzar or _vencida()):
            return
        _corriendo["si"] = True

    def _run():
        try:
            correr()
        finally:
            _corriendo["si"] = False

    threading.Thread(target=_run, name="verificacion-externa", daemon=True).start()


def arrancar() -> None:
    """Al iniciar la aplicación: revisa cada 6 horas si toca la verificación semanal."""
    def bucle():
        import time
        while True:
            try:
                lanzar()
            except Exception:  # noqa: BLE001
                _log.exception("Verificación externa")
            time.sleep(6 * 3600)

    threading.Thread(target=bucle, name="verificacion-externa-planificador", daemon=True).start()
