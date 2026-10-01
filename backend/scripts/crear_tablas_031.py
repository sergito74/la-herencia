"""031: tablas de lotes de corrección de vínculos. --apply toma un backup
verificado de WC (COPY_ONLY, CHECKSUM + RESTORE VERIFYONLY) antes del DDL.
Sin --apply solo imprime el DDL. Idempotente."""

from __future__ import annotations

import argparse

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

DDL = """
IF OBJECT_ID('dbo.CorreccionVinculosLote','U') IS NULL
BEGIN
    CREATE TABLE dbo.CorreccionVinculosLote (
        IdLote int IDENTITY PRIMARY KEY,
        Estado varchar(20) NOT NULL DEFAULT 'propuesto',
        FechaPropuesta datetime2 NOT NULL DEFAULT sysutcdatetime(),
        FechaAplicado datetime2 NULL,
        FechaRevertido datetime2 NULL,
        Usuario varchar(100) NOT NULL,
        BackupArchivo varchar(400) NULL,
        Resumen nvarchar(max) NULL,
        CONSTRAINT CK_CorreccionVinculosLote_Estado CHECK (Estado IN ('propuesto','aplicado','revertido','descartado'))
    );
END;
IF OBJECT_ID('dbo.CorreccionVinculosItem','U') IS NULL
BEGIN
    CREATE TABLE dbo.CorreccionVinculosItem (
        IdItem int IDENTITY PRIMARY KEY,
        IdLote int NOT NULL REFERENCES dbo.CorreccionVinculosLote(IdLote),
        Grupo varchar(40) NOT NULL,
        Accion varchar(20) NOT NULL,
        IdAplicacion int NULL,
        OrigenMovimiento varchar(20) NULL,
        IdMovimientoOrigen bigint NULL,
        TipoDocumento varchar(20) NULL,
        IdDocumento int NULL,
        Importe money NULL,
        Motivo nvarchar(400) NOT NULL,
        Candidatos nvarchar(max) NULL,
        Incluido bit NOT NULL DEFAULT 1,
        Elegido bit NOT NULL DEFAULT 0,
        IdAplicacionCreada int NULL,
        CONSTRAINT CK_CorreccionVinculosItem_Accion CHECK (Accion IN ('anular','pesificar','reemplazo'))
    );
    CREATE INDEX IX_CorreccionVinculosItem_Lote ON dbo.CorreccionVinculosItem (IdLote, Grupo);
END;
"""
DDL_ORIGEN = """
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name='CK_AplicacionesPago_Origen_Conciliacion')
    ALTER TABLE dbo.AplicacionesPago DROP CONSTRAINT CK_AplicacionesPago_Origen_Conciliacion;
ALTER TABLE dbo.AplicacionesPago WITH CHECK ADD CONSTRAINT CK_AplicacionesPago_Origen_Conciliacion
    CHECK (Origen IN ('automatica-mejor-esfuerzo','automatica-exacta','manual','correccion-031'));
"""


def apply() -> None:
    _assert_target_is_wc()
    ruta = backup_verificado("pre_031")
    print(f"BACKUP_VERIFIED={ruta}", flush=True)
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cursor = conn.cursor()
        if cursor.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cursor.execute(DDL)
        cursor.execute(DDL_ORIGEN)
        conn.commit()
        print("MIGRATION_031=OK")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    if parser.parse_args().apply:
        apply()
    else:
        print(DDL + DDL_ORIGEN)
