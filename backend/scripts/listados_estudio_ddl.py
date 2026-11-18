"""18/11/2026: huellas de los informes del Estudio (bancos y tarjetas en Dropbox): el sistema regenera solo los que
cambiaron. Solo WC. Re-corrible."""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc


def main() -> None:
    _assert_target_is_wc()
    with pyodbc.connect(CONNECTION_STRING) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cur.execute("""IF OBJECT_ID('dbo.ListadosEstudioHuellas') IS NULL
            CREATE TABLE dbo.ListadosEstudioHuellas (
                Clave varchar(30) NOT NULL PRIMARY KEY,
                Huella nvarchar(400) NOT NULL,
                Fecha datetime2 NOT NULL CONSTRAINT DF_ListadosEstudioHuellas_Fecha DEFAULT SYSDATETIME())""")
        conn.commit()
        print("ok")


if __name__ == "__main__":
    main()
