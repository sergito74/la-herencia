"""Persistencia de la bóveda en `WC` (042, data-model.md).

Solo SQL parametrizado. Los secretos entran y salen cifrados: este módulo
nunca ve una contraseña en claro salvo en `crear_credencial`/`cambiar_clave`,
que la cifran antes de escribir, y `leer_*_cifrado`, que devuelven el blob.
"""

from __future__ import annotations

from src.db.connection import (
    execute_insert_returning_id, execute_write, execute_write_transaction, fetch_all, fetch_one,
)
from src.features.boveda import cifrado

LIMITE_MAXIMO = 100


# --- Auditoría ---------------------------------------------------------------

def auditar(accion: str, usuario: str | None, *, id_portal: int | None = None, id_credencial: int | None = None,
            detalle: str | None = None) -> None:
    execute_write(
        "INSERT INTO dbo.Boveda_Auditoria (Usuario, Accion, IdPortal, IdCredencial, Detalle) VALUES (?, ?, ?, ?, ?)",
        (usuario, accion, id_portal, id_credencial, (detalle or "")[:400] or None),
    )


# --- Credenciales ------------------------------------------------------------

def hay_secretos() -> bool:
    return fetch_one(
        "SELECT TOP 1 1 AS x FROM dbo.Boveda_Credenciales WHERE ClaveCifrada IS NOT NULL "
        "UNION ALL SELECT TOP 1 1 FROM dbo.Boveda_CredencialDatos WHERE ValorCifrado IS NOT NULL") is not None


def clave_para_escribir() -> bytes:
    """La clave maestra existente; se crea solo si la bóveda todavía no guardó ningún secreto
    (si hay secretos y falta la clave, crear otra los dejaría ilegibles)."""
    try:
        return cifrado.clave_maestra(crear=False)
    except cifrado.ClaveMaestraNoDisponible:
        if hay_secretos():
            raise cifrado.ClaveMaestraNoDisponible(
                "Falta la clave maestra de la bóveda en este equipo/usuario de Windows: restaurarla con "
                "scripts/boveda_clave.py importar. No se creó otra para no dejar ilegibles las contraseñas guardadas.")
        return cifrado.clave_maestra(crear=True)


def listar_credenciales() -> list[dict]:
    filas = fetch_all(
        "SELECT c.IdCredencial AS idCredencial, c.Nombre AS nombre, c.Titular AS titular, c.IdSocio AS idSocio, "
        "c.Usuario AS usuario, CAST(CASE WHEN c.ClaveCifrada IS NULL THEN 0 ELSE 1 END AS bit) AS claveConfigurada, "
        "c.ClaveActualizada AS claveActualizada, c.Rechazada AS rechazada "
        "FROM dbo.Boveda_Credenciales c WHERE c.Activo = 1 ORDER BY c.Nombre"
    )
    datos = fetch_all(
        "SELECT IdCredencial AS idCredencial, Nombre AS nombre, Secreto AS secreto, "
        "CASE WHEN Secreto = 1 THEN NULL ELSE ValorTexto END AS valor "
        "FROM dbo.Boveda_CredencialDatos ORDER BY Nombre"
    )
    portales = fetch_all("SELECT IdCredencial AS idCredencial, IdPortal AS idPortal FROM dbo.Portales WHERE IdCredencial IS NOT NULL")
    for c in filas:
        c["datos"] = [{k: d[k] for k in ("nombre", "secreto", "valor")} for d in datos if d["idCredencial"] == c["idCredencial"]]
        c["portales"] = [p["idPortal"] for p in portales if p["idCredencial"] == c["idCredencial"]]
    return filas


def obtener_credencial(id_credencial: int) -> dict | None:
    return fetch_one(
        "SELECT IdCredencial AS idCredencial, Nombre AS nombre, Usuario AS usuario, Rechazada AS rechazada "
        "FROM dbo.Boveda_Credenciales WHERE IdCredencial = ? AND Activo = 1",
        (id_credencial,),
    )


def _stmts_datos(datos: list[dict], obtener_id, clave_maestra: bytes) -> list:
    stmts = []
    for d in datos:
        def stmt(res, d=d):
            idc = obtener_id(res)
            if d["secreto"]:
                blob = cifrado.cifrar(d["valor"], cifrado.aad_dato(idc, d["nombre"]), clave_maestra)
                return (
                    "INSERT INTO dbo.Boveda_CredencialDatos (IdCredencial, Nombre, Secreto, ValorCifrado) VALUES (?, ?, 1, ?)",
                    (idc, d["nombre"], blob),
                )
            return (
                "INSERT INTO dbo.Boveda_CredencialDatos (IdCredencial, Nombre, Secreto, ValorTexto) VALUES (?, ?, 0, ?)",
                (idc, d["nombre"], d["valor"]),
            )
        stmts.append(stmt)
    return stmts


