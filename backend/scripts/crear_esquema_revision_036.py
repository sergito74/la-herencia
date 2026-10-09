"""036 — Esquema de la revisión sistemática de cuentas (solo en `WC`).

Crea, de forma idempotente:
  * dbo.RevisionCortes            (corte vigente del método; la fila más nueva manda)
  * dbo.RevisionFichas            (una fila por cuenta con lo que decide una persona; la etapa se calcula)
  * dbo.RevisionPagosSinFactura   (marcas sobre los pagos que el detector no pudo respaldar)
  * dbo.RevisionSaldosExternos    (saldo informado por el proveedor, el banco o la tarjeta)
  * dbo.RevisionTableroFotos      (foto semanal del tablero)
y carga el corte inicial 30/09/2026 si la tabla de cortes está vacía.

Uso (desde backend/):
    python -m scripts.crear_esquema_revision_036 --verificar   # no escribe
    python -m scripts.crear_esquema_revision_036               # respaldo verificado y creación
    python -m scripts.crear_esquema_revision_036 --revertir    # borra las tablas nuevas (si no se usaron)
"""

from __future__ import annotations

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

# De la más dependiente a la menos (orden de borrado al revertir)
TABLAS = ("RevisionTableroFotos", "RevisionSaldosExternos", "RevisionPagosSinFactura", "RevisionFichas", "RevisionCortes")

CORTE_INICIAL = ("2026-09-30", "Primer corte: cierre del mes 9")

