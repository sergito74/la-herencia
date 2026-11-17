"""050 (17/11/2026): tabla de fotos del costo por cultivo/campaña. El control de integridad guarda una foto por
cultivo/campaña cerrada y, si el costo cambia después, una nueva con los documentos que cambiaron: así ningún
resultado de una campaña cerrada cambia sin que el sistema lo muestre. Solo WC. Re-corrible.
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc


def main() -> None:
    _assert_target_is_wc()
    with pyodbc.connect(CONNECTION_STRING) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cur.execute("""
            IF OBJECT_ID('dbo.ResultadoCultivo_Fotos') IS NULL
            CREATE TABLE dbo.ResultadoCultivo_Fotos (
                IdFoto int IDENTITY(1,1) PRIMARY KEY,
                IdCultivo int NOT NULL,
                IdCampania int NOT NULL,
                Fecha datetime2 NOT NULL CONSTRAINT DF_ResultadoCultivo_Fotos_Fecha DEFAULT SYSDATETIME(),
                CostoPesos decimal(18,2) NOT NULL,
                CostoDolares decimal(18,2) NOT NULL,
                PorDocumento nvarchar(max) NOT NULL,
                Cambios nvarchar(max) NULL
            )""")
        cur.execute("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ResultadoCultivo_Fotos_Par') "
                    "CREATE INDEX IX_ResultadoCultivo_Fotos_Par ON dbo.ResultadoCultivo_Fotos (IdCultivo, IdCampania, IdFoto)")
        conn.commit()
        print("ok")


if __name__ == "__main__":
    main()
