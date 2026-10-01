"""031 (revisión por proveedor): IdContacto en los ítems del lote y tabla
con la decisión de Sergio por proveedor. --apply toma backup verificado
antes del DDL. Idempotente."""

from __future__ import annotations

import argparse

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

DDL = """
IF COL_LENGTH('dbo.CorreccionVinculosItem', 'IdContacto') IS NULL
    ALTER TABLE dbo.CorreccionVinculosItem ADD IdContacto int NULL;
IF OBJECT_ID('dbo.CorreccionVinculosRevision','U') IS NULL
BEGIN
    CREATE TABLE dbo.CorreccionVinculosRevision (
        IdLote int NOT NULL REFERENCES dbo.CorreccionVinculosLote(IdLote),
        IdContacto int NOT NULL,
        Estado varchar(20) NOT NULL,
        Usuario varchar(100) NOT NULL,
        Fecha datetime2 NOT NULL DEFAULT sysutcdatetime(),
        CONSTRAINT PK_CorreccionVinculosRevision PRIMARY KEY (IdLote, IdContacto),
        CONSTRAINT CK_CorreccionVinculosRevision_Estado CHECK (Estado IN ('aprobado','rechazado'))
    );
END;
"""


def apply() -> None:
    _assert_target_is_wc()
    print(f"BACKUP_VERIFIED={backup_verificado('pre_031_revision')}", flush=True)
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cursor = conn.cursor()
        if cursor.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cursor.execute(DDL)
        conn.commit()
        print("MIGRATION_031_REVISION=OK")
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
        print(DDL)