DDL = [
    """
    IF OBJECT_ID('dbo.RevisionCortes', 'U') IS NULL
    CREATE TABLE dbo.RevisionCortes (
        IdCorte int IDENTITY(1,1) NOT NULL CONSTRAINT PK_RevisionCortes PRIMARY KEY,
        Corte date NOT NULL,
        Motivo varchar(200) NULL,
        Usuario varchar(60) NOT NULL,
        Fecha datetime2 NOT NULL CONSTRAINT DF_RevisionCortes_Fecha DEFAULT SYSDATETIME()
    )
    """,
    """
    IF OBJECT_ID('dbo.RevisionFichas', 'U') IS NULL
    CREATE TABLE dbo.RevisionFichas (
        IdContacto int NOT NULL CONSTRAINT PK_RevisionFichas PRIMARY KEY,
        Estado varchar(24) NOT NULL CONSTRAINT DF_RevisionFichas_Estado DEFAULT 'pendiente'
            CONSTRAINT CK_RevisionFichas_Estado CHECK (Estado IN ('pendiente', 'en-proceso', 'esperando-evidencia',
                                                                    'esperando-sergio', 'cerrada', 'cerrada-con-excepcion')),
        InventarioFuentes nvarchar(max) NULL,
        Nota varchar(500) NULL,
        PreguntaBloqueante varchar(300) NULL,
        Corte date NULL,
        SaldoAlCierre money NULL,
        Moneda varchar(10) NULL,
        MotivoExcepcion varchar(500) NULL,
        UsuarioCierre varchar(60) NULL,
        FechaCierre datetime2 NULL,
        UsuarioActualiza varchar(60) NULL,
        FechaActualiza datetime2 NOT NULL CONSTRAINT DF_RevisionFichas_Fecha DEFAULT SYSDATETIME(),
        CONSTRAINT CK_RevisionFichas_Excepcion CHECK (Estado <> 'cerrada-con-excepcion' OR MotivoExcepcion IS NOT NULL)
    )
    """,
    """
    IF OBJECT_ID('dbo.RevisionPagosSinFactura', 'U') IS NULL
    CREATE TABLE dbo.RevisionPagosSinFactura (
        IdMarca int IDENTITY(1,1) NOT NULL CONSTRAINT PK_RevisionPagosSinFactura PRIMARY KEY,
        IdContacto int NOT NULL,
        Medio varchar(20) NOT NULL,
        IdMovimiento int NOT NULL,
        Estado varchar(24) NOT NULL CONSTRAINT CK_RevisionPagosSinFactura_Estado
            CHECK (Estado IN ('pendiente', 'factura-cargada', 'sin-documento', 'anticipo', 'venta-cargada')),
        IdCompra int NULL,
        TipoVenta varchar(20) NULL,
        IdVenta int NULL,
        FuenteRespaldo varchar(20) NULL CONSTRAINT CK_RevisionPagosSinFactura_Fuente
            CHECK (FuenteRespaldo IN ('portal', 'estado-de-cuenta', 'pdf')),
        Nota varchar(500) NULL,
        Usuario varchar(60) NOT NULL,
        Fecha datetime2 NOT NULL CONSTRAINT DF_RevisionPagosSinFactura_Fecha DEFAULT SYSDATETIME(),
        CONSTRAINT CK_RevisionPagosSinFactura_Nota CHECK (Estado <> 'sin-documento' OR Nota IS NOT NULL)
    )
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_RevisionPagosSinFactura'
                   AND object_id = OBJECT_ID('dbo.RevisionPagosSinFactura'))
    CREATE UNIQUE INDEX UX_RevisionPagosSinFactura ON dbo.RevisionPagosSinFactura (IdContacto, Medio, IdMovimiento)
    """,
    """
    IF OBJECT_ID('dbo.RevisionSaldosExternos', 'U') IS NULL
    CREATE TABLE dbo.RevisionSaldosExternos (
        IdSaldoExterno int IDENTITY(1,1) NOT NULL CONSTRAINT PK_RevisionSaldosExternos PRIMARY KEY,
        IdContacto int NOT NULL,
        FechaSaldo date NOT NULL,
        Saldo money NOT NULL,
        Moneda varchar(10) NOT NULL CONSTRAINT CK_RevisionSaldosExternos_Moneda CHECK (Moneda IN ('Pesos', 'Dolares')),
        Fuente varchar(20) NOT NULL CONSTRAINT CK_RevisionSaldosExternos_Fuente
            CHECK (Fuente IN ('portal', 'pdf', 'mail', 'banco', 'tarjeta', 'sin-estado')),
        Referencia varchar(400) NULL,
        Nota varchar(500) NULL,
        Usuario varchar(60) NOT NULL,
        Fecha datetime2 NOT NULL CONSTRAINT DF_RevisionSaldosExternos_Fecha DEFAULT SYSDATETIME(),
        Anulado bit NOT NULL CONSTRAINT DF_RevisionSaldosExternos_Anulado DEFAULT 0,
        CONSTRAINT CK_RevisionSaldosExternos_Nota CHECK (Fuente <> 'sin-estado' OR Nota IS NOT NULL)
    )
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_RevisionSaldosExternos_Contacto'
                   AND object_id = OBJECT_ID('dbo.RevisionSaldosExternos'))
    CREATE INDEX IX_RevisionSaldosExternos_Contacto ON dbo.RevisionSaldosExternos (IdContacto, FechaSaldo)
    """,
    """
    IF OBJECT_ID('dbo.RevisionTableroFotos', 'U') IS NULL
    CREATE TABLE dbo.RevisionTableroFotos (
        IdFoto int IDENTITY(1,1) NOT NULL CONSTRAINT PK_RevisionTableroFotos PRIMARY KEY,
        Semana date NOT NULL CONSTRAINT UQ_RevisionTableroFotos_Semana UNIQUE,
        Corte date NOT NULL,
        Datos nvarchar(max) NOT NULL,
        Usuario varchar(60) NULL,
        Fecha datetime2 NOT NULL CONSTRAINT DF_RevisionTableroFotos_Fecha DEFAULT SYSDATETIME()
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
        for t in TABLAS:
            existe = cur.execute("SELECT OBJECT_ID(?, 'U')", f"dbo.{t}").fetchone()[0] is not None
            print(f"dbo.{t}: {'existe' if existe else 'se creará'}")
        print("Solo verificación: no se escribió nada.")
    finally:
        conn.close()


def aplicar() -> None:
    from src.features.vinculos.backup import backup_verificado

    print(f"Respaldo verificado: {backup_verificado('esquema-revision-036')}")
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        for sql in DDL:
            cur.execute(sql)
        cur.execute(
            "IF NOT EXISTS (SELECT 1 FROM dbo.RevisionCortes) "
            "INSERT INTO dbo.RevisionCortes (Corte, Motivo, Usuario) VALUES (?, ?, 'esquema-036')",
            CORTE_INICIAL[0], CORTE_INICIAL[1],
        )
        conn.commit()
        for t in TABLAS:
            n = cur.execute(f"SELECT COUNT(*) FROM dbo.{t}").fetchone()[0]
            print(f"dbo.{t}: {n} filas")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def revertir() -> None:
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        for t in TABLAS:
            if t == "RevisionCortes":
                continue
            if cur.execute("SELECT OBJECT_ID(?, 'U')", f"dbo.{t}").fetchone()[0] is None:
                continue
            usadas = cur.execute(f"SELECT COUNT(*) FROM dbo.{t}").fetchone()[0]
            if usadas:
                raise SystemExit(f"dbo.{t} tiene {usadas} filas: no se borran las tablas.")
        for t in TABLAS:
            cur.execute(f"IF OBJECT_ID('dbo.{t}', 'U') IS NOT NULL DROP TABLE dbo.{t}")
        conn.commit()
        print("Tablas de la revisión sistemática eliminadas.")
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