def crear_credencial(nombre: str, titular: str, id_socio: int | None, usuario: str | None, clave: str | None,
                     datos: list[dict]) -> int:
    clave_maestra = clave_para_escribir() if clave or any(d["secreto"] for d in datos) else None
    stmts: list = [(
        "INSERT INTO dbo.Boveda_Credenciales (Nombre, Titular, IdSocio, Usuario) OUTPUT INSERTED.IdCredencial VALUES (?, ?, ?, ?)",
        (nombre, titular, id_socio, usuario),
    )]
    if clave:
        stmts.append(lambda res: (
            "UPDATE dbo.Boveda_Credenciales SET ClaveCifrada = ?, ClaveActualizada = SYSDATETIME() WHERE IdCredencial = ?",
            (cifrado.cifrar(clave, cifrado.aad_clave(res[0]), clave_maestra), res[0]),
        ))
    stmts += _stmts_datos(datos, lambda res: res[0], clave_maestra)
    return execute_write_transaction(stmts)[0]


def editar_credencial(id_credencial: int, nombre: str | None, usuario: str | None, datos: list[dict] | None) -> None:
    nuevos_secretos = datos is not None and any(d["secreto"] and d.get("valor") for d in datos)
    clave_maestra = clave_para_escribir() if nuevos_secretos else None
    stmts: list = [(
        "UPDATE dbo.Boveda_Credenciales SET Nombre = COALESCE(?, Nombre), Usuario = COALESCE(?, Usuario) WHERE IdCredencial = ?",
        (nombre, usuario, id_credencial),
    )]
    if datos is not None:
        # Un dato secreto sin valor nuevo conserva el cifrado anterior.
        # Solo se conserva lo que ya estaba guardado como secreto: un dato que pasa a secreto exige valor nuevo
        # (si no, quedaría en texto plano marcado como secreto).
        ya_secretos = {d["nombre"] for d in leer_datos(id_credencial) if d["secreto"]}
        for d in datos:
            if d["secreto"] and not d.get("valor") and d["nombre"] not in ya_secretos:
                raise ValueError(f"Para guardar {d['nombre']} como secreto hay que escribir su valor")
        conservar = [d["nombre"] for d in datos if d["secreto"] and not d.get("valor")]
        nuevos = [d for d in datos if d.get("valor")]
        if conservar:
            marcas = ", ".join("?" for _ in conservar)
            stmts.append((f"DELETE FROM dbo.Boveda_CredencialDatos WHERE IdCredencial = ? AND Nombre NOT IN ({marcas})",
                          (id_credencial, *conservar)))
        else:
            stmts.append(("DELETE FROM dbo.Boveda_CredencialDatos WHERE IdCredencial = ?", (id_credencial,)))
        stmts += _stmts_datos(nuevos, lambda res: id_credencial, clave_maestra)
    execute_write_transaction(stmts)


def borrar_credencial(id_credencial: int) -> None:
    """Deshace un alta que no llegó a usarse (alta de portal fallida)."""
    execute_write_transaction([
        ("DELETE FROM dbo.Boveda_CredencialDatos WHERE IdCredencial = ?", (id_credencial,)),
        ("DELETE FROM dbo.Boveda_Credenciales WHERE IdCredencial = ? "
         "AND NOT EXISTS (SELECT 1 FROM dbo.Portales p WHERE p.IdCredencial = ?)", (id_credencial, id_credencial)),
    ])


def cambiar_clave(id_credencial: int, clave: str) -> int:
    blob = cifrado.cifrar(clave, cifrado.aad_clave(id_credencial), clave_para_escribir())
    return execute_write(
        "UPDATE dbo.Boveda_Credenciales SET ClaveCifrada = ?, ClaveActualizada = SYSDATETIME(), Rechazada = 0 "
        "WHERE IdCredencial = ? AND Activo = 1",
        (blob, id_credencial),
    )


def marcar_rechazada(id_credencial: int) -> None:
    execute_write("UPDATE dbo.Boveda_Credenciales SET Rechazada = 1 WHERE IdCredencial = ?", (id_credencial,))


def leer_clave_cifrada(id_credencial: int) -> bytes | None:
    fila = fetch_one("SELECT ClaveCifrada AS blob FROM dbo.Boveda_Credenciales WHERE IdCredencial = ? AND Activo = 1",
                     (id_credencial,))
    return fila["blob"] if fila else None


def leer_datos(id_credencial: int) -> list[dict]:
    return fetch_all(
        "SELECT Nombre AS nombre, Secreto AS secreto, ValorTexto AS valorTexto, ValorCifrado AS valorCifrado "
        "FROM dbo.Boveda_CredencialDatos WHERE IdCredencial = ?",
        (id_credencial,),
    )


# --- Portales ----------------------------------------------------------------

