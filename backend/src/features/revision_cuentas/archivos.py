"""Revisión de solo lectura de las carpetas de comprobantes de compras — 036 (US6, research D9; FR-032 y FR-033).

Informa los archivos incompletos o ilegibles (un `.crdownload` de una descarga cortada, un archivo vacío, un PDF dañado) y si su comprobante
ya está cargado, para que ninguna factura se saltee en silencio. NUNCA modifica, renombra, mueve ni borra un archivo. La raíz de las
carpetas es un parámetro del backend (variable de entorno `COMPRAS_RAIZ`): el cliente nunca manda una ruta.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from pathlib import Path

from src.db.connection import fetch_all

RAIZ_POR_DEFECTO = Path.home() / "Dropbox" / "Giamigli de Bolivar SA" / "Compras"
PERIODO = re.compile(r"^04 (\d{4}) - 03 (\d{4})$")
EXTENSIONES_DE_IMAGEN = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".bmp", ".gif"}
_NUMERO = re.compile(r"(\d{4,5}-\d{8})")
_IMPORTE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})")
_NOMBRE = re.compile(r"^(\d{8})_(.+?)(?:\s+\d{3})?$")
ESTADOS = ("comprobante-legible-extension-incorrecta", "no-legible", "vacio", "imagen-revisar")


def raiz() -> Path:
    return Path(os.environ.get("COMPRAS_RAIZ") or RAIZ_POR_DEFECTO)


def validar_periodo(periodo: str | None) -> None:
    """`04 AAAA - 03 AAAA+1` (ValueError → 422). Evita rutas arbitrarias: el período solo elige una subcarpeta de la raíz."""
    if periodo is None:
        return
    m = PERIODO.match(periodo)
    if not m or int(m.group(2)) != int(m.group(1)) + 1:
        raise ValueError("El período tiene que ser como '04 2025 - 03 2026'")


def periodos(base: Path) -> list[str]:
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and PERIODO.match(p.name))


# --------------------------------------------------------------------------- lectura de archivos (no modifica nada)

def _texto_pdf(ruta: Path) -> str | None:
    """Texto de la primera página de un PDF, o None si no se puede leer. Solo lectura."""
    try:
        import pdfplumber

        with pdfplumber.open(str(ruta)) as pdf:
            return (pdf.pages[0].extract_text() or "") if pdf.pages else None
    except Exception:
        return None


def _empieza_como_pdf(ruta: Path) -> bool:
    try:
        with open(ruta, "rb") as f:
            return f.read(1024).lstrip().startswith(b"%PDF")
    except OSError:
        return False


def normalizar_numero(numero: str | None) -> str | None:
    """`0009-00077393` y `00009-00077393` son el mismo comprobante: se comparan solo los dígitos sin ceros a la izquierda."""
    digitos = re.sub(r"\D", "", numero or "").lstrip("0")
    return digitos or None


def datos_del_nombre(nombre: str) -> tuple[date | None, str]:
    """`20250923_JaureguiYMorales.crdownload` → (2025-09-23, 'JaureguiYMorales'); admite el sufijo ` 001`."""
    base = nombre
    for _ in range(2):                                        # quita la extensión (y `.pdf.crdownload`)
        raiz_nombre, ext = os.path.splitext(base)
        if ext.lower() in (".crdownload", ".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".bmp", ".gif"):
            base = raiz_nombre
        else:
            break
    m = _NOMBRE.match(base)
    if not m:
        return None, base
    try:
        fecha = datetime.strptime(m.group(1), "%Y%m%d").date()
    except ValueError:
        fecha = None
    return fecha, m.group(2)


def clasificar(ruta: Path, texto_pdf=None) -> dict | None:
    """Estado de un archivo si está incompleto o hay que mirarlo a mano; None si está bien. Solo lectura."""
    texto_pdf = texto_pdf or _texto_pdf
    ext = ruta.suffix.lower()
    try:
        tamano = ruta.stat().st_size
    except OSError:
        return None
    base = {"numero": None, "importe": None}
    if ext == ".crdownload":
        if tamano == 0:
            return {"estado": "vacio", **base}
        texto = texto_pdf(ruta)
        if texto and len(texto.strip()) > 20:
            numero = _NUMERO.search(texto)
            importes = _IMPORTE.findall(texto)
            return {"estado": "comprobante-legible-extension-incorrecta", "numero": numero.group(1) if numero else None,
                    "importe": float(importes[-1].replace(".", "").replace(",", ".")) if importes else None}
        return {"estado": "no-legible", **base}
    if ext == ".pdf":
        if tamano == 0:
            return {"estado": "vacio", **base}
        return None if _empieza_como_pdf(ruta) else {"estado": "no-legible", **base}   # un PDF sano no se informa
    if ext in EXTENSIONES_DE_IMAGEN:
        return {"estado": "vacio" if tamano == 0 else "imagen-revisar", **base}
    return None


def _cargadas() -> tuple[dict[str, int], list[tuple[str, int]]]:
    """Comprobantes ya cargados: número normalizado → compra, y los "documento original" en minúsculas (para reconocer el archivo por su nombre)."""
    filas = fetch_all("SELECT IdDeuda AS i, [Nro Documento] AS n, [Documento Original] AS d FROM dbo.Compras", ())
    numeros: dict[str, int] = {}
    documentos: list[tuple[str, int]] = []
    for f in filas:
        n = normalizar_numero(f["n"])
        if n and n not in numeros:
            numeros[n] = int(f["i"])
        if f["d"]:
            documentos.append((str(f["d"]).lower(), int(f["i"])))
    return numeros, documentos


def revisar(periodo: str | None = None, estado: str | None = None, pagina: int = 1, tamano: int = 50,
            base: Path | None = None, cargadas=None, texto_pdf=None) -> dict:
    """Archivos incompletos o por mirar de las carpetas de compras (todas o de un período), con su estado y si el comprobante está cargado."""
    validar_periodo(periodo)
    if estado is not None and estado not in ESTADOS:
        raise ValueError("Estado desconocido")
    base = base or raiz()
    texto_pdf = texto_pdf or _texto_pdf
    numeros, documentos = (cargadas or _cargadas)()
    elegidos = [periodo] if periodo else periodos(base)
    archivos: list[dict] = []
    for p in elegidos:
        carpeta = base / p
        if not carpeta.is_dir():
            continue
        for ruta in sorted(carpeta.iterdir()):
            if not ruta.is_file():
                continue
            c = clasificar(ruta, texto_pdf)
            if c is None or (estado and c["estado"] != estado):
                continue
            fecha, proveedor = datos_del_nombre(ruta.name)
            id_compra = numeros.get(normalizar_numero(c["numero"])) if c["numero"] else None
            if id_compra is None:
                nombre = ruta.name.lower()
                id_compra = next((i for d, i in documentos if nombre in d), None)
            archivos.append({"ruta": str(ruta), "periodo": p, "proveedor": proveedor, "fecha": fecha, "estado": c["estado"], "numero": c["numero"],
                             "importe": c["importe"], "cargado": id_compra is not None, "idCompra": id_compra})
    archivos.sort(key=lambda a: (a["periodo"], a["fecha"] or date.min, a["ruta"]), reverse=True)
    inicio = (pagina - 1) * tamano
    return {"raiz": str(base), "total": len(archivos), "archivos": archivos[inicio:inicio + tamano]}
