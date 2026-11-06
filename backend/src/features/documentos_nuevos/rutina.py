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
import threading
from datetime import datetime, time, timedelta
from pathlib import Path

from src.features.documentos_nuevos import avisos, clasificador, lectores, mails, repository

log = logging.getLogger(__name__)

# Pedidos desde la pantalla ('documentos' o 'portales'): los atiende el hilo del planificador, de a uno, para no
# abrir dos navegadores a la vez.
ALCANCES = ("documentos", "portales", "todo")
_pedidos: list[str] = []
_lock_pedidos = threading.Lock()


def pedir(alcance: str) -> None:
    if alcance not in ALCANCES:
        raise ValueError(f"Alcance desconocido: {alcance}")
    with _lock_pedidos:
        if alcance not in _pedidos:
            _pedidos.append(alcance)


def pedidos_pendientes() -> list[str]:
    with _lock_pedidos:
        return list(_pedidos)


def _tomar_pedido() -> str | None:
    with _lock_pedidos:
        return _pedidos.pop(0) if _pedidos else None

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

# 04/11/2026: un portal colgado (ARCA Sergio, Movistar) frenaba la corrida entera y los mails nunca se leían.
LIMITE_PORTAL = 10 * 60  # red de seguridad: el vigilante de la bóveda corta antes (2' sin avance, 8' total)


def _correr_con_limite(servicio, p: dict) -> str:
    """Corre el portal en un hilo aparte; si no termina a tiempo se sigue (el hilo queda con su lock y su corrida
    'en curso', así la próxima lo saltea en vez de abrir otro navegador)."""
    salida: dict = {}

    def trabajo():
        try:
            salida["estado"] = servicio.correr_portal(p["idPortal"], "programada", "sistema")[1]
        except Exception:
            log.exception("Rutina: falló la cuenta %s", p["idPortal"])
            salida["estado"] = "error"

    hilo = threading.Thread(target=trabajo, daemon=True, name=f"rutina-portal-{p['idPortal']}")
    hilo.start()
    hilo.join(LIMITE_PORTAL)
    if hilo.is_alive():
        log.warning("Rutina: la cuenta %s no terminó en %s s; se sigue", p["idPortal"], LIMITE_PORTAL)
        return "colgada"
    return salida.get("estado", "error")


def _cuentas(r: dict, problemas: list[str]) -> None:
    from src.features.boveda import repository as boveda, servicio

    sin_red = False
    for p in repository.portales_sincronizables():
        # Sin internet no se intenta el portal (03/11/2026: un corte dejó 4 cuentas "con error"); se espera hasta 2'.
        if sin_red or not servicio.esperar_internet(120):
            sin_red = True
            problemas.append(f"{p['nombre']}: sin conexión a internet, se salteó")
            r["cuentasConProblemas"] += 1
            continue
        if boveda.corrida_en_curso(p["idPortal"]) is not None:
            problemas.append(f"{p['nombre']}: estaba sincronizando, se salteó")
            r["cuentasConProblemas"] += 1
            continue
        estado = _correr_con_limite(servicio, p)
        if estado == "colgada":
            problemas.append(f"{p['nombre']}: no terminó en {LIMITE_PORTAL // 60} minutos, se siguió con las demás")
            r["cuentasCorridas"] += 1
            r["cuentasConProblemas"] += 1
            continue
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
    if contenido.lstrip()[:5] == b"<?xml":  # el nombre lo arma el clasificador siempre como .pdf
        nombre = str(Path(nombre).with_suffix(".xml"))
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
    """Devuelve el estado registrado (`cargado_solo`, `para_cargar`, `ya_estaba`) o `None` si se ignoró.
    La decisión vive en `proceso` (común con las carpetas locales)."""
    from src.features.documentos_nuevos import proceso

    if adj.nombre.lower().endswith(".xml") and any(a.nombre.lower().endswith(".pdf") for a in mail.adjuntos):
        return None  # 04/11/2026: XML de autorización de ARCA junto a su PDF (Starlink): es el mismo comprobante
    sha = hashlib.sha256(adj.contenido).hexdigest()
    if repository.adjunto_procesado(mail.entry_id, sha) or repository.existente(sha):
        return None  # ya procesado, o el mismo archivo llegó por portal: un solo aviso
    bloques = proceso.textos_de(adj.nombre, adj.contenido)
    texto = bloques[0].texto
    from src.features.documentos_nuevos.lectores import sueldos

    if adj.nombre.lower().endswith(".pdf") and sueldos.reconoce(texto):
        return sueldos.procesar(mail, adj, texto, sha, id_corrida)
    origen = {"idRutinaCorrida": id_corrida, "mailEntryId": mail.entry_id, "mailRemitente": mail.remitente,
              "mailAsunto": mail.asunto, "mailRecibido": mail.recibido}
    if adj.nombre.lower().endswith(".pdf") and not texto.strip():
        # Escaneo sin texto: solo si el remitente es un proveedor conocido (un mail personal no entra).
        emisor = clasificador.contacto_por_remitente(mail.remitente)
        if not emisor:
            return None
        c = proceso.escaneo(*emisor)
        carpeta, nombre = clasificador.carpeta_y_nombre(c, adj.nombre)
        ruta = _guardar(carpeta, nombre, adj.contenido, sha)
        return proceso.registrar(origen, c, sha, ruta, "para_cargar", c.motivo, None)
    if not clasificador.dirigido_a_la_empresa(texto):
        return None  # mail personal: no se guarda ni avisa
    estado_final, ruta = None, None
    for b in bloques:
        c = proceso.clasificar(b.texto, mail.remitente)
        if not c.comprobante or not c.para_giamigli:
            continue  # no es comprobante, o es de otra sociedad: no se guarda ni avisa
        if c.id_contacto and c.numero and repository.mismo_comprobante(c.id_contacto, c.numero, c.modulo):
            continue  # otra copia del mismo comprobante (original y duplicado en el mismo mail)
        if ruta is None:
            carpeta, nombre = clasificador.carpeta_y_nombre(c, adj.nombre)
            ruta = _guardar(carpeta, nombre, adj.contenido, sha)
        estado, motivo, id_registro = proceso.resolver(c, b.texto, adj.contenido, ruta)
        e = proceso.registrar(origen, c, b.sha, ruta, estado, motivo, id_registro)
        estado_final = estado_final or e
    return estado_final