_SQL_PORTALES = """
SELECT p.IdPortal AS idPortal, p.Nombre AS nombre, p.Url AS url, p.Tipo AS tipo, p.IdContacto AS idContacto,
       ct.[Razon Social] AS contacto, p.IdCredencial AS idCredencial, cr.Nombre AS credencialNombre,
       cr.Usuario AS credencialUsuario,
       CAST(CASE WHEN cr.ClaveCifrada IS NULL THEN 0 ELSE 1 END AS bit) AS claveConfigurada,
       cr.Rechazada AS credencialRechazada, p.CodigoConector AS codigoConector, p.Notas AS notas,
       a.Fecha AS autFecha, a.AutorizadoPor AS autPor, a.Fuente AS autFuente,
       pr.Frecuencia AS frecuencia, pr.DiaSemana AS diaSemana, pr.DiaMes AS diaMes,
       CONVERT(varchar(5), pr.Hora, 108) AS hora, pr.ProximaCorrida AS proximaCorrida,
       pr.Suspendida AS suspendida, pr.MotivoSuspension AS motivoSuspension,
       uc.IdCorrida AS ucId, uc.Inicio AS ucInicio, uc.Fin AS ucFin, uc.Estado AS ucEstado, uc.Nuevos AS ucNuevos,
       uc.Existentes AS ucExistentes, uc.Cargados AS ucCargados, uc.Pendientes AS ucPendientes, uc.Mensaje AS ucMensaje,
       uc.Paso AS ucPaso, uc.AvanceHecho AS ucHecho, uc.AvanceTotal AS ucTotal,
       uf.FechaCorte AS ufFechaCorte, uf.Moneda AS ufMoneda, uf.SaldoPortal AS ufSaldoPortal,
       uf.SaldoSistema AS ufSaldoSistema, uf.Diferencia AS ufDiferencia
FROM dbo.Portales p
LEFT JOIN dbo.Contactos ct ON ct.IdContacto = p.IdContacto
LEFT JOIN dbo.Boveda_Credenciales cr ON cr.IdCredencial = p.IdCredencial
OUTER APPLY (SELECT TOP 1 * FROM dbo.Portales_Autorizaciones x
             WHERE x.IdPortal = p.IdPortal AND x.Revocada IS NULL ORDER BY x.IdAutorizacion DESC) a
LEFT JOIN dbo.Portales_Programacion pr ON pr.IdPortal = p.IdPortal
OUTER APPLY (SELECT TOP 1 * FROM dbo.Portales_Corridas x WHERE x.IdPortal = p.IdPortal ORDER BY x.IdCorrida DESC) uc
OUTER APPLY (SELECT TOP 1 * FROM dbo.Portales_EstadoCuenta x WHERE x.IdPortal = p.IdPortal ORDER BY x.IdFoto DESC) uf
WHERE p.Activo = 1
"""


def listar_portales() -> list[dict]:
    return fetch_all(_SQL_PORTALES + " ORDER BY p.Nombre")


def obtener_portal(id_portal: int) -> dict | None:
    return fetch_one(_SQL_PORTALES + " AND p.IdPortal = ?", (id_portal,))


def existe_nombre_portal(nombre: str, excepto: int | None = None) -> bool:
    return fetch_one("SELECT 1 AS x FROM dbo.Portales WHERE Nombre = ? AND IdPortal <> ?", (nombre, excepto or 0)) is not None


def crear_portal(nombre: str, url: str, tipo: str, id_contacto: int | None, id_credencial: int | None,
                 codigo_conector: str | None, notas: str | None) -> int:
    return execute_insert_returning_id(
        "INSERT INTO dbo.Portales (Nombre, Url, Tipo, IdContacto, IdCredencial, CodigoConector, Notas) "
        "OUTPUT INSERTED.IdPortal VALUES (?, ?, ?, ?, ?, ?, ?)",
        (nombre, url, tipo, id_contacto, id_credencial, codigo_conector, notas),
    )


_CAMPOS_PORTAL = {"nombre": "Nombre", "url": "Url", "tipo": "Tipo", "idContacto": "IdContacto",
                  "idCredencial": "IdCredencial", "codigoConector": "CodigoConector", "notas": "Notas"}


def editar_portal(id_portal: int, cambios: dict) -> int:
    campos = [(col, cambios[k]) for k, col in _CAMPOS_PORTAL.items() if k in cambios]
    if not campos:
        return 0
    asignaciones = ", ".join(f"{col} = ?" for col, _ in campos)
    return execute_write(f"UPDATE dbo.Portales SET {asignaciones} WHERE IdPortal = ?",
                         tuple(v for _, v in campos) + (id_portal,))


def existe_contacto(id_contacto: int) -> bool:
    return fetch_one("SELECT 1 AS x FROM dbo.Contactos WHERE IdContacto = ?", (id_contacto,)) is not None


# --- Autorizaciones ----------------------------------------------------------

