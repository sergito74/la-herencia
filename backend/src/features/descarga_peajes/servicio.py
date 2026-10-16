"""Ejecución de la descarga de peajes (037): la misma para el botón de la
aplicación y para la tarea semanal (FR-009).

- Una sola ejecución a la vez entre procesos (API y tarea programada):
  `sp_getapplock` de sesión sobre una conexión dedicada; si el proceso muere,
  SQL Server libera el lock solo (research.md R3).
- Cada portal es independiente: el error de uno no corta a los demás.
- Un documento se registra solo después de guardar su PDF: si la descarga
  falla, no queda registrado y se reintenta la próxima vez.
- `dry_run`: no escribe nada (ni base, ni disco, ni lock); solo informa.
- Nunca se loguean ni se guardan credenciales.
"""

from __future__ import annotations

import logging
import threading
import traceback

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.descarga_peajes import carga, portales, repository
from src.features.descarga_peajes.configuracion import credenciales_configuradas

log = logging.getLogger(__name__)
RECURSO_LOCK = "DescargaPeajes"


# --- Lock -------------------------------------------------------------------------

def tomar_lock():
    """Conexión dueña del lock, o `None` si otra ejecución lo tiene."""
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        r = conn.cursor().execute(
            "DECLARE @r int; EXEC @r = sp_getapplock @Resource = ?, @LockMode = 'Exclusive', "
            "@LockOwner = 'Session', @LockTimeout = 0; SELECT @r", (RECURSO_LOCK,),
        ).fetchone()[0]
    except Exception:
        conn.close()
        raise
    if r is None or r < 0:
        conn.close()
        return None
    return conn


def _soltar_lock(conn) -> None:
    try:
        conn.close()  # el lock de sesión se libera al cerrar la conexión
    except Exception:
        pass


# --- Ejecución --------------------------------------------------------------------

def _procesar_portal(pw, nombre: str, listar, id_ejecucion: int | None, dry_run: bool, informe: list) -> dict:
    res = {"estado": "ok", "nuevos": 0, "existentes": 0, "cargados": 0, "pendientes": 0, "error": None}
    if not credenciales_configuradas(nombre):
        return {**res, "estado": "sin_credenciales", "error": "Faltan credenciales: hay que correr el instalador"}
    errores: list[str] = []
    avisos: list[str] = []
    ctx = None
    try:
        docs, ctx, avisos = listar(pw)
        for d in docs:
            if repository.existe_clave(d["clave"]) or repository.existe_alguna(d.get("equivalentes", [])):
                res["existentes"] += 1
                continue
            try:
                contenido = d["bajar"]()
            except Exception as e:
                errores.append(f"No se pudo bajar {d['detalle']}: {e}")
                continue
            if not contenido.startswith(b"%PDF"):
                errores.append(f"{d['detalle']}: el portal no devolvió un PDF")
                continue
            ruta = portales.destino_libre(d["fecha"], d["proveedor"])
            if dry_run:
                r = carga.cargar(d["proveedor"], d["idContacto"], contenido, str(ruta), simular=True)
                informe.append({"portal": nombre, "detalle": d["detalle"], "archivo": ruta.name, **r})
                res["nuevos"] += 1
                continue
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(contenido)
            r = carga.cargar(d["proveedor"], d["idContacto"], contenido, str(ruta))
            repository.insertar_documento({
                "clave": d["clave"], "portal": nombre, "proveedor": d["proveedor"], "idContacto": d["idContacto"],
                "fecha": d["fecha"], "ruta": str(ruta), "idEjecucion": id_ejecucion, **r,
            })
            res["nuevos"] += 1
            if r["estadoCarga"] == "cargado_auto":
                res["cargados"] += 1
            elif r["estadoCarga"] == "pendiente":
                res["pendientes"] += 1
    except Exception as e:
        errores.append(str(e) if isinstance(e, portales.ErrorPortal) else f"Error inesperado: {e.__class__.__name__}: {e}")
        log.warning("Descarga de peajes, portal %s: %s", nombre, traceback.format_exc())
        res["estado"] = "error"
    finally:
        if ctx is not None:
            try:
                ctx.browser.close()
            except Exception:
                pass
    if errores:
        res["estado"] = "error"
    if errores or avisos:
        res["error"] = " · ".join(errores + avisos)[:400]
    return res


