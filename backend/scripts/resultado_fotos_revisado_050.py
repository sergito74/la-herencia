"""050 (18/11/2026): marca de revisado en las fotos del costo de campañas cerradas. Un cambio ya explicado y
aceptado (Revisado = 1, con nota) deja de mostrarse en el control de integridad; la foto queda como historia.
Solo WC. Re-corrible. Con --marcar-hasta AAAA-MM-DD "nota" marca como revisados los cambios hasta esa fecha.
"""

from __future__ import annotations

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc


def main() -> None:
    _assert_target_is_wc()
    with pyodbc.connect(CONNECTION_STRING) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cur.execute("IF COL_LENGTH('dbo.ResultadoCultivo_Fotos', 'Revisado') IS NULL "
                    "ALTER TABLE dbo.ResultadoCultivo_Fotos ADD Revisado bit NOT NULL "
                    "CONSTRAINT DF_ResultadoCultivo_Fotos_Revisado DEFAULT 0, NotaRevision nvarchar(400) NULL")
        conn.commit()
        if len(sys.argv) >= 4 and sys.argv[1] == "--marcar-hasta":
            n = cur.execute("UPDATE dbo.ResultadoCultivo_Fotos SET Revisado = 1, NotaRevision = ? "
                            "WHERE Cambios IS NOT NULL AND Revisado = 0 AND Fecha < DATEADD(day, 1, CAST(? AS date))",
                            (sys.argv[3], sys.argv[2])).rowcount
            conn.commit()
            print("revisados", n)
        print("ok")


if __name__ == "__main__":
    main()
