"""Proceso común de un documento nuevo (043), igual para mails y carpetas locales (03/11/2026).

Antes había dos copias (rutina.procesar_adjunto y carpetas.procesar_archivo_carpeta) que divergían: una tenía el
respaldo por remitente y la otra no, etc. Acá vive todo lo que decide qué es el documento y qué se hace con él:

- `textos_de`: texto del archivo y, si es un PDF con varias facturas (Sancor manda 3 en uno), un bloque por factura.
- `clasificar`: clasificación + emisor por remitente + número nulo en resúmenes de proveedor.
- `resolver`: ya estaba / se carga solo / queda para cargar a mano, con el motivo.
- `registrar`: el aviso en `DocumentosNuevos`.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass

from src.features.documentos_nuevos import clasificador, lectores, repository
from src.features.documentos_nuevos.clasificador import Clasificacion

MOTIVO_ESCANEO = "Escaneo sin texto: el sistema no lo puede leer, revisarlo y cargarlo a mano"


@dataclass
class Bloque:
    texto: str
    sha: str
    indice: int = 0


def _numero_rotulado(t: str) -> str | None:
    m = re.search(r"(?:FACTURA|NOTA DE CR[EÉ]DITO|NOTA DE D[EÉ]BITO)\s*N[°º.]?\s*:?\s*(\d{4,5})\s*-\s*(\d{8,9})", t,
                  re.I)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def textos_de(nombre: str, contenido: bytes) -> list[Bloque]:
    """Uno o más bloques de texto. Un PDF con varias facturas numeradas con CAE (Sancor: 3 pólizas en un archivo)
    devuelve un bloque por factura, cada uno con su propio sha (el del archivo + '#n') para no chocar en la base."""
    sha = hashlib.sha256(contenido).hexdigest()
    if not nombre.lower().endswith(".pdf"):
        return [Bloque(contenido.decode("utf-8", errors="ignore"), sha)]
    texto = clasificador.texto_pdf(contenido)
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(contenido)) as doc:
            paginas = [(p.extract_text() or "") for p in doc.pages]
    except Exception:
        return [Bloque(texto, sha)]
    grupos: list[tuple[str, list[str]]] = []
    for pag in paginas:
        numero = _numero_rotulado(pag) if re.search(clasificador.CAE_RE, pag.upper()) else None
        if numero and (not grupos or grupos[-1][0] != numero):
            grupos.append((numero, [pag]))
        elif grupos:
            grupos[-1][1].append(pag)
    if len({n for n, _ in grupos}) < 2:
        return [Bloque(texto, sha)]
    return [Bloque("\n".join(pags), sha if i == 0 else hashlib.sha256(contenido + f"#{i}".encode()).hexdigest(), i)
            for i, (_, pags) in enumerate(grupos)]


def clasificar(texto: str, remitente: str | None) -> Clasificacion:
    c = clasificador.clasificar(texto, clasificador.buscar_contacto_por_cuit)
    if not c.comprobante:
        return c
    if not c.id_contacto and remitente and c.tipo not in ("resumen_banco", "resumen_tarjeta"):
        por_mail = clasificador.contacto_por_remitente(remitente)
        if por_mail:
            c.id_contacto, c.contacto = por_mail
            if c.motivo and c.motivo.startswith("Emisor nuevo"):
                c.motivo = None
    if c.tipo == "resumen_proveedor":
        c.numero = None  # el número que aparece es de un renglón del detalle, no del resumen
    return c


def resolver(c: Clasificacion, texto: str, contenido: bytes, ruta: str) -> tuple[str, str | None, int | None]:
    """(estado, motivo, idRegistro)."""
    from src.features.boveda import repository as boveda

    estado, motivo, id_registro = "para_cargar", c.motivo, None
    if c.modulo == "compras" and c.id_contacto and c.numero:
        id_registro = boveda.compra_existente(c.id_contacto, c.numero, ruta)
        if id_registro:
            estado, motivo = "ya_estaba", None
    if c.modulo == "impuestos" and c.tipo == "boleta" and c.id_contacto:
        id_registro = repository.impuesto_existente(c.id_contacto, c.total, c.fecha)
        if id_registro:
            estado, motivo = "ya_estaba", None
    r = None
    if estado == "para_cargar" and c.tipo in ("resumen_banco", "resumen_tarjeta"):
        r = lectores.cargar_resumen(texto, contenido, ruta)
        if r is None:
            motivo = "Importar el resumen desde Tesorería"
    elif estado == "para_cargar" and c.id_contacto and c.tipo != "recibo":
        r = lectores.cargar(c.tipo, c.id_contacto, c.contacto or "", c.numero, c.fecha, contenido, ruta)
    if r is not None:
        registro = r.get("idRegistro") or r.get("idCompra")
        if r["estadoCarga"] == "cargado_auto":
            estado, motivo, id_registro = "cargado_solo", None, registro
        elif r["estadoCarga"] == "ya_cargado":
            estado, motivo, id_registro = "ya_estaba", None, registro
        else:
            motivo = r["motivo"]
    if estado == "para_cargar" and not motivo:
        motivo = ("Vincular el recibo con los pagos y facturas" if c.tipo == "recibo"
                  else "Importar el resumen desde Tesorería" if c.modulo == "tesoreria"
                  else "Revisar el documento guardado" if c.tipo in ("contrato", "resumen_proveedor")
                  else "El sistema todavía no sabe leer este comprobante: cargar a mano")
    return estado, motivo, id_registro


def registrar(origen: dict, c: Clasificacion, sha: str, ruta: str, estado: str, motivo: str | None,
              id_registro: int | None) -> str:
    """`origen`: idRutinaCorrida, mailEntryId, mailRemitente, mailAsunto, mailRecibido."""
    repository.registrar_documento({
        **origen, "origen": "mail", "sha256": sha, "ruta": ruta, "tipo": c.tipo or "otro", "modulo": c.modulo,
        "idContacto": c.id_contacto, "fecha": c.fecha, "numero": c.numero, "total": c.total,
        "estado": estado, "motivo": motivo, "idRegistro": id_registro,
    })
    return estado


def escaneo(id_contacto: int | None, contacto: str | None) -> Clasificacion:
    """PDF sin texto (escaneo o foto): se avisa "sin clasificar" en vez de ignorarlo en silencio."""
    return Clasificacion(comprobante=True, tipo="otro", modulo="sin_clasificar", id_contacto=id_contacto,
                         contacto=contacto, motivo=MOTIVO_ESCANEO)
