"""Persistencia de documentos nuevos y de la rutina en `WC` (043, data-model.md).

Solo SQL parametrizado. `DocumentosNuevos` es el único lugar de los avisos de
todos los módulos: un archivo (SHA-256) genera a lo sumo un aviso por módulo.
"""

from __future__ import annotations

from datetime import datetime

import pyodbc

from src.db.connection import execute_insert_returning_id, execute_write, fetch_all, fetch_one

LIMITE_MAXIMO = 100
MODULOS = ("compras", "impuestos", "ventas", "tesoreria", "cuentas_corrientes", "sin_clasificar")
PENDIENTE = "d.Estado IN ('cargado_solo', 'para_cargar') AND d.Revisado IS NULL"


# --- Documentos nuevos -------------------------------------------------------

def existente(sha: str, modulo: str | None = None) -> dict | None:
    """Documento ya registrado con este archivo (en ese módulo, o en cualquiera)."""
    if modulo:
        return fetch_one("SELECT IdDocumentoNuevo AS id, Estado AS estado, Ruta AS ruta FROM dbo.DocumentosNuevos "
                         "WHERE Sha256 = ? AND Modulo = ?", (sha, modulo))
    return fetch_one("SELECT TOP 1 IdDocumentoNuevo AS id, Estado AS estado, Ruta AS ruta FROM dbo.DocumentosNuevos "
                     "WHERE Sha256 = ? ORDER BY IdDocumentoNuevo", (sha,))


def mismo_comprobante(id_contacto: int, numero: str, modulo: str) -> bool:
    """Ya hay aviso del mismo comprobante (emisor y número) aunque el PDF sea otro (original y duplicado)."""
    return fetch_one("SELECT TOP 1 1 AS x FROM dbo.DocumentosNuevos WHERE IdContacto = ? AND Numero = ? AND Modulo = ?",
                     (id_contacto, numero[:50], modulo)) is not None


def adjunto_procesado(entry_id: str, sha: str) -> bool:
    return fetch_one("SELECT TOP 1 1 AS x FROM dbo.DocumentosNuevos WHERE MailEntryId = ? AND Sha256 = ?",
                     (entry_id[:200], sha)) is not None


def registrar_documento(d: dict) -> tuple[int, bool]:
    """Inserta el documento si no existe ya (Sha256, Modulo). Devuelve `(id, nuevo)`."""
    previo = existente(d["sha256"], d["modulo"])
    if previo:
        return previo["id"], False
    try:
        id_ = execute_insert_returning_id(
            "INSERT INTO dbo.DocumentosNuevos (IdRutinaCorrida, Origen, IdPortal, IdDocumentoPortal, MailEntryId, "
            "MailRemitente, MailAsunto, MailRecibido, Sha256, Ruta, Tipo, Modulo, IdContacto, Fecha, Numero, Total, "
            "Estado, Motivo, IdRegistro) OUTPUT INSERTED.IdDocumentoNuevo "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (d.get("idRutinaCorrida"), d["origen"], d.get("idPortal"), d.get("idDocumentoPortal"),
             (d.get("mailEntryId") or "")[:200] or None, (d.get("mailRemitente") or "")[:200] or None,
             (d.get("mailAsunto") or "")[:200] or None, d.get("mailRecibido"), d["sha256"], d["ruta"][:400],
             d["tipo"][:30], d["modulo"], d.get("idContacto"), d.get("fecha"), (d.get("numero") or "")[:50] or None,
             d.get("total"), d["estado"], (d.get("motivo") or "")[:300] or None, d.get("idRegistro")),
        )
    except pyodbc.IntegrityError:  # otra vía lo registró al mismo tiempo
        return existente(d["sha256"], d["modulo"])["id"], False
    return id_, True


def resumen_pendientes() -> dict[str, int]:
    filas = fetch_all(f"SELECT d.Modulo AS modulo, COUNT(*) AS n FROM dbo.DocumentosNuevos d WHERE {PENDIENTE} "
                      "GROUP BY d.Modulo")
    return {f["modulo"]: f["n"] for f in filas}


