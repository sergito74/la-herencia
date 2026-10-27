"""042 — Esquema de la Bóveda de portales (solo en `WC`).

Crea, de forma idempotente, las tablas de specs/042-boveda-portales/data-model.md:
  Boveda_Credenciales, Boveda_CredencialDatos, Portales, Portales_Autorizaciones,
  Portales_Programacion, Portales_Corridas, Portales_Documentos,
  Portales_EstadoCuenta, Portales_EstadoCuentaMovimientos, Boveda_Auditoria.

Uso (desde backend/):
    python -m scripts.crear_esquema_boveda_042 --verificar    # no escribe
    python -m scripts.crear_esquema_boveda_042                # respaldo verificado y creación
    python -m scripts.crear_esquema_boveda_042 --revertir     # borra las tablas si no hubo corridas ni portales
    python -m scripts.crear_esquema_boveda_042 --migrar-037   # T031: peajes a la bóveda (respaldo verificado antes)
    python -m scripts.crear_esquema_boveda_042 --registrar-portales  # T037: alta de los portales autorizados

Los pasos son idempotentes: se pueden repetir sin duplicar. Las tablas de 037
quedan intactas; las credenciales del keyring de 037 no se borran.
"""

from __future__ import annotations

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

# Orden de borrado (hijas primero).
TABLAS = (
    "Portales_EstadoCuentaMovimientos", "Portales_EstadoCuenta", "Portales_Documentos", "Portales_Corridas",
    "Portales_Programacion", "Portales_Autorizaciones", "Portales", "Boveda_CredencialDatos",
    "Boveda_Credenciales", "Boveda_Auditoria",
)