def autorizacion_vigente(id_portal: int) -> dict | None:
    return fetch_one(
        "SELECT TOP 1 IdAutorizacion AS idAutorizacion, Fecha AS fecha, AutorizadoPor AS autorizadoPor, Fuente AS fuente "
        "FROM dbo.Portales_Autorizaciones WHERE IdPortal = ? AND Revocada IS NULL ORDER BY IdAutorizacion DESC",
        (id_portal,),
    )


def autorizar(id_portal: int, fecha, autorizado_por: str, fuente: str | None, usuario: str | None) -> int:
    """Reemplaza la autorización vigente en una sola transacción (nunca queda el portal sin autorización a medias)."""
    return execute_write_transaction([
        ("INSERT INTO dbo.Portales_Autorizaciones (IdPortal, Alcance, AutorizadoPor, Fecha, Fuente) "
         "OUTPUT INSERTED.IdAutorizacion VALUES (?, 'solo_lectura_descarga', ?, ?, ?)",
         (id_portal, autorizado_por, fecha, fuente)),
        lambda res: ("UPDATE dbo.Portales_Autorizaciones SET Revocada = SYSDATETIME(), RevocadaPor = ? "
                     "WHERE IdPortal = ? AND Revocada IS NULL AND IdAutorizacion <> ?",
                     (usuario or "desconocido", id_portal, res[0])),
    ])[0]


def revocar(id_portal: int, usuario: str | None) -> int:
    return execute_write(
        "UPDATE dbo.Portales_Autorizaciones SET Revocada = SYSDATETIME(), RevocadaPor = ? "
        "WHERE IdPortal = ? AND Revocada IS NULL",
        (usuario or "desconocido", id_portal),
    )


# --- Programación ------------------------------------------------------------

def obtener_programacion(id_portal: int) -> dict | None:
    return fetch_one(
        "SELECT IdPortal AS idPortal, Frecuencia AS frecuencia, DiaSemana AS diaSemana, DiaMes AS diaMes, Hora AS hora, "
        "ProximaCorrida AS proximaCorrida, Suspendida AS suspendida, MotivoSuspension AS motivoSuspension "
        "FROM dbo.Portales_Programacion WHERE IdPortal = ?",
        (id_portal,),
    )


def guardar_programacion(id_portal: int, frecuencia: str, dia_semana: int | None, dia_mes: int | None, hora,
                         proxima) -> None:
    execute_write_transaction([
        ("DELETE FROM dbo.Portales_Programacion WHERE IdPortal = ?", (id_portal,)),
        ("INSERT INTO dbo.Portales_Programacion (IdPortal, Frecuencia, DiaSemana, DiaMes, Hora, ProximaCorrida, Suspendida) "
         "VALUES (?, ?, ?, ?, ?, ?, 0)", (id_portal, frecuencia, dia_semana, dia_mes, hora, proxima)),
    ])


def fijar_proxima(id_portal: int, proxima) -> None:
    execute_write("UPDATE dbo.Portales_Programacion SET ProximaCorrida = ? WHERE IdPortal = ?", (proxima, id_portal))


def suspender(id_portal: int, motivo: str) -> None:
    execute_write("UPDATE dbo.Portales_Programacion SET Suspendida = 1, MotivoSuspension = ? WHERE IdPortal = ?",
                  (motivo[:200], id_portal))


def levantar_suspension_credencial(id_credencial: int) -> list[int]:
    """Al cambiar la clave se levantan las suspensiones de los portales que la usan."""
    ids = [f["id"] for f in fetch_all(
        "SELECT p.IdPortal AS id FROM dbo.Portales p JOIN dbo.Portales_Programacion pr ON pr.IdPortal = p.IdPortal "
        "WHERE p.IdCredencial = ? AND pr.Suspendida = 1", (id_credencial,))]
    if ids:
        execute_write(
            "UPDATE pr SET Suspendida = 0, MotivoSuspension = NULL FROM dbo.Portales_Programacion pr "
            "JOIN dbo.Portales p ON p.IdPortal = pr.IdPortal WHERE p.IdCredencial = ?", (id_credencial,))
    return ids


def portales_vencidos(ahora) -> list[dict]:
    """Portales a correr: activos, con conector, autorizados, programados, no suspendidos y vencidos."""
    return fetch_all(
        "SELECT p.IdPortal AS idPortal, p.CodigoConector AS codigoConector FROM dbo.Portales p "
        "JOIN dbo.Portales_Programacion pr ON pr.IdPortal = p.IdPortal "
        "WHERE p.Activo = 1 AND p.CodigoConector IS NOT NULL AND pr.Frecuencia <> 'desactivada' "
        "AND pr.Suspendida = 0 AND pr.ProximaCorrida IS NOT NULL AND pr.ProximaCorrida <= ? "
        "AND EXISTS (SELECT 1 FROM dbo.Portales_Autorizaciones a WHERE a.IdPortal = p.IdPortal AND a.Revocada IS NULL) "
        "ORDER BY pr.ProximaCorrida, p.IdPortal",
        (ahora,),
    )