def ejecutar(origen: str, usuario: str | None, dry_run: bool = False, conexion_lock=None,
             id_ejecucion: int | None = None) -> dict:
    """Corre la descarga completa. Devuelve `{idEjecucion, estado, portales, informe}`
    (`informe` solo en dry-run). Código de salida sugerido en `codigo` (0/1/2)."""
    from playwright.sync_api import sync_playwright

    if dry_run:
        informe: list = []
        resultados = {}
        with sync_playwright() as pw:
            for nombre, listar in portales.PORTALES:
                resultados[nombre] = _procesar_portal(pw, nombre, listar, None, True, informe)
        return {"idEjecucion": None, "estado": "simulacion", "portales": resultados, "informe": informe, "codigo": 0}

    lock = conexion_lock or tomar_lock()
    if lock is None:
        id_salteada = repository.crear_ejecucion(origen, usuario, "salteada", "Había otra descarga en curso")
        return {"idEjecucion": id_salteada, "estado": "salteada", "portales": {}, "codigo": 2}
    try:
        if id_ejecucion is None:
            id_ejecucion = repository.crear_ejecucion(origen, usuario)
        repository.marcar_incompletas(excepto=id_ejecucion)
        if not portales.COMPRAS.exists():
            repository.cerrar_ejecucion(id_ejecucion, "con_errores",
                                        f"No está disponible la carpeta de Compras ({portales.COMPRAS})")
            return {"idEjecucion": id_ejecucion, "estado": "con_errores", "portales": {}, "codigo": 1}
        for nombre, _ in portales.PORTALES:
            repository.crear_portal(id_ejecucion, nombre)
        resultados = {}
        with sync_playwright() as pw:
            for nombre, listar in portales.PORTALES:
                repository.actualizar_portal(id_ejecucion, nombre, "en_curso")
                r = _procesar_portal(pw, nombre, listar, id_ejecucion, False, [])
                repository.actualizar_portal(id_ejecucion, nombre, r["estado"], nuevos=r["nuevos"],
                                             existentes=r["existentes"], cargados=r["cargados"],
                                             pendientes=r["pendientes"], error=r["error"])
                resultados[nombre] = r
        estado = "completa" if all(r["estado"] == "ok" for r in resultados.values()) else "con_errores"
        repository.cerrar_ejecucion(id_ejecucion, estado)
        return {"idEjecucion": id_ejecucion, "estado": estado, "portales": resultados, "codigo": 0}
    except Exception as e:
        log.error("Descarga de peajes: %s", traceback.format_exc())
        if id_ejecucion is not None:
            repository.cerrar_ejecucion(id_ejecucion, "con_errores", f"Error general: {e.__class__.__name__}: {e}"[:400])
        return {"idEjecucion": id_ejecucion, "estado": "con_errores", "portales": {}, "codigo": 1}
    finally:
        _soltar_lock(lock)


def iniciar_en_segundo_plano(usuario: str | None) -> tuple[int | None, int | None]:
    """El lock se decide acá, dentro de la petición HTTP, antes de responder:
    devuelve `(idEjecucion, None)` si arrancó o `(None, idEnCurso)` para el 409."""
    lock = tomar_lock()
    if lock is None:
        en_curso = repository.ejecucion_en_curso()
        return None, (en_curso or {}).get("idEjecucion")
    try:
        id_ejecucion = repository.crear_ejecucion("manual", usuario)
    except Exception:
        _soltar_lock(lock)
        raise
    threading.Thread(
        target=ejecutar, kwargs={"origen": "manual", "usuario": usuario, "conexion_lock": lock,
                                 "id_ejecucion": id_ejecucion},
        daemon=True, name=f"descarga-peajes-{id_ejecucion}",
    ).start()
    return id_ejecucion, None
