"""050 (17/11/2026): tabla con el resultado de la verificación externa semanal (portal de Bayá Casal y ARCA Mis
Comprobantes contra el sistema). Solo WC. Re-corrible."""
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
            IF OBJECT_ID('dbo.VerificacionExterna') IS NULL
            CREATE TABLE dbo.VerificacionExterna (
                IdVerificacion int IDENTITY(1,1) PRIMARY KEY,
                Fecha datetime2 NOT NULL CONSTRAINT DF_VerificacionExterna_Fecha DEFAULT SYSDATETIME(),
                Resultado nvarchar(max) NOT NULL
            )""")
        conn.commit()
        print("ok")


if __name__ == "__main__":
    main()