def portal_para_correr(id_portal: int) -> dict | None:
    return fetch_one(
        "SELECT p.IdPortal AS idPortal, p.Nombre AS nombre, p.IdContacto AS idContacto, p.IdCredencial AS idCredencial, "
        "p.CodigoConector AS codigoConector FROM dbo.Portales p WHERE p.IdPortal = ? AND p.Activo = 1",
        (id_portal,),
    )


# --- Corridas ----------------------------------------------------------------

_COLS_CORRIDA = (
    "c.IdCorrida AS idCorrida, c.IdPortal AS idPortal, p.Nombre AS portal, c.Origen AS origen, c.Usuario AS usuario, "
    "c.Inicio AS inicio, c.Fin AS fin, c.Estado AS estado, c.Nuevos AS nuevos, c.Existentes AS existentes, "
    "c.Cargados AS cargados, c.Pendientes AS pendientes, c.Mensaje AS mensaje, c.Paso AS paso, "
    "c.AvanceHecho AS avanceHecho, c.AvanceTotal AS avanceTotal"
)


def crear_corrida(id_portal: int, origen: str, usuario: str | None, estado: str = "en_curso",
                  mensaje: str | None = None) -> int:
    return execute_insert_returning_id(
        "INSERT INTO dbo.Portales_Corridas (IdPortal, Origen, Usuario, Estado, Mensaje, Fin) OUTPUT INSERTED.IdCorrida "
        "VALUES (?, ?, ?, ?, ?, CASE WHEN ? = 'en_curso' THEN NULL ELSE SYSDATETIME() END)",
        (id_portal, origen, usuario, estado, (mensaje or "")[:400] or None, estado),
    )


def cerrar_corrida(id_corrida: int, estado: str, *, nuevos: int = 0, existentes: int = 0, cargados: int = 0,
                   pendientes: int = 0, mensaje: str | None = None) -> None:
    execute_write(
        "UPDATE dbo.Portales_Corridas SET Estado = ?, Nuevos = ?, Existentes = ?, Cargados = ?, Pendientes = ?, "
        "Mensaje = ?, Fin = SYSDATETIME(), Paso = NULL WHERE IdCorrida = ?",
        (estado, nuevos, existentes, cargados, pendientes, (mensaje or "")[:400] or None, id_corrida),
    )


def avance(id_corrida: int, paso: str, hecho: int | None = None, total: int | None = None, **conteos) -> None:
    """Paso visible de la corrida en curso ("Descargando 3 de 12…") y conteos parciales."""
    execute_write(
        "UPDATE dbo.Portales_Corridas SET Paso = ?, AvanceHecho = ?, AvanceTotal = ?, "
        "Nuevos = COALESCE(?, Nuevos), Existentes = COALESCE(?, Existentes), Cargados = COALESCE(?, Cargados), "
        "Pendientes = COALESCE(?, Pendientes) WHERE IdCorrida = ? AND Estado = 'en_curso'",
        (paso[:160], hecho, total, conteos.get("nuevos"), conteos.get("existentes"), conteos.get("cargados"),
         conteos.get("pendientes"), id_corrida),
    )


def marcar_incompletas(id_portal: int) -> int:
    """Corridas del portal que quedaron `en_curso` sin proceso vivo (quien llama tiene el lock del portal)."""
    return execute_write(
        "UPDATE dbo.Portales_Corridas SET Estado = 'incompleta', Fin = SYSDATETIME(), "
        "Mensaje = COALESCE(Mensaje, N'Se interrumpió antes de terminar') WHERE IdPortal = ? AND Estado = 'en_curso'",
        (id_portal,),
    )


def corrida_en_curso(id_portal: int) -> dict | None:
    return fetch_one(
        f"SELECT TOP 1 {_COLS_CORRIDA} FROM dbo.Portales_Corridas c JOIN dbo.Portales p ON p.IdPortal = c.IdPortal "
        "WHERE c.IdPortal = ? AND c.Estado = 'en_curso' ORDER BY c.IdCorrida DESC",
        (id_portal,),
    )


def listar_corridas(id_portal: int | None, limite: int = 20, desde: int = 0,
                    portales: list[int] | None = None) -> tuple[list[dict], int]:
    limite = min(limite, LIMITE_MAXIMO)
    condiciones, params = [], []
    if id_portal:
        condiciones.append("c.IdPortal = ?")
        params.append(id_portal)
    if portales:
        condiciones.append(f"c.IdPortal IN ({', '.join('?' for _ in portales)})")
        params += portales
    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    total = fetch_one(f"SELECT COUNT(*) AS n FROM dbo.Portales_Corridas c {where}", tuple(params))["n"]
    filas = fetch_all(
        f"SELECT {_COLS_CORRIDA} FROM dbo.Portales_Corridas c JOIN dbo.Portales p ON p.IdPortal = c.IdPortal {where} "
        "ORDER BY c.IdCorrida DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        tuple(params) + (desde, limite),
    )
    return filas, total


