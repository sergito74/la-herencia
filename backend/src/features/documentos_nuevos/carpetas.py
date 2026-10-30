"""Subrutina de verificación de comprobantes e impuestos guardados en carpetas locales (Dropbox).

Revisa periódicamente el ejercicio actual y el anterior de Compras e Impuestos.
No toca la base si el archivo ya fue vinculado (en Compras/Impuestos) o ya está en DocumentosNuevos.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from src.db.connection import fetch_all
from src.features.descarga_peajes.portales import COMPRAS, carpeta_ejercicio
from src.features.documentos_nuevos import clasificador, lectores, repository

log = logging.getLogger(__name__)

IMPUESTOS = COMPRAS.parent / "Impuestos"


def ejercicios_a_revisar(hoy: date | None = None) -> list[str]:
    """Nombres de las carpetas de ejercicio: actual y anterior (ej: '04 2026 - 03 2027' y '04 2025 - 03 2026')."""
    hoy = hoy or date.today()
    actual = carpeta_ejercicio(hoy).name
    # 1 año atrás
    anterior_fecha = date(hoy.year - 1 if hoy.month >= 4 else hoy.year - 2, 5, 1)
    anterior = carpeta_ejercicio(anterior_fecha).name
    return [actual, anterior]


def archivos_en_base() -> set[str]:
    """Nombres de archivo (minúsculas) ya vinculados en Compras o Impuestos."""
    nombres: set[str] = set()
    for tabla, col in (("dbo.Compras", "[Documento Original]"), ("dbo.Impuestos", "[Documento Original]")):
        try:
            filas = fetch_all(f"SELECT {col} AS doc FROM {tabla} WHERE {col} IS NOT NULL")
            for f in filas:
                for parte in (f["doc"] or "").split("#"):
                    if parte:
                        nombres.add(Path(parte).name.lower())
        except Exception:
            log.exception("Error al consultar %s para auditoría de archivos", tabla)
    return nombres


def listar_archivos_carpetas(ejercicios: list[str]) -> Iterator[Path]:
    """Itera archivos .pdf y .xml de las carpetas de ejercicios seleccionadas y raíces."""
    for raiz in (COMPRAS, IMPUESTOS):
        if not raiz.exists():
            continue
        # Archivos sueltos en la raíz
        for p in raiz.iterdir():
            if p.is_file() and p.suffix.lower() in (".pdf", ".xml"):
                yield p
        # Archivos dentro de los ejercicios
        for ej in ejercicios:
            carpeta_ej = raiz / ej
            if not carpeta_ej.exists():
                continue
            for root, _, files in os.walk(carpeta_ej):
                for f in files:
                    if f.lower().endswith((".pdf", ".xml")):
                        yield Path(root) / f


def procesar_archivo_carpeta(id_corrida: int | None, path: Path, conocidos: set[str]) -> str | None:
    """Procesa un archivo encontrado en carpeta local. Devuelve estado ('cargado_solo', 'para_cargar', 'ya_estaba') o None."""
    if path.name.lower() in conocidos:
        return None

    try:
        contenido = path.read_bytes()
    except OSError:
        return None

    sha = hashlib.sha256(contenido).hexdigest()
    if repository.existente(sha):
        return None

    if path.suffix.lower() == ".pdf":
        texto = clasificador.texto_pdf(contenido)
    else:
        texto = contenido.decode("utf-8", errors="ignore")

    c = clasificador.clasificar(texto, clasificador.buscar_contacto_por_cuit)
    # Recibos no van a Compras: son constancias de pago que corresponderán al futuro módulo de pagos
    if not c.comprobante or not c.para_giamigli or c.tipo == "recibo":
        return None

    # Verificar si es duplicado de número y emisor
    if c.id_contacto and c.numero and repository.mismo_comprobante(c.id_contacto, c.numero, c.modulo):
        return None

    from src.features.boveda import repository as boveda
    ruta_str = str(path)
    estado, motivo, id_registro = "para_cargar", c.motivo, None

    if c.modulo == "compras" and c.id_contacto and c.numero:
        id_registro = boveda.compra_existente(c.id_contacto, c.numero, ruta_str)
        if id_registro:
            estado, motivo = "ya_estaba", None

    r = None
    if estado == "para_cargar" and c.tipo in ("resumen_banco", "resumen_tarjeta"):
        r = lectores.cargar_resumen(texto, contenido, ruta_str)
        if r is None:
            motivo = "Importar el resumen desde Tesorería"
    elif estado == "para_cargar" and c.id_contacto:
        r = lectores.cargar(c.tipo, c.id_contacto, c.contacto or "", c.numero, c.fecha, contenido, ruta_str)

    if r is not None:
        registro = r.get("idRegistro") or r.get("idCompra")
        if r["estadoCarga"] == "cargado_auto":
            estado, motivo, id_registro = "cargado_solo", None, registro
        elif r["estadoCarga"] == "ya_cargado":
            estado, motivo, id_registro = "ya_estaba", None, registro
        else:
            motivo = r["motivo"]

    if estado == "para_cargar" and not motivo:
        motivo = ("Importar el resumen desde Tesorería" if c.modulo == "tesoreria"
                  else "Revisar el documento guardado" if c.tipo in ("contrato", "resumen_proveedor")
                  else "El sistema todavía no sabe leer este comprobante: cargar a mano")

    repository.registrar_documento({
        "idRutinaCorrida": id_corrida,
        "origen": "mail",
        "mailEntryId": None,
        "mailRemitente": "Carpeta local (Dropbox)",
        "mailAsunto": path.name,
        "mailRecibido": datetime.fromtimestamp(path.stat().st_mtime),
        "sha256": sha,
        "ruta": ruta_str,
        "tipo": c.tipo or "otro",
        "modulo": c.modulo,
        "idContacto": c.id_contacto,
        "fecha": c.fecha,
        "numero": c.numero,
        "total": c.total,
        "estado": estado,
        "motivo": motivo,
        "idRegistro": id_registro,
    })
    return estado
