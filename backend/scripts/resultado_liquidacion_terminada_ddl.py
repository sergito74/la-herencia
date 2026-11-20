"""20/11/2026: marca por cultivo/campaña de 'liquidación terminada' (silo en cero). Hasta entonces lo cosechado
y no liquidado es un estimado; después, la diferencia queda como consumo de la hacienda. Solo WC. Re-corrible."""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc


def main() -> None:
    _assert_target_is_wc()
    with pyodbc.connect(CONNECTION_STRING) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cur.execute("""IF COL_LENGTH('dbo.ResultadoCultivo_Cierre', 'FechaLiquidacionTerminada') IS NULL
            ALTER TABLE dbo.ResultadoCultivo_Cierre ADD FechaLiquidacionTerminada date NULL""")
        conn.commit()
        print("ok")


if __name__ == "__main__":
    main()