def sin_procesar(id_corrida: int | None, mail: mails.Mail, adj: mails.Adjunto) -> str | None:
    """Adjunto que no se pudo leer: se guarda en Compras del ejercicio y queda "sin clasificar" con aviso.
    06/11/2026: solo si el remitente es un proveedor conocido (como los escaneos); los resúmenes personales de Sergio
    (ICBC, PDF con clave) entraban a Compras de Giamigli."""
    if not clasificador.contacto_por_remitente(mail.remitente):
        return None
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


def _reevaluar(problemas: list[str]) -> None:
    from src.features.documentos_nuevos import carpetas
    try:
        carpetas.reevaluar_pendientes()
    except Exception:
        log.exception("Rutina: no se pudieron reevaluar los pendientes sin contacto")
        problemas.append("No se pudieron reevaluar los pendientes sin emisor")


def correr(origen: str = "programada", alcance: str = "todo") -> int | None:
    """Una corrida. `alcance`: 'documentos' (mails + carpetas de Compras e Impuestos), 'portales' (cuentas de la
    bóveda) o 'todo'. `None` si ya había otra en curso."""
    id_corrida = repository.abrir_corrida(origen, alcance)
    if id_corrida is None:
        return None
    r = {k: 0 for k in ("cuentasCorridas", "cuentasConProblemas", "mailsLeidos", "documentosNuevos",
                        "cargadosSolos", "paraCargarAMano")}
    problemas: list[str] = []
    avisos.fijar_corrida(id_corrida)
    try:
        if alcance in ("documentos", "todo"):
            _mails(id_corrida, r, problemas, datetime.now())  # primero: es rápido y no depende de ningún portal
        if alcance in ("portales", "todo"):
            _cuentas(r, problemas)
            _contar_portal(id_corrida, r)
        if alcance in ("documentos", "todo"):
            _carpetas(id_corrida, r, problemas)
        _reevaluar(problemas)
    except Exception:
        log.exception("Rutina: falló la corrida %s", id_corrida)
        problemas.append("La corrida no pudo terminar; se reintenta en la próxima")
    finally:
        avisos.fijar_corrida(None)
        repository.cerrar_corrida(id_corrida, "con_problemas" if problemas else "ok", r, " · ".join(problemas) or None)
    return id_corrida


# 06/11/2026 (Sergio): las búsquedas son a pedido; si una no corrió en 2 días, corre sola.
SIN_CORRER_MAXIMO = timedelta(days=2)


def _vencida(alcance: str, ahora: datetime) -> bool:
    u = repository.ultima_corrida(alcance)
    if not u:
        return True
    inicio = u["inicio"]
    if isinstance(inicio, str):
        inicio = datetime.fromisoformat(inicio.replace(" ", "T").split(".")[0])
    return inicio is None or ahora - inicio >= SIN_CORRER_MAXIMO


def tick(ahora: datetime | None = None) -> bool:
    """Llamado por el planificador cada minuto. Atiende primero los pedidos de la pantalla; si no hay, corre sola la
    búsqueda (mails y carpetas, o portales) que lleva 2 días o más sin correr. Devuelve si corrió."""
    pedido = _tomar_pedido()
    if pedido:
        correr("programada", pedido)
        return True
    ahora = ahora or datetime.now()
    for alcance in ("documentos", "portales"):
        if _vencida(alcance, ahora):
            correr("programada", alcance)
            return True
    return False