DDL = [
    """
    IF OBJECT_ID('dbo.Boveda_Credenciales', 'U') IS NULL
    CREATE TABLE dbo.Boveda_Credenciales (
        IdCredencial int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Boveda_Credenciales PRIMARY KEY,
        Nombre nvarchar(80) NOT NULL CONSTRAINT UQ_Boveda_Credenciales_Nombre UNIQUE,
        Titular varchar(10) NOT NULL CONSTRAINT CK_Boveda_Credenciales_Titular CHECK (Titular IN ('empresa', 'socio')),
        IdSocio int NULL,
        Usuario nvarchar(120) NULL,
        ClaveCifrada varbinary(512) NULL,
        ClaveActualizada datetime2 NULL,
        Rechazada bit NOT NULL CONSTRAINT DF_Boveda_Credenciales_Rechazada DEFAULT 0,
        Activo bit NOT NULL CONSTRAINT DF_Boveda_Credenciales_Activo DEFAULT 1
    )
    """,
    """
    IF OBJECT_ID('dbo.Boveda_CredencialDatos', 'U') IS NULL
    CREATE TABLE dbo.Boveda_CredencialDatos (
        IdDato int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Boveda_CredencialDatos PRIMARY KEY,
        IdCredencial int NOT NULL CONSTRAINT FK_Boveda_CredencialDatos_Credencial
            REFERENCES dbo.Boveda_Credenciales (IdCredencial),
        Nombre nvarchar(60) NOT NULL,
        Secreto bit NOT NULL,
        ValorTexto nvarchar(200) NULL,
        ValorCifrado varbinary(512) NULL,
        CONSTRAINT UQ_Boveda_CredencialDatos UNIQUE (IdCredencial, Nombre),
        CONSTRAINT CK_Boveda_CredencialDatos_Valor CHECK (
            (Secreto = 1 AND ValorTexto IS NULL) OR (Secreto = 0 AND ValorCifrado IS NULL))
    )
    """,
    """
    IF OBJECT_ID('dbo.Portales', 'U') IS NULL
    CREATE TABLE dbo.Portales (
        IdPortal int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Portales PRIMARY KEY,
        Nombre nvarchar(80) NOT NULL CONSTRAINT UQ_Portales_Nombre UNIQUE,
        Url nvarchar(400) NOT NULL CONSTRAINT CK_Portales_Url CHECK (Url LIKE 'http://%' OR Url LIKE 'https://%'),
        Tipo varchar(12) NOT NULL CONSTRAINT CK_Portales_Tipo
            CHECK (Tipo IN ('organismo', 'proveedor', 'cliente', 'banco', 'otro')),
        IdContacto int NULL,
        IdCredencial int NULL CONSTRAINT FK_Portales_Credencial REFERENCES dbo.Boveda_Credenciales (IdCredencial),
        CodigoConector varchar(30) NULL,
        Notas nvarchar(1000) NULL,
        Activo bit NOT NULL CONSTRAINT DF_Portales_Activo DEFAULT 1
    )
    """,
    """
    IF OBJECT_ID('dbo.Portales_Autorizaciones', 'U') IS NULL
    CREATE TABLE dbo.Portales_Autorizaciones (
        IdAutorizacion int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Portales_Autorizaciones PRIMARY KEY,
        IdPortal int NOT NULL CONSTRAINT FK_Portales_Autorizaciones_Portal REFERENCES dbo.Portales (IdPortal),
        Alcance varchar(30) NOT NULL CONSTRAINT CK_Portales_Autorizaciones_Alcance CHECK (Alcance = 'solo_lectura_descarga'),
        AutorizadoPor nvarchar(60) NOT NULL,
        Fecha date NOT NULL,
        Fuente nvarchar(300) NULL,
        RevocadaPor nvarchar(60) NULL,
        Revocada datetime2 NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Portales_Programacion', 'U') IS NULL
    CREATE TABLE dbo.Portales_Programacion (
        IdPortal int NOT NULL CONSTRAINT PK_Portales_Programacion PRIMARY KEY
            CONSTRAINT FK_Portales_Programacion_Portal REFERENCES dbo.Portales (IdPortal),
        Frecuencia varchar(10) NOT NULL CONSTRAINT CK_Portales_Programacion_Frecuencia
            CHECK (Frecuencia IN ('desactivada', 'diaria', 'semanal', 'mensual')),
        DiaSemana tinyint NULL CONSTRAINT CK_Portales_Programacion_DiaSemana CHECK (DiaSemana BETWEEN 1 AND 7),
        DiaMes tinyint NULL CONSTRAINT CK_Portales_Programacion_DiaMes CHECK (DiaMes BETWEEN 1 AND 28),
        Hora time(0) NOT NULL CONSTRAINT DF_Portales_Programacion_Hora DEFAULT '07:00',
        ProximaCorrida datetime2 NULL,
        Suspendida bit NOT NULL CONSTRAINT DF_Portales_Programacion_Suspendida DEFAULT 0,
        MotivoSuspension nvarchar(200) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Portales_Corridas', 'U') IS NULL
    CREATE TABLE dbo.Portales_Corridas (
        IdCorrida int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Portales_Corridas PRIMARY KEY,
        IdPortal int NOT NULL CONSTRAINT FK_Portales_Corridas_Portal REFERENCES dbo.Portales (IdPortal),
        Origen varchar(12) NOT NULL CONSTRAINT CK_Portales_Corridas_Origen CHECK (Origen IN ('programada', 'manual', 'migrada037')),
        Usuario nvarchar(60) NULL,
        Inicio datetime2 NOT NULL CONSTRAINT DF_Portales_Corridas_Inicio DEFAULT SYSDATETIME(),
        Fin datetime2 NULL,
        Estado varchar(24) NOT NULL CONSTRAINT CK_Portales_Corridas_Estado CHECK (Estado IN (
            'en_curso', 'ok', 'error', 'requiere_intervencion', 'credenciales_rechazadas', 'sin_autorizacion',
            'sin_credenciales', 'portal_cambio', 'incompleta', 'salteada')),
        Nuevos int NOT NULL CONSTRAINT DF_Portales_Corridas_Nuevos DEFAULT 0,
        Existentes int NOT NULL CONSTRAINT DF_Portales_Corridas_Existentes DEFAULT 0,
        Cargados int NOT NULL CONSTRAINT DF_Portales_Corridas_Cargados DEFAULT 0,
        Pendientes int NOT NULL CONSTRAINT DF_Portales_Corridas_Pendientes DEFAULT 0,
        Mensaje nvarchar(400) NULL,
        IdEjecucion037 int NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Portales_Documentos', 'U') IS NULL
    CREATE TABLE dbo.Portales_Documentos (
        IdDocumento int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Portales_Documentos PRIMARY KEY,
        IdPortal int NOT NULL CONSTRAINT FK_Portales_Documentos_Portal REFERENCES dbo.Portales (IdPortal),
        Clave varchar(160) NOT NULL,
        Tipo varchar(20) NOT NULL CONSTRAINT CK_Portales_Documentos_Tipo CHECK (Tipo IN (
            'factura', 'nota_credito', 'nota_debito', 'resumen', 'certificado', 'boleta', 'poliza', 'liquidacion', 'otro')),
        Proveedor nvarchar(60) NOT NULL,
        IdContacto int NULL,
        FechaDocumento date NULL,
        NumeroDocumento varchar(30) NULL,
        TotalImpreso decimal(18,2) NULL,
        Moneda char(3) NULL CONSTRAINT CK_Portales_Documentos_Moneda CHECK (Moneda IN ('ARS', 'USD')),
        Ruta nvarchar(400) NULL,
        Sha256 char(64) NULL,
        IdCorrida int NULL CONSTRAINT FK_Portales_Documentos_Corrida REFERENCES dbo.Portales_Corridas (IdCorrida),
        EstadoCarga varchar(20) NOT NULL CONSTRAINT CK_Portales_Documentos_EstadoCarga
            CHECK (EstadoCarga IN ('cargado_auto', 'ya_cargado', 'pendiente', 'no_aplica', 'historico')),
        Motivo nvarchar(300) NULL,
        IdCompra int NULL,
        Creado datetime2 NOT NULL CONSTRAINT DF_Portales_Documentos_Creado DEFAULT SYSDATETIME(),
        CONSTRAINT UQ_Portales_Documentos_Clave UNIQUE (IdPortal, Clave)
    )
    """,
    """
    IF OBJECT_ID('dbo.Portales_EstadoCuenta', 'U') IS NULL
    CREATE TABLE dbo.Portales_EstadoCuenta (
        IdFoto int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Portales_EstadoCuenta PRIMARY KEY,
        IdPortal int NOT NULL CONSTRAINT FK_Portales_EstadoCuenta_Portal REFERENCES dbo.Portales (IdPortal),
        IdCorrida int NULL CONSTRAINT FK_Portales_EstadoCuenta_Corrida REFERENCES dbo.Portales_Corridas (IdCorrida),
        IdContacto int NULL,
        FechaCorte date NOT NULL,
        Moneda char(3) NOT NULL CONSTRAINT CK_Portales_EstadoCuenta_Moneda CHECK (Moneda IN ('ARS', 'USD')),
        SaldoPortal decimal(18,2) NOT NULL,
        SaldoSistema decimal(18,2) NULL,
        Diferencia decimal(18,2) NULL,
        Completa bit NOT NULL,
        Revisada bit NOT NULL CONSTRAINT DF_Portales_EstadoCuenta_Revisada DEFAULT 0,
        Creado datetime2 NOT NULL CONSTRAINT DF_Portales_EstadoCuenta_Creado DEFAULT SYSDATETIME()
    )
    """,
    """
    IF OBJECT_ID('dbo.Portales_EstadoCuentaMovimientos', 'U') IS NULL
    CREATE TABLE dbo.Portales_EstadoCuentaMovimientos (
        IdMovimiento int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Portales_EstadoCuentaMovimientos PRIMARY KEY,
        IdFoto int NOT NULL CONSTRAINT FK_Portales_ECM_Foto REFERENCES dbo.Portales_EstadoCuenta (IdFoto),
        Fecha date NULL,
        Comprobante nvarchar(60) NULL,
        Detalle nvarchar(200) NULL,
        Debe decimal(18,2) NULL,
        Haber decimal(18,2) NULL,
        Saldo decimal(18,2) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Boveda_Auditoria', 'U') IS NULL
    CREATE TABLE dbo.Boveda_Auditoria (
        IdEvento bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_Boveda_Auditoria PRIMARY KEY,
        Fecha datetime2 NOT NULL CONSTRAINT DF_Boveda_Auditoria_Fecha DEFAULT SYSDATETIME(),
        Usuario nvarchar(60) NULL,
        Accion varchar(30) NOT NULL,
        IdPortal int NULL,
        IdCredencial int NULL,
        Detalle nvarchar(400) NULL
    )
    """,
]


