"""Registro de la descarga de peajes en `WC` (037, data-model.md).

Tablas: dbo.DescargaPeajes_Ejecuciones, dbo.DescargaPeajes_EjecucionPortales,
dbo.DescargaPeajes_Documentos. Solo SQL parametrizado; las compras se crean
en `carga.py` con el repositorio de Compras.
"""

from __future__ import annotations

from src.db.connection import execute_insert_returning_id, execute_write, fetch_all, fetch_one

LIMITE_MAXIMO = 100

_COLS_EJECUCION = """
    e.IdEjecucion AS idEjecucion, e.Origen AS origen, e.Usuario AS usuario, e.Inicio AS inicio,
    e.Fin AS fin, e.Estado AS estado, e.Mensaje AS mensaje
"""
_COLS_DOCUMENTO = """
    d.IdDocumento AS idDocumento, d.Portal AS portal, d.Proveedor AS proveedor, d.IdContacto AS idContacto,
    d.FechaDocumento AS fechaDocumento, d.NumeroDocumento AS numeroDocumento, d.TotalImpreso AS totalImpreso,
    d.Ruta AS ruta, d.EstadoCarga AS estadoCarga, d.Motivo AS motivo, d.IdCompra AS idCompra,
    d.IdEjecucion AS idEjecucion
"""


# --- Ejecuciones -------------------------------------------------------------

def crear_ejecucion(origen: str, usuario: str | None, estado: str = "en_curso", mensaje: str | None = None) -> int:
    return execute_insert_returning_id(
        "INSERT INTO dbo.DescargaPeajes_Ejecuciones (Origen, Usuario, Estado, Mensaje, Fin) "
        "OUTPUT INSERTED.IdEjecucion VALUES (?, ?, ?, ?, CASE WHEN ? = 'en_curso' THEN NULL ELSE SYSDATETIME() END)",
        (origen, usuario, estado, mensaje, estado),
    )


def cerrar_ejecucion(id_ejecucion: int, estado: str, mensaje: str | None = None) -> None:
    execute_write(
        "UPDATE dbo.DescargaPeajes_Ejecuciones SET Estado = ?, Mensaje = COALESCE(?, Mensaje), Fin = SYSDATETIME() "
        "WHERE IdEjecucion = ?",
        (estado, mensaje, id_ejecucion),
    )


def marcar_incompletas(excepto: int | None = None) -> int:
    """Ejecuciones que quedaron `en_curso` sin un proceso vivo (quien llama ya tiene el lock)."""
    return execute_write(
        "UPDATE dbo.DescargaPeajes_Ejecuciones SET Estado = 'incompleta', Fin = SYSDATETIME(), "
        "Mensaje = COALESCE(Mensaje, N'Se interrumpió antes de terminar') "
        "WHERE Estado = 'en_curso' AND IdEjecucion <> ?",
        (excepto or 0,),
    )


def ejecucion_en_curso() -> dict | None:
    return fetch_one(
        f"SELECT TOP 1 {_COLS_EJECUCION} FROM dbo.DescargaPeajes_Ejecuciones e "
        "WHERE e.Estado = 'en_curso' ORDER BY e.IdEjecucion DESC"
    )


def crear_portal(id_ejecucion: int, portal: str) -> None:
    execute_write(
        "INSERT INTO dbo.DescargaPeajes_EjecucionPortales (IdEjecucion, Portal, Estado) VALUES (?, ?, 'pendiente')",
        (id_ejecucion, portal),
    )


def actualizar_portal(id_ejecucion: int, portal: str, estado: str, *, nuevos: int = 0, existentes: int = 0,
                      cargados: int = 0, pendientes: int = 0, error: str | None = None) -> None:
    execute_write(
        "UPDATE dbo.DescargaPeajes_EjecucionPortales SET Estado = ?, Nuevos = ?, Existentes = ?, Cargados = ?, "
        "Pendientes = ?, Error = ? WHERE IdEjecucion = ? AND Portal = ?",
        (estado, nuevos, existentes, cargados, pendientes, (error or None) and error[:400], id_ejecucion, portal),
    )


def _portales_de(ids: list[int]) -> dict[int, list[dict]]:
    if not ids:
        return {}
    marcas = ",".join("?" for _ in ids)
    filas = fetch_all(
        "SELECT IdEjecucion AS idEjecucion, Portal AS portal, Estado AS estado, Nuevos AS nuevos, "
        "Existentes AS existentes, Cargados AS cargados, Pendientes AS pendientes, Error AS error "
        f"FROM dbo.DescargaPeajes_EjecucionPortales WHERE IdEjecucion IN ({marcas}) ORDER BY IdEjecucion, Portal",
        tuple(ids),
    )
    resultado: dict[int, list[dict]] = {}
    for f in filas:
        resultado.setdefault(f.pop("idEjecucion"), []).append(f)
    return resultado


def listar_ejecuciones(limite: int = 20, desde: int = 0) -> tuple[list[dict], int]:
    limite = max(1, min(limite, LIMITE_MAXIMO))
    items = fetch_all(
        f"SELECT {_COLS_EJECUCION} FROM dbo.DescargaPeajes_Ejecuciones e "
        "ORDER BY e.IdEjecucion DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        (max(0, desde), limite),
    )
    portales = _portales_de([i["idEjecucion"] for i in items])
    for i in items:
        i["portales"] = portales.get(i["idEjecucion"], [])
    total = fetch_one("SELECT COUNT(*) AS n FROM dbo.DescargaPeajes_Ejecuciones")["n"]
    return items, total