_COLS = (
    "d.IdDocumentoNuevo AS idDocumentoNuevo, d.Origen AS origen, p.Nombre AS portal, d.MailRemitente AS mailRemitente, "
    "d.MailAsunto AS mailAsunto, d.MailRecibido AS mailRecibido, d.Creado AS creado, d.Tipo AS tipo, "
    "d.Modulo AS modulo, d.Estado AS estado, d.Motivo AS motivo, d.IdContacto AS idContacto, "
    "ct.[Razon Social] AS contacto, d.Fecha AS fecha, d.Numero AS numero, d.Total AS total, d.Ruta AS ruta, "
    "d.IdRegistro AS idRegistro"
)
_FROM = ("FROM dbo.DocumentosNuevos d LEFT JOIN dbo.Portales p ON p.IdPortal = d.IdPortal "
         "LEFT JOIN dbo.Contactos ct ON ct.IdContacto = d.IdContacto")


def listar_pendientes(modulo: str, limite: int = 50, desde: int = 0) -> tuple[list[dict], int]:
    limite = min(limite, LIMITE_MAXIMO)
    total = fetch_one(f"SELECT COUNT(*) AS n FROM dbo.DocumentosNuevos d WHERE d.Modulo = ? AND {PENDIENTE}",
                      (modulo,))["n"]
    filas = fetch_all(
        f"SELECT {_COLS} {_FROM} WHERE d.Modulo = ? AND {PENDIENTE} "
        "ORDER BY d.IdDocumentoNuevo OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        (modulo, desde, limite),
    )
    return filas, total


def obtener(id_documento: int) -> dict | None:
    return fetch_one(f"SELECT {_COLS} {_FROM} WHERE d.IdDocumentoNuevo = ?", (id_documento,))


def renglones_compras(ids: list[int]) -> list[dict]:
    if not ids:
        return []
    return fetch_all(
        "SELECT dc.IdCompra AS idCompra, dc.[Producto/Servicio] AS detalle, dc.Cantidad AS cantidad, "
        "dc.[Precio Unitario] AS precioUnitario, dc.IVA AS iva, r.Rubro AS rubro, cc.[Centro de costos] AS centroCosto "
        "FROM dbo.Det_Compras dc LEFT JOIN dbo.Rubros r ON r.IdRubro = dc.IdRubro "
        "LEFT JOIN dbo.[Centro de costos] cc ON cc.IdCentro = dc.IdCentroCostos "
        f"WHERE dc.IdCompra IN ({', '.join('?' for _ in ids)}) ORDER BY dc.IdDetalleCompra", tuple(ids))


def marcar_revisado(id_documento: int, usuario: str | None) -> int:
    return execute_write(
        "UPDATE d SET Revisado = SYSDATETIME(), RevisadoPor = ? FROM dbo.DocumentosNuevos d "
        f"WHERE d.IdDocumentoNuevo = ? AND {PENDIENTE}", ((usuario or "")[:60] or None, id_documento))


def cambiar_modulo(id_documento: int, modulo: str, usuario: str | None) -> int:
    """Mueve el aviso a otro módulo dejando constancia del anterior, quién y cuándo. No mueve si ese archivo
    ya tiene aviso en el módulo destino."""
    return execute_write(
        "UPDATE d SET ModuloAnterior = d.Modulo, Modulo = ?, ModuloCambiado = SYSDATETIME(), ModuloCambiadoPor = ? "
        f"FROM dbo.DocumentosNuevos d WHERE d.IdDocumentoNuevo = ? AND d.Modulo <> ? AND {PENDIENTE} "
        "AND NOT EXISTS (SELECT 1 FROM dbo.DocumentosNuevos o WHERE o.Sha256 = d.Sha256 AND o.Modulo = ?)",
        (modulo, (usuario or "")[:60] or None, id_documento, modulo, modulo))


def vincular_registro(id_documento: int, id_registro: int) -> int:
    """Un `para_cargar` cargado después a mano recibe su registro y sigue esperando la revisión."""
    return execute_write("UPDATE dbo.DocumentosNuevos SET IdRegistro = ? WHERE IdDocumentoNuevo = ?",
                         (id_registro, id_documento))


# --- Rutina ------------------------------------------------------------------

def abrir_corrida(origen: str = "programada") -> int | None:
    """Nueva corrida `en_curso`, o `None` si ya hay otra (índice único filtrado)."""
    try:
        return execute_insert_returning_id(
            "INSERT INTO dbo.Rutina_Corridas (Origen, Estado) OUTPUT INSERTED.IdRutinaCorrida VALUES (?, 'en_curso')",
            (origen,))
    except pyodbc.IntegrityError:
        return None


