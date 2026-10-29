"""044 — Esquema del detector de facturas faltantes (solo en `WC`).

Crea, de forma idempotente, las tablas de specs/044-detector-facturas-faltantes/data-model.md:
  FacturasFaltantesPerfil, FacturasFaltantesAlarmas, FacturasFaltantesMarcas.
No toca tablas contables.

Uso (desde backend/):
    python -m scripts.crear_esquema_detector_044 --verificar    # no escribe
    python -m scripts.crear_esquema_detector_044                # respaldo verificado y creación
    python -m scripts.crear_esquema_detector_044 --revertir     # borra las tablas si están vacías
"""

from __future__ import annotations

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

TABLAS = ("FacturasFaltantesMarcas", "FacturasFaltantesAlarmas", "FacturasFaltantesPerfil")

DDL = [
    """
    IF OBJECT_ID('dbo.FacturasFaltantesPerfil', 'U') IS NULL
    CREATE TABLE dbo.FacturasFaltantesPerfil (
        IdContacto int NOT NULL CONSTRAINT PK_FacturasFaltantesPerfil PRIMARY KEY,
        CicloDias int NULL CONSTRAINT CK_FFPerfil_Ciclo CHECK (CicloDias IN (30, 60, 90)),
        SinCiclo bit NOT NULL CONSTRAINT DF_FFPerfil_SinCiclo DEFAULT 0,
        MargenDias int NULL CONSTRAINT CK_FFPerfil_Margen CHECK (MargenDias BETWEEN 0 AND 120),
        DadoDeBaja bit NOT NULL CONSTRAINT DF_FFPerfil_Baja DEFAULT 0,
        PreguntaBajaFecha datetime2(0) NULL,
        Usuario nvarchar(60) NOT NULL,
        FechaModificacion datetime2(0) NOT NULL CONSTRAINT DF_FFPerfil_Fecha DEFAULT SYSDATETIME()
    )
    """,
    """
    IF OBJECT_ID('dbo.FacturasFaltantesAlarmas', 'U') IS NULL
    CREATE TABLE dbo.FacturasFaltantesAlarmas (
        IdDecision int IDENTITY(1,1) NOT NULL CONSTRAINT PK_FacturasFaltantesAlarmas PRIMARY KEY,
        Clave nvarchar(120) NOT NULL CONSTRAINT UQ_FFAlarmas_Clave UNIQUE,
        IdContacto int NOT NULL,
        Decision nvarchar(20) NOT NULL CONSTRAINT CK_FFAlarmas_Decision CHECK (Decision IN ('descartada')),
        Motivo nvarchar(255) NOT NULL CONSTRAINT CK_FFAlarmas_Motivo CHECK (LEN(Motivo) > 0),
        Usuario nvarchar(60) NOT NULL,
        Fecha datetime2(0) NOT NULL CONSTRAINT DF_FFAlarmas_Fecha DEFAULT SYSDATETIME()
    )
    """,
    """
    IF OBJECT_ID('dbo.FacturasFaltantesMarcas', 'U') IS NULL
    CREATE TABLE dbo.FacturasFaltantesMarcas (
        IdMarca int IDENTITY(1,1) NOT NULL CONSTRAINT PK_FacturasFaltantesMarcas PRIMARY KEY,
        IdContacto int NOT NULL,
        OrigenPago nvarchar(30) NOT NULL,
        IdPago int NOT NULL,
        PeriodoDesde date NULL,
        PeriodoHasta date NULL,
        ImporteAprox money NULL,
        Estado nvarchar(10) NOT NULL CONSTRAINT CK_FFMarcas_Estado CHECK (Estado IN ('abierta', 'cerrada', 'anulada')),
        IdDeudaCierre int NULL,
        Motivo nvarchar(255) NULL,
        Usuario nvarchar(60) NOT NULL,
        FechaAlta datetime2(0) NOT NULL CONSTRAINT DF_FFMarcas_Alta DEFAULT SYSDATETIME(),
        FechaCierre datetime2(0) NULL
    )
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_FFMarcas_PagoAbierta')
    CREATE UNIQUE INDEX UX_FFMarcas_PagoAbierta ON dbo.FacturasFaltantesMarcas (OrigenPago, IdPago) WHERE Estado = 'abierta'
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

    print(f"Respaldo verificado: {backup_verificado('esquema-detector-044')}")
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        for sql in DDL:
            cur.execute(sql)
        conn.commit()
        print("Esquema 044 listo.")
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
            if cur.execute("SELECT OBJECT_ID(?, 'U')", f"dbo.{t}").fetchone()[0] and cur.execute(f"SELECT COUNT(*) FROM dbo.{t}").fetchone()[0]:
                raise SystemExit(f"dbo.{t} tiene datos: no se borra.")
        for t in TABLAS:
            cur.execute(f"IF OBJECT_ID('dbo.{t}', 'U') IS NOT NULL DROP TABLE dbo.{t}")
        conn.commit()
        print("Tablas 044 eliminadas.")
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