def obtener_ejecucion(id_ejecucion: int) -> dict | None:
    e = fetch_one(f"SELECT {_COLS_EJECUCION} FROM dbo.DescargaPeajes_Ejecuciones e WHERE e.IdEjecucion = ?",
                  (id_ejecucion,))
    if e is None:
        return None
    e["portales"] = _portales_de([id_ejecucion]).get(id_ejecucion, [])
    e["documentos"] = fetch_all(
        f"SELECT {_COLS_DOCUMENTO} FROM dbo.DescargaPeajes_Documentos d WHERE d.IdEjecucion = ? ORDER BY d.IdDocumento",
        (id_ejecucion,),
    )
    return e


# --- Documentos --------------------------------------------------------------

def existe_clave(clave: str) -> bool:
    return fetch_one("SELECT 1 AS x FROM dbo.DescargaPeajes_Documentos WHERE Clave = ?", (clave,)) is not None


def existe_alguna(patrones: list[str]) -> bool:
    """La misma factura ofrecida por otro portal (ej. AUBASA en TelePASE y en su oficina virtual)."""
    for patron in patrones:
        if fetch_one("SELECT 1 AS x FROM dbo.DescargaPeajes_Documentos WHERE Clave LIKE ?", (patron,)):
            return True
    return False


def insertar_documento(doc: dict) -> int:
    return execute_insert_returning_id(
        "INSERT INTO dbo.DescargaPeajes_Documentos (Clave, Portal, Proveedor, IdContacto, FechaDocumento, "
        "NumeroDocumento, TotalImpreso, Ruta, IdEjecucion, EstadoCarga, Motivo, IdCompra) "
        "OUTPUT INSERTED.IdDocumento VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (doc["clave"], doc["portal"], doc["proveedor"], doc.get("idContacto"), doc.get("fecha"),
         doc.get("numeroDocumento"), doc.get("totalImpreso"), doc.get("ruta"), doc.get("idEjecucion"),
         doc["estadoCarga"], (doc.get("motivo") or None) and doc["motivo"][:300], doc.get("idCompra")),
    )


def listar_documentos(estado: str | None, limite: int = 50, desde: int = 0) -> tuple[list[dict], int]:
    limite = max(1, min(limite, LIMITE_MAXIMO))
    filtro, params = ("WHERE d.EstadoCarga = ?", (estado,)) if estado else ("WHERE d.EstadoCarga <> 'historico'", ())
    items = fetch_all(
        f"SELECT {_COLS_DOCUMENTO} FROM dbo.DescargaPeajes_Documentos d {filtro} "
        "ORDER BY d.IdDocumento DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        params + (max(0, desde), limite),
    )
    total = fetch_one(f"SELECT COUNT(*) AS n FROM dbo.DescargaPeajes_Documentos d {filtro}", params)["n"]
    return items, total


def compra_existente(id_contacto: int | None, numero: str | None, ruta: str | None) -> int | None:
    """Compra ya cargada para este documento: mismo archivo como documento
    original, o mismo proveedor y número de comprobante."""
    if ruta:
        # Ruta exacta, o el formato heredado del Access "ruta#ruta#" (no un prefijo cualquiera).
        fila = fetch_one("SELECT TOP 1 IdDeuda AS id FROM dbo.Compras WHERE [Documento Original] = ? "
                         "OR [Documento Original] LIKE ?",
                         (ruta, ruta.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]") + "#%"))
        if fila:
            return fila["id"]
    if id_contacto and numero:
        fila = fetch_one("SELECT TOP 1 IdDeuda AS id FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?",
                         (id_contacto, numero))
        if fila:
            return fila["id"]
    return None


def revalidar_pendientes() -> int:
    """R8: un pendiente que ya tiene compra (cargada por la pantalla de
    Compras) pasa a `ya_cargado`. Devuelve cuántos cambiaron."""
    cambiados = 0
    for d in fetch_all("SELECT IdDocumento AS id, IdContacto AS c, NumeroDocumento AS n, Ruta AS r "
                       "FROM dbo.DescargaPeajes_Documentos WHERE EstadoCarga = 'pendiente'"):
        id_compra = compra_existente(d["c"], d["n"], d["r"])
        if id_compra:
            execute_write("UPDATE dbo.DescargaPeajes_Documentos SET EstadoCarga = 'ya_cargado', IdCompra = ? "
                          "WHERE IdDocumento = ? AND EstadoCarga = 'pendiente'", (id_compra, d["id"]))
            cambiados += 1
    return cambiados


def resumen() -> dict:
    """FR-020: pendientes de carga manual + portales con error en su última ejecución."""
    pendientes = fetch_one("SELECT COUNT(*) AS n FROM dbo.DescargaPeajes_Documentos WHERE EstadoCarga = 'pendiente'")["n"]
    con_error = fetch_one(
        "SELECT COUNT(*) AS n FROM ("
        " SELECT p.Portal, p.Estado, ROW_NUMBER() OVER (PARTITION BY p.Portal ORDER BY p.IdEjecucion DESC) AS rn"
        " FROM dbo.DescargaPeajes_EjecucionPortales p"
        " WHERE p.Estado IN ('ok', 'error', 'sin_credenciales')"
        ") u WHERE u.rn = 1 AND u.Estado = 'error'"
    )["n"]
    return {"pendientes": pendientes, "portalesConError": con_error}