def obtener_corrida(id_corrida: int) -> dict | None:
    return fetch_one(
        f"SELECT {_COLS_CORRIDA} FROM dbo.Portales_Corridas c JOIN dbo.Portales p ON p.IdPortal = c.IdPortal "
        "WHERE c.IdCorrida = ?",
        (id_corrida,),
    )


# --- Documentos --------------------------------------------------------------

_COLS_DOC = (
    "d.IdDocumento AS idDocumento, d.IdPortal AS idPortal, p.Nombre AS portal, d.Tipo AS tipo, d.Proveedor AS proveedor, "
    "d.IdContacto AS idContacto, d.FechaDocumento AS fechaDocumento, d.NumeroDocumento AS numeroDocumento, "
    "d.TotalImpreso AS totalImpreso, d.Moneda AS moneda, d.Ruta AS ruta, d.EstadoCarga AS estadoCarga, "
    "d.Motivo AS motivo, d.IdCompra AS idCompra, d.IdCorrida AS idCorrida"
)


def existe_documento(id_portal: int, clave: str) -> bool:
    return fetch_one("SELECT 1 AS x FROM dbo.Portales_Documentos WHERE IdPortal = ? AND Clave = ?",
                     (id_portal, clave)) is not None


def existe_equivalente(patrones: list[str]) -> bool:
    """Mismo comprobante ofrecido por otro portal (ej. AUBASA en TelePASE): patrones LIKE sobre `Clave`."""
    return any(fetch_one("SELECT TOP 1 1 AS x FROM dbo.Portales_Documentos WHERE Clave LIKE ?", (p,)) for p in patrones)


def existe_sha(sha: str) -> str | None:
    fila = fetch_one("SELECT TOP 1 Ruta AS ruta FROM dbo.Portales_Documentos WHERE Sha256 = ?", (sha,))
    return fila["ruta"] if fila else None


def insertar_documento(d: dict) -> int:
    return execute_insert_returning_id(
        "INSERT INTO dbo.Portales_Documentos (IdPortal, Clave, Tipo, Proveedor, IdContacto, FechaDocumento, "
        "NumeroDocumento, TotalImpreso, Moneda, Ruta, Sha256, IdCorrida, EstadoCarga, Motivo, IdCompra) "
        "OUTPUT INSERTED.IdDocumento VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (d["idPortal"], d["clave"], d["tipo"], d["proveedor"][:60], d.get("idContacto"), d.get("fecha"),
         d.get("numeroDocumento"), d.get("totalImpreso"), d.get("moneda"), d.get("ruta"), d.get("sha256"),
         d.get("idCorrida"), d["estadoCarga"], (d.get("motivo") or "")[:300] or None, d.get("idCompra")),
    )


def listar_documentos(id_portal: int | None, estado: str | None, limite: int = 50, desde: int = 0,
                      portales: list[int] | None = None) -> tuple[list[dict], int]:
    limite = min(limite, LIMITE_MAXIMO)
    condiciones, params = [], []
    if id_portal:
        condiciones.append("d.IdPortal = ?")
        params.append(id_portal)
    if portales:
        condiciones.append(f"d.IdPortal IN ({', '.join('?' for _ in portales)})")
        params += portales
    if estado:
        condiciones.append("d.EstadoCarga = ?")
        params.append(estado)
    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    total = fetch_one(f"SELECT COUNT(*) AS n FROM dbo.Portales_Documentos d {where}", tuple(params))["n"]
    filas = fetch_all(
        f"SELECT {_COLS_DOC} FROM dbo.Portales_Documentos d JOIN dbo.Portales p ON p.IdPortal = d.IdPortal {where} "
        "ORDER BY COALESCE(d.FechaDocumento, CAST(d.Creado AS date)) DESC, d.IdDocumento DESC "
        "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        tuple(params) + (desde, limite),
    )
    return filas, total


def documentos_de_corrida(id_corrida: int) -> list[dict]:
    return fetch_all(
        f"SELECT {_COLS_DOC} FROM dbo.Portales_Documentos d JOIN dbo.Portales p ON p.IdPortal = d.IdPortal "
        "WHERE d.IdCorrida = ? ORDER BY d.IdDocumento",
        (id_corrida,),
    )


def compra_existente(id_contacto: int | None, numero: str | None, ruta: str | None) -> int | None:
    from src.features.descarga_peajes.repository import compra_existente as de_037

    encontrada = de_037(id_contacto, numero, ruta)
    if encontrada or not (id_contacto and numero):
        return encontrada
    # Números cargados a mano con espacios ("0020- 00136689").
    fila = fetch_one("SELECT TOP 1 IdDeuda AS id FROM dbo.Compras WHERE IdContacto = ? "
                     "AND REPLACE([Nro Documento], ' ', '') = ?", (id_contacto, numero.replace(" ", "")))
    return fila["id"] if fila else None


