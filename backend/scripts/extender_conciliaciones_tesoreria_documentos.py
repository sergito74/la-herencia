"""026: esquema documental. --apply crea y verifica backup antes de DDL en WC."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import PureWindowsPath

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

DDL = """
IF COL_LENGTH('dbo.ConciliacionesTesoreria', 'TipoOrigenDocumento') IS NULL
    ALTER TABLE dbo.ConciliacionesTesoreria ADD TipoOrigenDocumento varchar(20) NULL;
IF COL_LENGTH('dbo.ConciliacionesTesoreria', 'IdOrigenDocumento') IS NULL
    ALTER TABLE dbo.ConciliacionesTesoreria ADD IdOrigenDocumento bigint NULL;
IF OBJECT_ID('dbo.ConciliacionesTesoreriaEstado','U') IS NULL
BEGIN
    CREATE TABLE dbo.ConciliacionesTesoreriaEstado (
        IdEstado int IDENTITY PRIMARY KEY,
        Medio varchar(20) NOT NULL,
        IdMovimiento bigint NOT NULL,
        Estado varchar(20) NOT NULL,
        Motivo varchar(30) NOT NULL,
        Detalle nvarchar(255) NULL,
        ImporteDiferencia money NULL,
        Usuario nvarchar(100) NOT NULL,
        Fecha datetime NOT NULL DEFAULT getdate(),
        CONSTRAINT CK_ConciliacionesTesoreriaEstado_Estado
            CHECK (Estado IN ('SinDocumento','DiferenciaAceptada','EstadoQuitado')),
        CONSTRAINT CK_ConciliacionesTesoreriaEstado_Medio CHECK
            (Medio IN ('bna','galicia','mercado-libre','efectivo','valores-propios','valores-recibidos'))
    );
END;
"""
DDL_POST = """
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name='CK_ConciliacionesTesoreria_Importe')
    ALTER TABLE dbo.ConciliacionesTesoreria DROP CONSTRAINT CK_ConciliacionesTesoreria_Importe;
ALTER TABLE dbo.ConciliacionesTesoreria WITH CHECK ADD CONSTRAINT CK_ConciliacionesTesoreria_Importe
    CHECK (Importe > 0 OR (Importe < 0 AND TipoOrigenDocumento IS NOT NULL
        AND TipoOrigenDocumento = 'Compras' AND IdOrigenDocumento IS NOT NULL));
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.ConciliacionesTesoreria') AND name='IX_ConciliacionesTesoreria_Documento')
    CREATE INDEX IX_ConciliacionesTesoreria_Documento ON dbo.ConciliacionesTesoreria (TipoOrigenDocumento,IdOrigenDocumento) INCLUDE (Importe);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.ConciliacionesTesoreriaEstado') AND name='IX_ConciliacionesTesoreriaEstado_Movimiento')
    CREATE INDEX IX_ConciliacionesTesoreriaEstado_Movimiento ON dbo.ConciliacionesTesoreriaEstado (Medio,IdMovimiento,IdEstado DESC);
"""


def apply() -> None:
    _assert_target_is_wc()
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cursor = conn.cursor()
        if cursor.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        directory = cursor.execute("SELECT SERVERPROPERTY('InstanceDefaultBackupPath')").fetchone()[
            0
        ]
        if not directory:
            raise RuntimeError("No hay directorio de backup de instancia")
        path = str(PureWindowsPath(directory) / f"WC_pre_026_{datetime.now():%Y%m%d_%H%M%S_%f}.bak")
        cursor.execute("BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM", (path,))
        while cursor.nextset():
            pass
        cursor.execute("RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM", (path,))
        while cursor.nextset():
            pass
        print(f"BACKUP_VERIFIED={path}", flush=True)
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cursor = conn.cursor()
        cursor.execute(DDL)
        cursor.execute(DDL_POST)
        conn.commit()
        print("MIGRATION_026=OK")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.apply:
        apply()
    else:
        print(DDL + DDL_POST)
