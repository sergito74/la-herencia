"""043 — Esquema de la rutina de documentos nuevos (solo en `WC`).

Crea, de forma idempotente, las tablas de specs/043-rutina-documentos-nuevos/data-model.md:
  Rutina_Corridas, Rutina_Programacion, Rutina_MarcaMails, DocumentosNuevos.
Pasa a `DocumentosNuevos` lo cargado solo sin revisar (T011) y quita `Portales_Documentos.Revisado`
(lo reemplaza `DocumentosNuevos`).

Uso (desde backend/):
    python -m scripts.crear_esquema_rutina_043 --verificar    # no escribe
    python -m scripts.crear_esquema_rutina_043                # respaldo verificado y creación
    python -m scripts.crear_esquema_rutina_043 --revertir     # borra las tablas si no hubo corridas y restaura Revisado
"""

from __future__ import annotations

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

# Orden de borrado (hijas primero).
TABLAS = ("DocumentosNuevos", "Rutina_MarcaMails", "Rutina_Programacion", "Rutina_Corridas")

DDL = [
    """
    IF OBJECT_ID('dbo.Rutina_Corridas', 'U') IS NULL
    CREATE TABLE dbo.Rutina_Corridas (
        IdRutinaCorrida int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Rutina_Corridas PRIMARY KEY,
        Inicio datetime2(0) NOT NULL CONSTRAINT DF_Rutina_Corridas_Inicio DEFAULT SYSDATETIME(),
        Fin datetime2(0) NULL,
        Origen nvarchar(20) NOT NULL CONSTRAINT CK_Rutina_Corridas_Origen CHECK (Origen IN ('programada', 'prueba')),
        Estado nvarchar(20) NOT NULL CONSTRAINT CK_Rutina_Corridas_Estado
            CHECK (Estado IN ('en_curso', 'ok', 'con_problemas', 'incompleta')),
        CuentasCorridas int NOT NULL CONSTRAINT DF_Rutina_Corridas_CC DEFAULT 0,
        CuentasConProblemas int NOT NULL CONSTRAINT DF_Rutina_Corridas_CP DEFAULT 0,
        MailsLeidos int NOT NULL CONSTRAINT DF_Rutina_Corridas_ML DEFAULT 0,
        DocumentosNuevos int NOT NULL CONSTRAINT DF_Rutina_Corridas_DN DEFAULT 0,
        CargadosSolos int NOT NULL CONSTRAINT DF_Rutina_Corridas_CS DEFAULT 0,
        ParaCargarAMano int NOT NULL CONSTRAINT DF_Rutina_Corridas_PC DEFAULT 0,
        Mensaje nvarchar(400) NULL
    )
    """,
    # Una sola corrida en curso a la vez.
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_Rutina_Corridas_EnCurso')
    CREATE UNIQUE INDEX UX_Rutina_Corridas_EnCurso ON dbo.Rutina_Corridas (Estado) WHERE Estado = 'en_curso'
    """,
    """
    IF OBJECT_ID('dbo.Rutina_Programacion', 'U') IS NULL
    CREATE TABLE dbo.Rutina_Programacion (
        Id tinyint NOT NULL CONSTRAINT PK_Rutina_Programacion PRIMARY KEY CONSTRAINT CK_Rutina_Programacion_Unica CHECK (Id = 1),
        Horarios nvarchar(50) NOT NULL,
        ProximaCorrida datetime2(0) NULL,
        Activa bit NOT NULL CONSTRAINT DF_Rutina_Programacion_Activa DEFAULT 1
    )
    """,
    "IF NOT EXISTS (SELECT 1 FROM dbo.Rutina_Programacion) "
    "INSERT INTO dbo.Rutina_Programacion (Id, Horarios, ProximaCorrida, Activa) VALUES (1, N'07:00,14:00', NULL, 1)",
    """
    IF OBJECT_ID('dbo.Rutina_MarcaMails', 'U') IS NULL
    CREATE TABLE dbo.Rutina_MarcaMails (
        Almacen nvarchar(200) NOT NULL CONSTRAINT PK_Rutina_MarcaMails PRIMARY KEY,
        UltimoRecibido datetime2(0) NOT NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.DocumentosNuevos', 'U') IS NULL
    CREATE TABLE dbo.DocumentosNuevos (
        IdDocumentoNuevo int IDENTITY(1,1) NOT NULL CONSTRAINT PK_DocumentosNuevos PRIMARY KEY,
        IdRutinaCorrida int NULL CONSTRAINT FK_DocumentosNuevos_Corrida REFERENCES dbo.Rutina_Corridas (IdRutinaCorrida),
        Origen nvarchar(10) NOT NULL CONSTRAINT CK_DocumentosNuevos_Origen CHECK (Origen IN ('portal', 'mail')),
        IdPortal int NULL CONSTRAINT FK_DocumentosNuevos_Portal REFERENCES dbo.Portales (IdPortal),
        IdDocumentoPortal int NULL CONSTRAINT FK_DocumentosNuevos_DocPortal REFERENCES dbo.Portales_Documentos (IdDocumento),
        MailEntryId nvarchar(200) NULL,
        MailRemitente nvarchar(200) NULL,
        MailAsunto nvarchar(200) NULL,
        MailRecibido datetime2(0) NULL,
        Sha256 char(64) NOT NULL,
        Ruta nvarchar(400) NOT NULL,
        Tipo nvarchar(30) NOT NULL,
        Modulo nvarchar(30) NOT NULL CONSTRAINT CK_DocumentosNuevos_Modulo CHECK (Modulo IN
            ('compras', 'impuestos', 'ventas', 'tesoreria', 'cuentas_corrientes', 'sin_clasificar')),
        IdContacto int NULL,
        Fecha date NULL,
        Numero nvarchar(50) NULL,
        Total decimal(18,2) NULL,
        Estado nvarchar(20) NOT NULL CONSTRAINT CK_DocumentosNuevos_Estado
            CHECK (Estado IN ('cargado_solo', 'para_cargar', 'ya_estaba')),
        Motivo nvarchar(300) NULL,
        IdRegistro int NULL,
        Revisado datetime2(0) NULL,
        RevisadoPor nvarchar(60) NULL,
        ModuloAnterior nvarchar(30) NULL,
        ModuloCambiado datetime2(0) NULL,
        ModuloCambiadoPor nvarchar(60) NULL,
        Creado datetime2(0) NOT NULL CONSTRAINT DF_DocumentosNuevos_Creado DEFAULT SYSDATETIME(),
        CONSTRAINT UQ_DocumentosNuevos_Sha_Modulo UNIQUE (Sha256, Modulo)
    )
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DocumentosNuevos_Pendientes')
    CREATE INDEX IX_DocumentosNuevos_Pendientes ON dbo.DocumentosNuevos (Modulo, IdDocumentoNuevo)
        WHERE Estado IN ('cargado_solo', 'para_cargar') AND Revisado IS NULL
    """,
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DocumentosNuevos_Mail') "
    "CREATE INDEX IX_DocumentosNuevos_Mail ON dbo.DocumentosNuevos (MailEntryId, Sha256) WHERE MailEntryId IS NOT NULL",
]

# T011: lo que la bóveda cargó solo y nadie revisó todavía pasa a los avisos del módulo (antes de quitar la columna).
TRASPASO_PENDIENTES = """
    IF COL_LENGTH('dbo.Portales_Documentos', 'Revisado') IS NOT NULL
    EXEC('INSERT INTO dbo.DocumentosNuevos (Origen, IdPortal, IdDocumentoPortal, Sha256, Ruta, Tipo, Modulo, IdContacto,
              Fecha, Numero, Total, Estado, IdRegistro, Creado)
          SELECT ''portal'', d.IdPortal, d.IdDocumento, d.Sha256, d.Ruta, d.Tipo, ''compras'', d.IdContacto,
                 d.FechaDocumento, d.NumeroDocumento, d.TotalImpreso, ''cargado_solo'', d.IdCompra, d.Creado
          FROM dbo.Portales_Documentos d
          WHERE d.EstadoCarga = ''cargado_auto'' AND d.Revisado IS NULL AND d.Sha256 IS NOT NULL AND d.Ruta IS NOT NULL
            AND d.Tipo IN (''factura'', ''nota_credito'', ''nota_debito'')
            AND NOT EXISTS (SELECT 1 FROM dbo.DocumentosNuevos n WHERE n.Sha256 = d.Sha256 AND n.Modulo = ''compras'')')
"""

# El listado de revisión de la bóveda (27/10/2026) se retira: su columna se elimina.
QUITAR_REVISADO = """
    IF COL_LENGTH('dbo.Portales_Documentos', 'Revisado') IS NOT NULL
        ALTER TABLE dbo.Portales_Documentos DROP COLUMN Revisado
"""
RESTAURAR_REVISADO = """
    IF COL_LENGTH('dbo.Portales_Documentos', 'Revisado') IS NULL
    BEGIN
        ALTER TABLE dbo.Portales_Documentos ADD Revisado datetime2(0) NULL;
        EXEC('UPDATE dbo.Portales_Documentos SET Revisado = Creado WHERE EstadoCarga = ''cargado_auto''');
    END
"""


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
        tiene = cur.execute("SELECT COL_LENGTH('dbo.Portales_Documentos', 'Revisado')").fetchone()[0] is not None
        print(f"Portales_Documentos.Revisado: {'se eliminará' if tiene else 'ya no está'}")
        print("Solo verificación: no se escribió nada.")
    finally:
        conn.close()


def aplicar() -> None:
    from src.features.vinculos.backup import backup_verificado

    print(f"Respaldo verificado: {backup_verificado('esquema-rutina-043')}")
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        for sql in DDL:
            cur.execute(sql)
        cur.execute(TRASPASO_PENDIENTES)
        print(f"Cargados solos sin revisar pasados a los avisos: {cur.rowcount}")
        cur.execute(QUITAR_REVISADO)
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
        if cur.execute("SELECT OBJECT_ID('dbo.Rutina_Corridas', 'U')").fetchone()[0]:
            if cur.execute("SELECT COUNT(*) FROM dbo.Rutina_Corridas WHERE Origen = 'programada'").fetchone()[0]:
                raise SystemExit("La rutina ya corrió: no se borran las tablas.")
        for t in TABLAS:
            cur.execute(f"IF OBJECT_ID('dbo.{t}', 'U') IS NOT NULL DROP TABLE dbo.{t}")
        cur.execute(RESTAURAR_REVISADO)
        conn.commit()
        print("Tablas de la rutina eliminadas; Portales_Documentos.Revisado restaurada.")
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
    else:
        aplicar()


if __name__ == "__main__":
    main(sys.argv[1:])