def _conexion(autocommit: bool = True):
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=autocommit)
    if conn.cursor().execute("SELECT DB_NAME()").fetchone()[0] != "WC":
        conn.close()
        raise RuntimeError("Solo sobre WC")
    return conn


def verificar() -> None:
    conn = _conexion()
    try:
        cur = conn.cursor()
        for t in reversed(TABLAS):
            existe = cur.execute("SELECT OBJECT_ID(?, 'U')", f"dbo.{t}").fetchone()[0] is not None
            print(f"dbo.{t}: {'existe' if existe else 'se creará'}")
        print("Solo verificación: no se escribió nada.")
    finally:
        conn.close()


def aplicar() -> None:
    from src.features.vinculos.backup import backup_verificado

    print(f"Respaldo verificado: {backup_verificado('esquema-boveda-042')}")
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        for sql in DDL:
            cur.execute(sql)
        conn.commit()
        for t in reversed(TABLAS):
            print(f"dbo.{t}: {cur.execute(f'SELECT COUNT(*) FROM dbo.{t}').fetchone()[0]} filas")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def revertir() -> None:
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT OBJECT_ID('dbo.Portales', 'U')").fetchone()[0]:
            usados = cur.execute("SELECT (SELECT COUNT(*) FROM dbo.Portales) + (SELECT COUNT(*) FROM dbo.Portales_Corridas)").fetchone()[0]
            if usados:
                raise SystemExit("Hay portales o corridas registrados: no se borran las tablas.")
        for t in TABLAS:
            cur.execute(f"IF OBJECT_ID('dbo.{t}', 'U') IS NOT NULL DROP TABLE dbo.{t}")
        conn.commit()
        print("Tablas de la bóveda eliminadas.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Migración de 037 (T031) -----------------------------------------------------

# Portal → (url, IdContacto, código de conector, cuenta en el keyring de 037).
PEAJES = {
    "TelepeajePlus": ("https://www.telepeajeplus.com/Login/", 328, "telepeajeplus", "telepeajeplus"),
    "TelePASE": ("https://telepase.com.ar/login", None, "telepase", "telepase"),
    "CEAMSE": ("https://ceamse.sixon.com.ar/CEAMSE_OFICINA_VIRTUAL_PROD/com.ceamseoficinavirtual.login", 314, "ceamse", "ceamse"),
    "AUBASA": ("https://autogestionaubasa.com.ar/AUBASA_OFICINA_VIRTUAL_PROD/servlet/com.aubasaoficinavirtual.login", 316,
               "aubasa", "aubasa"),
}
ESTADO_PORTAL_037 = {"ok": "ok", "error": "error", "sin_credenciales": "sin_credenciales",
                     "pendiente": "incompleta", "en_curso": "incompleta"}


def _id_portal(cur, nombre: str) -> int | None:
    fila = cur.execute("SELECT IdPortal FROM dbo.Portales WHERE Nombre = ?", nombre).fetchone()
    return fila[0] if fila else None


def _alta_portal(cur, nombre, url, tipo, id_contacto, codigo, notas, aut_fecha, aut_fuente, id_credencial=None) -> int:
    id_portal = _id_portal(cur, nombre)
    if id_portal is None:
        id_portal = cur.execute(
            "INSERT INTO dbo.Portales (Nombre, Url, Tipo, IdContacto, IdCredencial, CodigoConector, Notas) "
            "OUTPUT INSERTED.IdPortal VALUES (?, ?, ?, ?, ?, ?, ?)",
            nombre, url, tipo, id_contacto, id_credencial, codigo, notas).fetchone()[0]
        cur.execute("INSERT INTO dbo.Boveda_Auditoria (Usuario, Accion, IdPortal, Detalle) VALUES ('migracion-042', 'alta_portal', ?, ?)",
                    id_portal, nombre)
    if not cur.execute("SELECT 1 FROM dbo.Portales_Autorizaciones WHERE IdPortal = ?", id_portal).fetchone():
        cur.execute("INSERT INTO dbo.Portales_Autorizaciones (IdPortal, Alcance, AutorizadoPor, Fecha, Fuente) "
                    "VALUES (?, 'solo_lectura_descarga', 'Sergio', ?, ?)", id_portal, aut_fecha, aut_fuente)
        cur.execute("INSERT INTO dbo.Boveda_Auditoria (Usuario, Accion, IdPortal, Detalle) VALUES ('migracion-042', 'autorizar', ?, ?)",
                    id_portal, f"{aut_fecha} Sergio; {aut_fuente}")
    return id_portal


def _credencial_peaje(cur, portal: str, cuenta: str) -> int | None:
    """Copia usuario/clave del keyring de 037 a la bóveda, cifrados. No borra el keyring."""
    import keyring

    from src.features.boveda import cifrado

    nombre = f"Peajes - {portal}"
    fila = cur.execute("SELECT IdCredencial FROM dbo.Boveda_Credenciales WHERE Nombre = ?", nombre).fetchone()
    if fila:
        return fila[0]
    usuario = keyring.get_password("LaHerencia-Peajes", f"{cuenta}-usuario")
    clave = keyring.get_password("LaHerencia-Peajes", cuenta)
    if not usuario or not clave:
        print(f"  {portal}: sin credenciales en el keyring de 037; queda sin credencial.")
        return None
    id_cred = cur.execute("INSERT INTO dbo.Boveda_Credenciales (Nombre, Titular, Usuario) OUTPUT INSERTED.IdCredencial "
                          "VALUES (?, 'empresa', ?)", nombre, usuario).fetchone()[0]
    cur.execute("UPDATE dbo.Boveda_Credenciales SET ClaveCifrada = ?, ClaveActualizada = SYSDATETIME() WHERE IdCredencial = ?",
                cifrado.cifrar(clave, cifrado.aad_clave(id_cred)), id_cred)
    cur.execute("INSERT INTO dbo.Boveda_Auditoria (Usuario, Accion, IdCredencial, Detalle) "
                "VALUES ('migracion-042', 'alta_credencial', ?, 'copiada del keyring LaHerencia-Peajes')", id_cred)
    return id_cred


def migrar_037() -> None:
    from datetime import datetime, time

    from src.features.boveda.planificador import proxima_corrida
    from src.features.vinculos.backup import backup_verificado

    print(f"Respaldo verificado: {backup_verificado('boveda-migrar-037')}")
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        for portal, (url, id_contacto, codigo, cuenta) in PEAJES.items():
            id_cred = _credencial_peaje(cur, portal, cuenta)
            id_portal = _alta_portal(cur, portal, url, "proveedor", id_contacto, codigo,
                                     "Migrado de 037 (descarga de peajes).", "2026-10-16",
                                     "Autorización de Sergio 16/10/2026 (spec 037)", id_cred)
            if id_cred and not cur.execute("SELECT IdCredencial FROM dbo.Portales WHERE IdPortal = ?", id_portal).fetchone()[0]:
                cur.execute("UPDATE dbo.Portales SET IdCredencial = ? WHERE IdPortal = ?", id_cred, id_portal)
            if not cur.execute("SELECT 1 FROM dbo.Portales_Programacion WHERE IdPortal = ?", id_portal).fetchone():
                # Misma periodicidad que la tarea semanal de 037: lunes 09:00.
                cur.execute("INSERT INTO dbo.Portales_Programacion (IdPortal, Frecuencia, DiaSemana, Hora, ProximaCorrida) "
                            "VALUES (?, 'semanal', 1, '09:00', ?)",
                            id_portal, proxima_corrida("semanal", 1, None, time(9, 0), datetime.now()))
            # Corridas: una por (ejecución, portal) de 037.
            for ej, estado, inicio, fin, origen, usuario, nuevos, existentes, cargados, pendientes, error in cur.execute(
                    "SELECT e.IdEjecucion, p.Estado, e.Inicio, e.Fin, e.Origen, e.Usuario, p.Nuevos, p.Existentes, "
                    "p.Cargados, p.Pendientes, COALESCE(p.Error, e.Mensaje) FROM dbo.DescargaPeajes_EjecucionPortales p "
                    "JOIN dbo.DescargaPeajes_Ejecuciones e ON e.IdEjecucion = p.IdEjecucion WHERE p.Portal = ? "
                    "ORDER BY e.IdEjecucion", portal).fetchall():
                if cur.execute("SELECT 1 FROM dbo.Portales_Corridas WHERE IdPortal = ? AND IdEjecucion037 = ?",
                               id_portal, ej).fetchone():
                    continue
                cur.execute(
                    "INSERT INTO dbo.Portales_Corridas (IdPortal, Origen, Usuario, Inicio, Fin, Estado, Nuevos, Existentes, "
                    "Cargados, Pendientes, Mensaje, IdEjecucion037) VALUES (?, 'migrada037', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    id_portal, usuario or origen, inicio, fin or inicio, ESTADO_PORTAL_037.get(estado, "incompleta"),
                    nuevos, existentes, cargados, pendientes, error, ej)
            cur.execute(
                "INSERT INTO dbo.Portales_Documentos (IdPortal, Clave, Tipo, Proveedor, IdContacto, FechaDocumento, "
                "NumeroDocumento, TotalImpreso, Moneda, Ruta, IdCorrida, EstadoCarga, Motivo, IdCompra, Creado) "
                "SELECT ?, d.Clave, 'factura', d.Proveedor, d.IdContacto, d.FechaDocumento, d.NumeroDocumento, "
                "d.TotalImpreso, 'ARS', d.Ruta, c.IdCorrida, d.EstadoCarga, d.Motivo, d.IdCompra, d.Creado "
                "FROM dbo.DescargaPeajes_Documentos d "
                "LEFT JOIN dbo.Portales_Corridas c ON c.IdPortal = ? AND c.IdEjecucion037 = d.IdEjecucion "
                "WHERE d.Portal = ? AND NOT EXISTS (SELECT 1 FROM dbo.Portales_Documentos x WHERE x.IdPortal = ? AND x.Clave = d.Clave)",
                id_portal, id_portal, portal, id_portal)
        # Control: mismos totales que 037.
        for portal in PEAJES:
            id_portal = _id_portal(cur, portal)
            a = cur.execute("SELECT COUNT(*) FROM dbo.DescargaPeajes_Documentos WHERE Portal = ?", portal).fetchone()[0]
            b = cur.execute("SELECT COUNT(*) FROM dbo.Portales_Documentos WHERE IdPortal = ?", id_portal).fetchone()[0]
            c = cur.execute("SELECT COUNT(*) FROM dbo.DescargaPeajes_EjecucionPortales WHERE Portal = ?", portal).fetchone()[0]
            d = cur.execute("SELECT COUNT(*) FROM dbo.Portales_Corridas WHERE IdPortal = ? AND Origen = 'migrada037'",
                            id_portal).fetchone()[0]
            if a > b or c != d:
                raise RuntimeError(f"{portal}: documentos 037={a} bóveda={b}; corridas 037={c} bóveda={d}")
            print(f"  {portal}: documentos 037={a} bóveda={b}; corridas 037={c} bóveda={d}")
        conn.commit()
        print("Migración de 037 aplicada.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Alta de portales autorizados (T037) -------------------------------------------

# Nombre → (url, tipo, IdContacto verificado en Contactos 27/10/2026, fecha de autorización, fuente, notas).
PORTALES_NUEVOS = {
    "Bayá Casal": ("https://extranet.ebayacasal.com.ar/", "proveedor", 226, "2026-10-19",
                   "Autorización de Sergio 19/10/2026 (local-access.md)", None),
    "Cargill": ("https://www.mycargill.com/cascsa/v2/login", "cliente", 258, "2026-10-20",
                "Autorización de Sergio 20/10/2026 (reference_portal_cargill)", None),
    "ARCA": ("https://auth.afip.gob.ar/contribuyente_/login.xhtml", "organismo", 119, "2026-10-27",
             "Pedido de Sergio 27/10/2026 (spec 042, Clarifications)", None),
    "ARBA": ("https://www.arba.gov.ar/", "organismo", 12, "2026-10-27",
             "Pedido de Sergio 27/10/2026 (spec 042, Clarifications)", "Enlace general sin verificar: ajustar al acceso de Mi ARBA."),
    "Municipalidad de Bolívar": ("https://www.bolivar.gob.ar/", "organismo", 72, "2026-10-27",
                                 "Pedido de Sergio 27/10/2026 (spec 042, Clarifications)",
                                 "Enlace general sin verificar: ajustar al acceso de autogestión de tasas."),
    "Sancor Seguros": ("https://www.sancorseguros.com.ar/", "proveedor", 171, "2026-10-27",
                       "Pedido de Sergio 27/10/2026 (spec 042, Clarifications)", "Enlace general sin verificar: ajustar al acceso de clientes."),
    "Allianz": ("https://www.allianz.com.ar/", "proveedor", 515, "2026-10-27",
                "Pedido de Sergio 27/10/2026 (spec 042, Clarifications)", "Enlace general sin verificar: ajustar al acceso de clientes."),
    "Jáuregui y Morales": ("https://sin-enlace.invalid/", "proveedor", 48, "2026-10-27",
                           "Pedido de Sergio 27/10/2026 (spec 042, Clarifications)",
                           "Falta el enlace del portal (.invalid = marcador): completarlo al cargar la credencial."),
    "Lartirigoyen": ("https://www.lartirigoyen.com.ar/", "proveedor", 61, "2026-10-27",
                     "Pedido de Sergio 27/10/2026 (spec 042, Clarifications)", "Enlace general sin verificar: ajustar al acceso de clientes."),
}


def registrar_portales() -> None:
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        for nombre, (url, tipo, id_contacto, fecha, fuente, notas) in PORTALES_NUEVOS.items():
            razon = cur.execute("SELECT [Razon Social] FROM dbo.Contactos WHERE IdContacto = ?", id_contacto).fetchone()
            if razon is None:
                raise RuntimeError(f"{nombre}: el contacto {id_contacto} no existe")
            nuevo = _id_portal(cur, nombre) is None
            id_portal = _alta_portal(cur, nombre, url, tipo, id_contacto, None, notas, fecha, fuente)
            print(f"  {nombre}: portal {id_portal} ({'nuevo' if nuevo else 'ya estaba'}), contacto {id_contacto} {razon[0]}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(argv: list[str]) -> None:
    if "--verificar" in argv:
        verificar()
    elif "--revertir" in argv:
        revertir()
    elif "--migrar-037" in argv:
        migrar_037()
    elif "--registrar-portales" in argv:
        registrar_portales()
    else:
        aplicar()


if __name__ == "__main__":
    main(sys.argv[1:])
