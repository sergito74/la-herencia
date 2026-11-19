"""Lectura automática del extracto mensual del Fondo Fima (19/11/2026, Inversiones etapa 2).

El sistema busca los PDF "Extracto_Inversiones_Galicia_AAAA_MM_DD.pdf" en Dropbox (Bancos/Galicia/Inversiones/<año> y
Cuenta Comitente/<año>), toma el saldo valorizado, las cuotapartes y el valor de la cuota del FIMA PREMIUM CLASE A y
suma el mes a `flujo_caja/fima_posiciones.json`. Con eso Inversiones y el flujo de caja calculan el rendimiento del mes.
Corre solo (al abrir el sistema y una vez por día); nunca a mano.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

_log = logging.getLogger(__name__)
BASE = Path.home() / "Dropbox" / "Giamigli de Bolivar SA" / "Bancos" / "Galicia"
CARPETAS = ("Inversiones", "Cuenta Comitente")
DESTINO = Path(__file__).resolve().parents[1] / "flujo_caja" / "fima_posiciones.json"
_NOMBRE = re.compile(r"Extracto_Inversiones_Galicia_(\d{4})_(\d{2})_(\d{2})\.pdf$", re.I)
_MOV = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(RESCATE|SUSCRIPCION|SUSCRIPCI.N)\s+[\d.,]+\s+\$\s*[\d.,]+\s+\$\s*([\d.]+,\d{2})", re.I)
_LINEA = re.compile(r"FIMA PREMIUM CLASE A\s+(.+?)\s+\$\s*([\d.]+,\d+)\s+\$\s*([\d.]+,\d{2})")


def _num(t: str) -> float:
    return float(t.replace(".", "").replace(",", "."))


def leer_pdf(ruta: Path) -> dict | None:
    import pdfplumber

    m = _NOMBRE.search(ruta.name)
    if not m:
        return None
    with pdfplumber.open(ruta) as d:
        texto = "\n".join(p.extract_text() or "" for p in d.pages)
    linea = _LINEA.search(texto)
    if not linea:
        return None
    fecha = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    movs = _MOV.findall(texto)
    # Suscripciones y rescates según el propio fondo (19/11/2026): el banco a veces los registra en otro corte de mes.
    return {"periodo": fecha[:7], "fecha": fecha, "saldo": _num(linea.group(3)),
            "cuotas": linea.group(1).strip(), "valorCuota": _num(linea.group(2)),
            "suscripciones": round(sum(_num(x[2]) for x in movs if not x[1].upper().startswith("RESCATE")), 2),
            "rescates": round(sum(_num(x[2]) for x in movs if x[1].upper().startswith("RESCATE")), 2)}


def actualizar() -> list[str]:
    """Suma los meses que faltan. Devuelve las fechas agregadas."""
    actual = json.loads(DESTINO.read_text(encoding="utf-8")) if DESTINO.exists() else {}
    periodos = {v["periodo"] for v in actual.values()}
    nuevos = []
    for carpeta in CARPETAS:
        for ruta in sorted((BASE / carpeta).glob("*/Extracto_Inversiones_Galicia_*.pdf")):
            m = _NOMBRE.search(ruta.name)
            if not m:
                continue
            existente = next((v for v in actual.values() if v["periodo"] == f"{m.group(1)}-{m.group(2)}"), None)
            if existente and "rescates" in existente:
                continue
            try:
                pos = leer_pdf(ruta)
            except Exception:
                _log.exception("No se pudo leer %s", ruta)
                continue
            if pos:
                if existente:
                    actual.pop(existente["fecha"], None)
                actual[pos["fecha"]] = pos
                periodos.add(pos["periodo"])
                nuevos.append(pos["fecha"])
    if nuevos:
        DESTINO.write_text(json.dumps(dict(sorted(actual.items())), ensure_ascii=False, indent=2), encoding="utf-8")
        _log.info("Fondo Fima: extractos agregados %s", nuevos)
    return nuevos
