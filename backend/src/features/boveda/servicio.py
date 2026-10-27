"""Corrida de un portal de la bóveda (042, US2/US3/US4).

- Un portal a la vez: `sp_getapplock` de sesión `boveda-portal-<id>` sobre una
  conexión dedicada; si el proceso muere, SQL Server libera el lock solo.
- Sin autorización vigente no se entra; se vuelve a verificar antes de cada
  descarga, así una revocación detiene la corrida en curso (FR-008).
- Las credenciales se descifran solo acá, como `Secreto`, y se pasan al
  conector; nunca se guardan ni se loguean.
- Credenciales rechazadas: no se reintenta, se marca la credencial y se
  suspende la programación hasta que se cambie la clave (FR-011).
- Un documento se registra solo después de guardar su PDF en la carpeta de
  Compras del ejercicio; si la descarga falla, se reintenta la próxima vez.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import traceback
from datetime import date
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.boveda import carga, cifrado, estado_cuenta, repository
from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, PortalCambio, RequiereIntervencion, cargar_conectores,
)
from src.features.descarga_peajes.portales import COMPRAS, carpeta_ejercicio

log = logging.getLogger(__name__)

# Portales esperando turno en una tanda manual ("Sincronizar seleccionados" / "todos"). Vive en el proceso del
# backend, que es uno solo: alcanza para mostrar "En cola" y para no encolar dos veces el mismo portal.
_cola: list[int] = []
_cola_lock = threading.Lock()


def en_cola() -> list[int]:
    with _cola_lock:
        return list(_cola)


class SinAutorizacion(Exception):
    pass


# --- Lock -------------------------------------------------------------------------

def _recurso(id_portal: int) -> str:
    return f"boveda-portal-{id_portal}"


def tomar_lock(id_portal: int):
    """Conexión dueña del lock del portal, o `None` si otra corrida lo tiene."""
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        cur.execute(
            "SET NOCOUNT ON; DECLARE @r int; EXEC @r = sp_getapplock @Resource = ?, @LockMode = 'Exclusive', "
            "@LockOwner = 'Session', @LockTimeout = 0; SELECT @r", (_recurso(id_portal),),
        )
        while cur.description is None:  # mismo patrón que connection.reconciliation_transaction
            if not cur.nextset():
                raise RuntimeError("El bloqueo del portal no devolvió resultado.")
        r = cur.fetchone()[0]
    except Exception:
        conn.close()
        raise
    if r is None or r < 0:
        conn.close()
        return None
    return conn


def _soltar_lock(conn, id_portal: int | None = None) -> None:
    """Libera el applock explícitamente: con el pooling del driver ODBC, `close()` solo devuelve la
    sesión al pool y el lock seguiría tomado hasta que la conexión se recicle."""
    try:
        if id_portal is not None:
            conn.cursor().execute("EXEC sp_releaseapplock @Resource = ?, @LockOwner = 'Session'", (_recurso(id_portal),))
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass


def _enmascarar(texto: str | None, cred: Credencial | None) -> str | None:
    """Ningún mensaje guardado o logueado lleva usuario ni clave, aunque una excepción los incluya."""
    if not texto or cred is None:
        return texto
    valores = [cred.usuario or "", cred.clave.valor() if cred.clave else ""]
    valores += [v.valor() if hasattr(v, "valor") else "" for v in cred.datos.values()]
    for v in sorted((v for v in valores if v and len(v) >= 3), key=len, reverse=True):
        texto = texto.replace(v, "***")
    return texto


# --- Credencial -------------------------------------------------------------------

def credencial_de(id_credencial: int | None) -> Credencial | None:
    if not id_credencial:
        return None
    blob = repository.leer_clave_cifrada(id_credencial)
    fila = repository.obtener_credencial(id_credencial)
    if not blob or not fila:
        return None
    datos = {}
    for d in repository.leer_datos(id_credencial):
        datos[d["nombre"]] = (cifrado.descifrar(d["valorCifrado"], cifrado.aad_dato(id_credencial, d["nombre"]))
                              if d["secreto"] else d["valorTexto"])
    return Credencial(usuario=fila["usuario"], clave=cifrado.descifrar(blob, cifrado.aad_clave(id_credencial)), datos=datos)


# --- Corrida ----------------------------------------------------------------------

def _verificar_autorizacion(id_portal: int) -> None:
    if repository.autorizacion_vigente(id_portal) is None:
        raise SinAutorizacion("Falta autorización: el sistema no entra a este portal")


VENTAS = COMPRAS.parent / "Ventas"


def _carpeta(tipo: str, fecha: date) -> Path:
    """Carpeta donde Sergio ya guarda cada clase de documento: liquidaciones de granos en Ventas del
    ejercicio, certificados de retención en Ventas/Retenciones del ejercicio, el resto en Compras."""
    ejercicio = carpeta_ejercicio(fecha).name
    if tipo == "liquidacion":
        return VENTAS / ejercicio
    if tipo == "certificado":
        return VENTAS / f"Retenciones {ejercicio}"
    return COMPRAS / ejercicio


def _destino(carpeta: Path, fecha: date, proveedor: str) -> Path:
    """`AAAAMMDD_Proveedor.pdf` en la carpeta; si existe, " 001", " 002"... Nunca pisa un archivo."""
    base = f"{fecha:%Y%m%d}_{proveedor}"
    ruta, n = carpeta / f"{base}.pdf", 1
    while ruta.exists():
        ruta, n = carpeta / f"{base} {n:03d}.pdf", n + 1
    return ruta


def _archivo_igual(carpeta: Path, sha: str, indice: dict[Path, dict[str, str]]) -> str | None:
    """Archivo idéntico ya guardado a mano en la carpeta (cualquier nombre): se reusa en vez de duplicarlo."""
    if carpeta not in indice:
        indice[carpeta] = {hashlib.sha256(f.read_bytes()).hexdigest(): str(f)
                           for f in carpeta.glob("*.pdf")} if carpeta.exists() else {}
    return indice[carpeta].get(sha)


def _archivo_de_compra(doc) -> str | None:
    """Comprobante ya cargado en Compras con su archivo: se usa ese archivo en vez de guardar otra copia
    (el PDF del portal puede no ser idéntico byte a byte al guardado a mano)."""
    if doc.tipo not in carga.TIPOS_COMPROBANTE or not (doc.numero and doc.id_contacto):
        return None
    id_compra = repository.compra_existente(doc.id_contacto, doc.numero, None)
    ruta = repository.documento_original(id_compra) if id_compra else None
    return ruta if ruta and Path(ruta).exists() else None


def _procesar(portal: dict, conector, cred: Credencial, id_corrida: int) -> dict:
    from playwright.sync_api import sync_playwright

    res = {"nuevos": 0, "existentes": 0, "cargados": 0, "pendientes": 0}
    errores: list[str] = []
    indice: dict[Path, dict[str, str]] = {}
    sesion = None
    with sync_playwright() as pw:
        try:
            repository.avance(id_corrida, "Ingresando al portal…")
            sesion = conector.ingresar(pw, cred)
            repository.avance(id_corrida, "Buscando documentos en el portal…")
            docs = conector.listar_documentos(sesion)
            total = len(docs)
            repository.avance(id_corrida, f"El portal ofrece {total} documentos; revisando cuáles faltan…", 0, total)
            for i, doc in enumerate(docs, start=1):
                _verificar_autorizacion(portal["idPortal"])
                if repository.existe_documento(portal["idPortal"], doc.clave) or repository.existe_equivalente(doc.equivalentes):
                    res["existentes"] += 1
                    if i % 10 == 0 or i == total:
                        repository.avance(id_corrida, f"Revisados {i} de {total} (ya estaban {res['existentes']})", i, total,
                                          **res)
                    continue
                repository.avance(id_corrida, f"Descargando {i} de {total}: {doc.detalle or doc.proveedor}", i - 1, total, **res)
                try:
                    contenido = doc.bajar()
                except Exception as e:
                    errores.append(f"No se pudo bajar {doc.detalle or doc.clave}: {e}")
                    continue
                if not contenido.startswith(b"%PDF"):
                    errores.append(f"{doc.detalle or doc.clave}: el portal no devolvió un PDF")
                    continue
                sha = hashlib.sha256(contenido).hexdigest()
                fecha = doc.fecha or date.today()
                carpeta = _carpeta(doc.tipo, fecha)
                ruta_igual = (repository.existe_sha(sha) or _archivo_igual(carpeta, sha, indice)
                              or _archivo_de_compra(doc))
                if ruta_igual:
                    ruta = ruta_igual
                else:
                    destino = _destino(carpeta, fecha, doc.proveedor)
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    destino.write_bytes(contenido)
                    ruta = str(destino)
                r = carga.cargar(conector, doc, contenido, ruta)
                repository.insertar_documento({
                    "idPortal": portal["idPortal"], "clave": doc.clave, "tipo": doc.tipo, "proveedor": doc.proveedor,
                    "idContacto": doc.id_contacto, "fecha": doc.fecha, "moneda": doc.moneda, "ruta": ruta,
                    "sha256": sha, "idCorrida": id_corrida, **r,
                })
                res["nuevos"] += 1
                if r["estadoCarga"] == "cargado_auto":
                    res["cargados"] += 1
                elif r["estadoCarga"] == "pendiente":
                    res["pendientes"] += 1
                repository.avance(id_corrida, f"Procesados {i} de {total}", i, total, **res)
            if conector.tiene_estado_cuenta:
                _verificar_autorizacion(portal["idPortal"])
                repository.avance(id_corrida, "Leyendo el estado de cuenta…", total, total, **res)
                for foto in conector.estado_cuenta(sesion):
                    estado_cuenta.guardar(portal["idPortal"], id_corrida, portal["idContacto"], foto)
        finally:
            if sesion is not None:
                try:
                    conector.cerrar(sesion)
                except Exception:
                    pass
    res["errores"] = errores
    return res


def ejecutar(id_portal: int, origen: str, usuario: str | None, lock, id_corrida: int) -> str:
    """Corre un portal teniendo ya el lock y la corrida creada. Devuelve el estado final."""
    portal = repository.portal_para_correr(id_portal)
    cred = None
    estado, mensaje, res = "error", None, {"nuevos": 0, "existentes": 0, "cargados": 0, "pendientes": 0}
    try:
        repository.avance(id_corrida, "Preparando…")
        conector = cargar_conectores().get(portal["codigoConector"]) if portal else None
        if conector is None:
            estado, mensaje = "error", "Esta cuenta todavía no tiene sincronización automática"
            return estado
        _verificar_autorizacion(id_portal)
        cred = credencial_de(portal["idCredencial"])
        if cred is None:
            estado, mensaje = "sin_credenciales", "Faltan usuario o contraseña en la bóveda"
            return estado
        if not COMPRAS.exists():
            estado, mensaje = "error", f"No está disponible la carpeta de Compras ({COMPRAS})"
            return estado
        res = _procesar(portal, conector, cred, id_corrida)
        errores = res.pop("errores")
        estado = "error" if errores else "ok"
        mensaje = " · ".join(errores) or None
    except SinAutorizacion as e:
        estado, mensaje = "sin_autorizacion", str(e)
    except CredencialesRechazadas:
        estado, mensaje = "credenciales_rechazadas", "El portal rechazó usuario o contraseña: actualizarla en la bóveda"
        repository.marcar_rechazada(portal["idCredencial"])
        repository.suspender(id_portal, "Credenciales rechazadas: cambiar la contraseña para reanudar")
        repository.auditar("suspension", "sistema", id_portal=id_portal, detalle="credenciales rechazadas")
    except RequiereIntervencion as e:
        estado, mensaje = "requiere_intervencion", f"El portal pide verificación humana (captcha o código): {e}"
    except PortalCambio as e:
        estado, mensaje = "portal_cambio", f"El portal cambió su página: {e}"
    except cifrado.ClaveMaestraNoDisponible as e:
        estado, mensaje = "error", str(e)
    except Exception as e:
        log.warning("Bóveda, portal %s: %s", id_portal, _enmascarar(traceback.format_exc(), cred))
        estado, mensaje = "error", f"{e.__class__.__name__}: {e}"
    finally:
        repository.cerrar_corrida(id_corrida, estado, mensaje=_enmascarar(mensaje, cred), **res)
        repository.auditar("corrida", usuario, id_portal=id_portal, detalle=f"{origen} #{id_corrida}: {estado}")
        _soltar_lock(lock, id_portal)
    return estado


def correr_portal(id_portal: int, origen: str, usuario: str | None) -> tuple[int, str]:
    """Corrida sincrónica (planificador). Devuelve `(idCorrida, estado)`."""
    lock = tomar_lock(id_portal)
    if lock is None:
        return repository.crear_corrida(id_portal, origen, usuario, "salteada", "Había otra corrida en curso"), "salteada"
    try:
        repository.marcar_incompletas(id_portal)
        id_corrida = repository.crear_corrida(id_portal, origen, usuario)
    except Exception:
        _soltar_lock(lock, id_portal)
        raise
    return id_corrida, ejecutar(id_portal, origen, usuario, lock, id_corrida)


def correr_varios_en_segundo_plano(ids: list[int], usuario: str | None) -> list[int]:
    """Tanda manual: uno por vez en un solo hilo, para no abrir varios navegadores a la vez. No encola un portal
    que ya está en cola o corriendo. Devuelve los que se encolaron."""
    with _cola_lock:
        nuevos = [i for i in dict.fromkeys(ids) if i not in _cola and repository.corrida_en_curso(i) is None]
        _cola.extend(nuevos)

    def serie():
        for id_portal in nuevos:
            try:
                correr_portal(id_portal, "manual", usuario)
            except Exception:
                log.exception("Bóveda: falló la corrida manual del portal %s", id_portal)
            finally:
                with _cola_lock:
                    if id_portal in _cola:
                        _cola.remove(id_portal)

    if nuevos:
        threading.Thread(target=serie, daemon=True, name="boveda-corrida-tanda").start()
    return nuevos