def venta_hacienda_existente(numero: str | None, fecha=None) -> dict | None:
    """Liquidación de hacienda ya cargada a mano en Ventas (043): mismo número de comprobante, normalizado a
    `PPPP-NNNNNNNN` ("11-82156" = "0011-00082156"). Devuelve `{idVenta, ruta}`."""
    import re

    m = re.fullmatch(r"\s*(\d{1,5})\s*-\s*(\d{1,8})\s*", numero or "")
    if not m:
        return None
    normal = f"{int(m.group(1)):04d}-{int(m.group(2)):08d}"
    # Mismo número y, si se conoce, fecha cercana: el número solo podría repetirse entre consignatarios.
    rango = "AND ABS(DATEDIFF(day, Fecha, ?)) <= 30 " if fecha else ""
    fila = fetch_one("SELECT TOP 1 IdVenta AS idVenta, [Documento Original] AS d FROM dbo.[Venta Hacienda] "
                     f"WHERE REPLACE([Nro documento], ' ', '') = ? {rango}ORDER BY IdVenta",
                     (normal, fecha) if fecha else (normal,))
    if not fila:
        return None
    ruta = (fila["d"] or "").split("#")[0].strip('"') or None
    if ruta and ruta.startswith(".."):  # rutas heredadas de Access, relativas a Documents
        from pathlib import Path

        ruta = str(Path.home() / re.sub(r"^(\.\.[\\/])+", "", ruta))
    return {"idVenta": fila["idVenta"], "ruta": ruta}


def documento_original(id_compra: int) -> str | None:
    fila = fetch_one("SELECT [Documento Original] AS r FROM dbo.Compras WHERE IdDeuda = ?", (id_compra,))
    return (fila["r"] or "").split("#")[0] or None if fila else None


def revalidar_pendientes() -> int:
    """Un pendiente que ya tiene compra (cargada a mano) pasa a `ya_cargado` (regla 037 R8)."""
    cambiados = 0
    for d in fetch_all("SELECT IdDocumento AS id, IdContacto AS c, NumeroDocumento AS n, Ruta AS r "
                       "FROM dbo.Portales_Documentos WHERE EstadoCarga = 'pendiente'"):
        id_compra = compra_existente(d["c"], d["n"], d["r"])
        if id_compra:
            execute_write("UPDATE dbo.Portales_Documentos SET EstadoCarga = 'ya_cargado', IdCompra = ? "
                          "WHERE IdDocumento = ? AND EstadoCarga = 'pendiente'", (id_compra, d["id"]))
            cambiados += 1
    return cambiados


# --- Estado de cuenta --------------------------------------------------------

def insertar_foto(f: dict, movimientos: list[dict]) -> int:
    stmts: list = [(
        "INSERT INTO dbo.Portales_EstadoCuenta (IdPortal, IdCorrida, IdContacto, FechaCorte, Moneda, SaldoPortal, "
        "SaldoSistema, Diferencia, Completa) OUTPUT INSERTED.IdFoto VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (f["idPortal"], f.get("idCorrida"), f.get("idContacto"), f["fechaCorte"], f["moneda"], f["saldoPortal"],
         f.get("saldoSistema"), f.get("diferencia"), f["completa"]),
    )]
    for m in movimientos:
        stmts.append(lambda res, m=m: (
            "INSERT INTO dbo.Portales_EstadoCuentaMovimientos (IdFoto, Fecha, Comprobante, Detalle, Debe, Haber, Saldo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (res[0], m.get("fecha"), (m.get("comprobante") or "")[:60] or None, (m.get("detalle") or "")[:200] or None,
             m.get("debe"), m.get("haber"), m.get("saldo")),
        ))
    return execute_write_transaction(stmts)[0]


_COLS_FOTO = (
    "f.IdFoto AS idFoto, f.IdPortal AS idPortal, p.Nombre AS portal, f.IdCorrida AS idCorrida, f.IdContacto AS idContacto, "
    "f.FechaCorte AS fechaCorte, f.Moneda AS moneda, f.SaldoPortal AS saldoPortal, f.SaldoSistema AS saldoSistema, "
    "f.Diferencia AS diferencia, f.Completa AS completa, f.Revisada AS revisada, f.Creado AS creado"
)


def listar_fotos(id_portal: int | None, limite: int = 50) -> list[dict]:
    filtro, params = ("WHERE f.IdPortal = ?", (id_portal,)) if id_portal else ("", ())
    return fetch_all(
        f"SELECT TOP {min(int(limite), LIMITE_MAXIMO)} {_COLS_FOTO} FROM dbo.Portales_EstadoCuenta f "
        f"JOIN dbo.Portales p ON p.IdPortal = f.IdPortal {filtro} ORDER BY f.IdFoto DESC",
        params,
    )


