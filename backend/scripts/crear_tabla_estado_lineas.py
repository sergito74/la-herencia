"""Crea `dbo.Tarjetas_Resumenes_Lineas_Estado` en `WC` (009-conciliacion-tarjetas).

Idempotente: si la tabla ya existe no hace nada. Nunca corre contra `LaHerencia`.
Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tabla_estado_lineas
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL = """
IF OBJECT_ID('dbo.Tarjetas_Resumenes_Lineas_Estado', 'U') IS NULL
CREATE TABLE dbo.Tarjetas_Resumenes_Lineas_Estado (
    IdLineaConsumo    int           NOT NULL PRIMARY KEY,
    Estado            nvarchar(20)  NOT NULL,  -- 'SinDocumento' | 'DiferenciaAceptada'
    Motivo            nvarchar(40)  NOT NULL,
    Detalle           nvarchar(255) NULL,
    ImporteDiferencia money         NULL
)
"""


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        conn.cursor().execute(DDL)
    finally:
        conn.close()
    print(f"OK: dbo.Tarjetas_Resumenes_Lineas_Estado lista en {DATABASE}.")


if __name__ == "__main__":
    main()
