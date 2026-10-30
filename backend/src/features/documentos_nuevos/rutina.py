"""Rutina de documentos nuevos (043, US2): todos los días a las 7:00 y a las 14:00, sin botón.

1. Sincroniza de a una las cuentas de la bóveda con autorización vigente y contraseña; cada documento bajado
   genera su aviso (`avisos.desde_portal`). Una cuenta que falla o está ocupada se informa y se sigue.
2. Lee los mails nuevos de cada almacén de Outlook desde su marca, toma solo comprobantes dirigidos a Giamigli
   (o a la Sucesión), los guarda en su carpeta sin duplicar, los carga si hay lector probado y registra el aviso.
   La marca de un almacén se adelanta cuando su lectura terminó bien, aunque alguna cuenta haya fallado.
3. Cierra la corrida con lo hecho en palabras simples (visible en la bóveda).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, time, timedelta
from pathlib import Path

from src.features.documentos_nuevos import avisos, clasificador, lectores, mails, repository

log = logging.getLogger(__name__)

PROBLEMAS = {"error", "sin_credenciales", "sin_autorizacion", "credenciales_rechazadas", "requiere_intervencion",
             "portal_cambio"}


# --- Horario -----------------------------------------------------------------

def horarios(texto: str | None) -> list[time]:
    return sorted(time.fromisoformat(h.strip()) for h in (texto or "07:00,14:00").split(",") if h.strip())


def proxima(texto: str | None, desde: datetime) -> datetime:
    """Primer horario estrictamente posterior a `desde` (hoy o mañana)."""
    for dia in (desde.date(), desde.date() + timedelta(days=1)):
        for h in horarios(texto):
            candidato = datetime.combine(dia, h)
            if candidato > desde:
                return candidato
    raise ValueError("Sin horarios para la rutina")


# --- Cuentas -----------------------------------------------------------------

def _cuentas(r: dict, problemas: list[str]) -> None:
    from src.features.boveda import repository as boveda, servicio

    for p in repository.portales_sincronizables():
        if boveda.corrida_en_curso(p["idPortal"]) is not None:
            problemas.append(f"{p['nombre']}: estaba sincronizando, se salteó")
            r["cuentasConProblemas"] += 1
            continue
        try:
            _, estado = servicio.correr_portal(p["idPortal"], "programada", "sistema")
        except Exception:
            log.exception("Rutina: falló la cuenta %s", p["idPortal"])
            estado = "error"
        r["cuentasCorridas"] += 1
        if estado == "salteada":
            problemas.append(f"{p['nombre']}: estaba sincronizando, se salteó")
            r["cuentasConProblemas"] += 1
        elif estado in PROBLEMAS:
            problemas.append(f"{p['nombre']}: revisar en la bóveda")
            r["cuentasConProblemas"] += 1


def _contar_portal(id_corrida: int, r: dict) -> None:
    """Lo que las cuentas dejaron en `DocumentosNuevos` durante esta corrida."""
    from src.db.connection import fetch_all

    for f in fetch_all("SELECT Estado AS e, COUNT(*) AS n FROM dbo.DocumentosNuevos WHERE IdRutinaCorrida = ? "
                       "AND Origen = 'portal' GROUP BY Estado", (id_corrida,)):
        if f["e"] != "ya_estaba":
            r["documentosNuevos"] += f["n"]
        r["cargadosSolos"] += f["n"] if f["e"] == "cargado_solo" else 0
        r["paraCargarAMano"] += f["n"] if f["e"] == "para_cargar" else 0


# --- Mails -------------------------------------------------------------------

def _guardar(carpeta: Path, nombre: str, contenido: bytes, sha: str) -> str:
    """Guarda sin pisar: si ya hay un archivo idéntico en la carpeta se reusa; si el nombre existe, " 001"…"""
    carpeta.mkdir(parents=True, exist_ok=True)
    for f in carpeta.glob(f"*{Path(nombre).suffix}"):
        try:
            if f.stat().st_size == len(contenido) and hashlib.sha256(f.read_bytes()).hexdigest() == sha:
                return str(f)
        except OSError:
            continue
    base, ext = Path(nombre).stem, Path(nombre).suffix or ".pdf"
    ruta, n = carpeta / f"{base}{ext}", 1
    while ruta.exists():
        ruta, n = carpeta / f"{base} {n:03d}{ext}", n + 1
    ruta.write_bytes(contenido)
    return str(ruta)


def procesar_adjunto(id_corrida: int | None, mail: mails.Mail, adj: mails.Adjunto) -> str | None:
    """Devuelve el estado registrado (`cargado_solo`, `para_cargar`, `ya_estaba`) o `None` si se ignoró."""
    from src.features.boveda import repository as boveda

    sha = hashlib.sha256(adj.contenido).hexdigest()
    if repository.adjunto_procesado(mail.entry_id, sha) or repository.existente(sha):
        return None  # ya procesado, o el mismo archivo llegó por portal: un solo aviso
    if adj.nombre.lower().endswith(".pdf"):
        texto = clasificador.texto_pdf(adj.contenido)
    else:
        texto = adj.contenido.decode("utf-8", errors="ignore")
    from src.features.documentos_nuevos.lectores import sueldos

    if adj.nombre.lower().endswith(".pdf") and sueldos.reconoce(texto):
        return sueldos.procesar(mail, adj, texto, sha, id_corrida)
    c = clasificador.clasificar(texto, clasificador.buscar_contacto_por_cuit)
    if not c.comprobante or not c.para_giamigli:
        return None  # no es comprobante, o es de otra sociedad: no se guarda ni avisa
    if c.id_contacto and c.numero and repository.mismo_comprobante(c.id_contacto, c.numero, c.modulo):
        return None  # otra copia del mismo comprobante (original y duplicado en el mismo mail)
    carpeta, nombre = clasificador.carpeta_y_nombre(c, adj.nombre)
    ruta = _guardar(carpeta, nombre, adj.contenido, sha)

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
        r = lectores.cargar_resumen(texto, adj.contenido, ruta)
        if r is None:
            motivo = "Importar el resumen desde Tesorería"
    elif estado == "para_cargar" and c.id_contacto and c.tipo != "recibo":
        r = lectores.cargar(c.tipo, c.id_contacto, c.contacto or "", c.numero, c.fecha, adj.contenido, ruta)
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
    repository.registrar_documento({
        "idRutinaCorrida": id_corrida, "origen": "mail", "mailEntryId": mail.entry_id, "mailRemitente": mail.remitente,
        "mailAsunto": mail.asunto, "mailRecibido": mail.recibido, "sha256": sha, "ruta": ruta, "tipo": c.tipo,
        "modulo": c.modulo, "idContacto": c.id_contacto, "fecha": c.fecha, "numero": c.numero, "total": c.total,
        "estado": estado, "motivo": motivo, "idRegistro": id_registro,
    })
    return estado


def sin_procesar(id_corrida: int | None, mail: mails.Mail, adj: mails.Adjunto) -> str | None:
    """Adjunto que no se pudo leer: se guarda en Compras del ejercicio y queda "sin clasificar" con aviso."""
    sha = hashlib.sha256(adj.contenido).hexdigest()
    if repository.adjunto_procesado(mail.entry_id, sha) or repository.existente(sha):
        return None
    carpeta = clasificador.COMPRAS / clasificador.carpeta_ejercicio(mail.recibido.date()).name
    ruta = _guardar(carpeta, f"{mail.recibido:%Y%m%d}_{Path(adj.nombre).name}", adj.contenido, sha)
    repository.registrar_documento({
        "idRutinaCorrida": id_corrida, "origen": "mail", "mailEntryId": mail.entry_id, "mailRemitente": mail.remitente,
        "mailAsunto": mail.asunto, "mailRecibido": mail.recibido, "sha256": sha, "ruta": ruta, "tipo": "otro",
        "modulo": "sin_clasificar", "estado": "para_cargar",
        "motivo": "Documento pendiente de procesamiento: no se pudo leer el archivo",
    })
    return "para_cargar"


def _mails(id_corrida: int, r: dict, problemas: list[str], ahora: datetime) -> None:
    try:
        for almacen in mails.nuevos(repository.marca_mails, ahora):
            if isinstance(almacen, Exception):
                log.warning("Rutina: no se pudo leer el almacén %s: %s", getattr(almacen, "almacen", "?"), almacen)
                continue  # almacenes sin bandeja de entrada (archivos) no son un problema para Sergio
            completo = True
            for mail in almacen.mails:
                r["mailsLeidos"] += 1
                for adj in mail.adjuntos:
                    try:
                        estado = procesar_adjunto(id_corrida, mail, adj)
                    except Exception:
                        log.exception("Rutina: falló el adjunto %s del mail %s", adj.nombre, mail.asunto)
                        try:  # un archivo que falla siempre no traba el almacén: queda pendiente de procesamiento
                            estado = sin_procesar(id_corrida, mail, adj)
                        except Exception:
                            log.exception("Rutina: no se pudo registrar el adjunto %s", adj.nombre)
                            completo = False
                            continue
                    if estado in ("cargado_solo", "para_cargar"):
                        r["documentosNuevos"] += 1
                        r["cargadosSolos"] += estado == "cargado_solo"
                        r["paraCargarAMano"] += estado == "para_cargar"
            if completo and almacen.ultimo:
                repository.fijar_marca_mails(almacen.nombre, almacen.ultimo)
            elif not completo:
                problemas.append(f"Mails de {almacen.nombre}: algún adjunto no se pudo procesar; se reintenta")
    except Exception:
        log.exception("Rutina: Outlook no respondió")
        problemas.append("Outlook no respondió: los mails quedan para la próxima corrida")


# --- Corrida -----------------------------------------------------------------



def _carpetas(id_corrida: int, r: dict, problemas: list[str]) -> None:
    """Verifica comprobantes e impuestos guardados en carpetas locales de Compras e Impuestos."""
    from src.features.documentos_nuevos import carpetas
    try:
        ejercicios = carpetas.ejercicios_a_revisar()
        conocidos = carpetas.archivos_en_base()
        for p in carpetas.listar_archivos_carpetas(ejercicios):
            try:
                estado = carpetas.procesar_archivo_carpeta(id_corrida, p, conocidos)
                if estado in ("cargado_solo", "para_cargar"):
                    r["documentosNuevos"] += 1
                    r["cargadosSolos"] += estado == "cargado_solo"
                    r["paraCargarAMano"] += estado == "para_cargar"
            except Exception:
                log.exception("Rutina: fallo al procesar archivo local %s", p.name)
    except Exception:
        log.exception("Rutina: no se pudieron verificar las carpetas locales")
        problemas.append("Carpetas locales: error al verificar archivos nuevos")


def correr(origen: str = "programada") -> int | None:
    """Una corrida completa. `None` si ya había otra en curso."""
    id_corrida = repository.abrir_corrida(origen)
    if id_corrida is None:
        return None
    r = {k: 0 for k in ("cuentasCorridas", "cuentasConProblemas", "mailsLeidos", "documentosNuevos",
                        "cargadosSolos", "paraCargarAMano")}
    problemas: list[str] = []
    avisos.fijar_corrida(id_corrida)
    try:
        _cuentas(r, problemas)
        _contar_portal(id_corrida, r)
        _mails(id_corrida, r, problemas, datetime.now())
        _carpetas(id_corrida, r, problemas)
    except Exception:
        log.exception("Rutina: falló la corrida %s", id_corrida)
        problemas.append("La corrida no pudo terminar; se reintenta en la próxima")
    finally:
        avisos.fijar_corrida(None)
        repository.cerrar_corrida(id_corrida, "con_problemas" if problemas else "ok", r, " · ".join(problemas) or None)
    return id_corrida


def tick(ahora: datetime | None = None) -> bool:
    """Llamado por el planificador cada minuto. Corre si venció la próxima corrida (una sola vez aunque se hayan
    perdido varios horarios) y recalcula la siguiente desde ahora. Devuelve si corrió."""
    prog = repository.programacion()
    if not prog or not prog["activa"]:
        return False
    ahora = ahora or datetime.now()
    if prog["proxima"] is None:  # activación: arranca en el próximo horario, sin correr ahora
        repository.fijar_proxima(proxima(prog["horarios"], ahora))
        return False
    vence = prog["proxima"]
    if isinstance(vence, str):
        vence = datetime.fromisoformat(vence.replace(" ", "T").split(".")[0])
    if vence > ahora:
        return False
    try:
        correr("programada")
    finally:
        repository.fijar_proxima(proxima(prog["horarios"], max(datetime.now(), ahora)))
    return True