def obtener_foto(id_foto: int) -> dict | None:
    foto = fetch_one(f"SELECT {_COLS_FOTO} FROM dbo.Portales_EstadoCuenta f JOIN dbo.Portales p ON p.IdPortal = f.IdPortal "
                     "WHERE f.IdFoto = ?", (id_foto,))
    if foto:
        foto["movimientos"] = fetch_all(
            "SELECT Fecha AS fecha, Comprobante AS comprobante, Detalle AS detalle, Debe AS debe, Haber AS haber, "
            "Saldo AS saldo FROM dbo.Portales_EstadoCuentaMovimientos WHERE IdFoto = ? ORDER BY IdMovimiento",
            (id_foto,),
        )
    return foto


def marcar_foto_revisada(id_foto: int, revisada: bool) -> int:
    return execute_write("UPDATE dbo.Portales_EstadoCuenta SET Revisada = ? WHERE IdFoto = ?", (revisada, id_foto))


# --- Resumen para el menú ----------------------------------------------------

# Una corrida interrumpida (`incompleta`) o salteada no dice nada del portal: cuenta la última que terminó (como 037).
_ESTADOS_ERROR = ("error", "credenciales_rechazadas", "portal_cambio", "sin_credenciales")


def portal_por_host(host: str) -> dict | None:
    """Portal por dominio, aunque esté dado de baja (ej. la Municipalidad, que solo sirve para el recordatorio)."""
    return fetch_one("SELECT TOP 1 IdPortal AS idPortal, Url AS url, IdContacto AS idContacto, IdCredencial AS idCredencial, "
                     "CodigoConector AS codigoConector FROM dbo.Portales WHERE Url LIKE ? ORDER BY IdPortal",
                     (f"%://{host}/%",))


def hay_tasa_vial(id_organismo: int, desde) -> bool:
    """Boleta de Tasa Vial (tipo 8) cargada en Impuestos desde `desde`."""
    return fetch_one("SELECT TOP 1 1 AS x FROM dbo.Impuestos WHERE IdOrganismo = ? AND IdTipoImpuesto = 8 AND Fecha >= ?",
                     (id_organismo, desde)) is not None


def dato_credencial(id_credencial: int, nombre: str) -> str | None:
    """Dato no secreto de una credencial (ej. "Número de cuenta")."""
    fila = fetch_one("SELECT ValorTexto AS v FROM dbo.Boveda_CredencialDatos WHERE IdCredencial = ? AND Nombre = ? "
                     "AND Secreto = 0", (id_credencial, nombre))
    return fila["v"] if fila else None


def resumen(portales: list[int] | None = None) -> dict:
    filtro_d = filtro_c = filtro_f = ""
    params: tuple = ()
    if portales:
        marcas = ", ".join("?" for _ in portales)
        filtro_d = f" AND d.IdPortal IN ({marcas})"
        filtro_c = f" AND u.IdPortal IN ({marcas})"
        filtro_f = f" AND f.IdPortal IN ({marcas})"
        params = tuple(portales)
    ultimas = fetch_all(
        "SELECT u.Estado AS estado FROM (SELECT c.IdPortal, c.Estado, "
        " ROW_NUMBER() OVER (PARTITION BY c.IdPortal ORDER BY c.IdCorrida DESC) AS rn "
        " FROM dbo.Portales_Corridas c WHERE c.Estado NOT IN ('en_curso', 'salteada', 'incompleta')) u "
        f"WHERE u.rn = 1{filtro_c}", params)
    diferencias = fetch_one(
        "SELECT COUNT(*) AS n FROM (SELECT f.IdPortal, f.Moneda, f.Diferencia, f.Completa, f.Revisada, "
        " ROW_NUMBER() OVER (PARTITION BY f.IdPortal, f.Moneda ORDER BY f.IdFoto DESC) AS rn "
        f" FROM dbo.Portales_EstadoCuenta f WHERE 1 = 1{filtro_f}) x "
        "WHERE x.rn = 1 AND x.Completa = 1 AND x.Revisada = 0 AND x.Diferencia IS NOT NULL AND x.Diferencia <> 0",
        params)["n"]
    errores = sum(1 for u in ultimas if u["estado"] in _ESTADOS_ERROR)
    intervencion = sum(1 for u in ultimas if u["estado"] == "requiere_intervencion")
    pendientes = fetch_one(
        f"SELECT COUNT(*) AS n FROM dbo.Portales_Documentos d WHERE d.EstadoCarga = 'pendiente'{filtro_d}", params)["n"]
    # Lo pendiente de cargar o revisar se avisa en el menú de cada módulo (043): no suma al aviso de la bóveda.
    return {"pendientesCarga": pendientes, "conError": errores, "requiereIntervencion": intervencion,
            "diferenciasSaldo": diferencias, "total": errores + intervencion + diferencias}