def cerrar_corrida(id_corrida: int, estado: str, r: dict, mensaje: str | None) -> None:
    execute_write(
        "UPDATE dbo.Rutina_Corridas SET Fin = SYSDATETIME(), Estado = ?, CuentasCorridas = ?, CuentasConProblemas = ?, "
        "MailsLeidos = ?, DocumentosNuevos = ?, CargadosSolos = ?, ParaCargarAMano = ?, Mensaje = ? "
        "WHERE IdRutinaCorrida = ?",
        (estado, r.get("cuentasCorridas", 0), r.get("cuentasConProblemas", 0), r.get("mailsLeidos", 0),
         r.get("documentosNuevos", 0), r.get("cargadosSolos", 0), r.get("paraCargarAMano", 0),
         (mensaje or "")[:400] or None, id_corrida))


def marcar_incompletas() -> int:
    """Al arrancar el backend, una corrida que quedó `en_curso` se cortó: pasa a `incompleta`."""
    return execute_write("UPDATE dbo.Rutina_Corridas SET Estado = 'incompleta', Fin = SYSDATETIME(), "
                         "Mensaje = N'Se cortó: el sistema se cerró durante la corrida' WHERE Estado = 'en_curso'")


def ultima_corrida() -> dict | None:
    return fetch_one(
        "SELECT TOP 1 Inicio AS inicio, Fin AS fin, Estado AS estado, CuentasCorridas AS cuentasCorridas, "
        "CuentasConProblemas AS cuentasConProblemas, MailsLeidos AS mailsLeidos, DocumentosNuevos AS documentosNuevos, "
        "CargadosSolos AS cargadosSolos, ParaCargarAMano AS paraCargarAMano, Mensaje AS mensaje "
        "FROM dbo.Rutina_Corridas ORDER BY IdRutinaCorrida DESC")


def programacion() -> dict | None:
    fila = fetch_one("SELECT Horarios AS horarios, ProximaCorrida AS proxima, Activa AS activa "
                     "FROM dbo.Rutina_Programacion WHERE Id = 1")
    return {**fila, "proxima": _fecha_hora(fila["proxima"])} if fila else None


def fijar_proxima(proxima: datetime | None) -> None:
    execute_write("UPDATE dbo.Rutina_Programacion SET ProximaCorrida = ? WHERE Id = 1", (proxima,))


def marca_mails(almacen: str) -> datetime | None:
    fila = fetch_one("SELECT UltimoRecibido AS u FROM dbo.Rutina_MarcaMails WHERE Almacen = ?", (almacen[:200],))
    return _fecha_hora(fila["u"]) if fila else None


def _fecha_hora(valor) -> datetime | None:
    """`datetime2` llega del driver ODBC como texto ("2026-10-27 07:00:00.0000000")."""
    if valor is None or isinstance(valor, datetime):
        return valor
    return datetime.fromisoformat(str(valor).replace(" ", "T", 1).split(".")[0])


def fijar_marca_mails(almacen: str, ultimo: datetime) -> None:
    if not execute_write("UPDATE dbo.Rutina_MarcaMails SET UltimoRecibido = ? WHERE Almacen = ?", (ultimo, almacen[:200])):
        execute_write("INSERT INTO dbo.Rutina_MarcaMails (Almacen, UltimoRecibido) VALUES (?, ?)", (almacen[:200], ultimo))


def portales_sincronizables() -> list[dict]:
    """Cuentas que la rutina corre: activas, con conector, autorización vigente y contraseña cargada."""
    return fetch_all(
        "SELECT p.IdPortal AS idPortal, p.Nombre AS nombre FROM dbo.Portales p "
        "JOIN dbo.Boveda_Credenciales c ON c.IdCredencial = p.IdCredencial "
        "WHERE p.Activo = 1 AND p.CodigoConector IS NOT NULL AND c.ClaveCifrada IS NOT NULL AND c.Rechazada = 0 "
        "AND EXISTS (SELECT 1 FROM dbo.Portales_Autorizaciones a WHERE a.IdPortal = p.IdPortal AND a.Revocada IS NULL) "
        "ORDER BY p.IdPortal")
