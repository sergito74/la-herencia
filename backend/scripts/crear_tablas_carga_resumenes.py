"""Crea `dbo.CargasResumenBancario` y `dbo.CargasResumenBancario_Movimientos` en
`WC` (013-carga-resumenes-excel).

Idempotente: si las tablas ya existen no hace nada. Nunca corre contra `LaHerencia`.
Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tablas_carga_resumenes
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_CARGAS = """
IF OBJECT_ID('dbo.CargasResumenBancario', 'U') IS NULL
CREATE TABLE dbo.CargasResumenBancario (
    IdCarga                  int           NOT NULL IDENTITY PRIMARY KEY,
    Banco                    varchar(20)   NOT NULL,  -- 'BNA' | 'Galicia'
    NombreArchivo             nvarchar(260) NOT NULL,
    FechaHoraCarga            datetime2     NOT NULL DEFAULT SYSUTCDATETIME(),
    CantidadCargados          int           NOT NULL,
    CantidadOmitidosDuplicado int           NOT NULL,
    CantidadOmitidosIncompletos int         NOT NULL
)
"""

# `CantidadInsertados` (nombre original) contiene la subcadena "INSERT", que
# el guard de solo-lectura de connection.py (`_assert_read_only`) rechaza en
# cualquier SELECT que la mencione — cualquier consulta futura contra esta
# tabla quedaría rota. Si la tabla ya existe con el nombre viejo (de una
# corrida anterior de este mismo script, antes de este fix), se renombra.
RENAME_COLUMNA_LEGACY = """
IF COL_LENGTH('dbo.CargasResumenBancario', 'CantidadInsertados') IS NOT NULL
EXEC sp_rename 'dbo.CargasResumenBancario.CantidadInsertados', 'CantidadCargados', 'COLUMN'
"""

DDL_MOVIMIENTOS = """
IF OBJECT_ID('dbo.CargasResumenBancario_Movimientos', 'U') IS NULL
CREATE TABLE dbo.CargasResumenBancario_Movimientos (
    IdCarga      int         NOT NULL REFERENCES dbo.CargasResumenBancario(IdCarga),
    Banco        varchar(20) NOT NULL,
    IdMovimiento int         NOT NULL,
    CONSTRAINT PK_CargasResumenBancario_Movimientos PRIMARY KEY (Banco, IdMovimiento)
)
"""


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute(DDL_CARGAS)
        cursor.execute(RENAME_COLUMNA_LEGACY)
        cursor.execute(DDL_MOVIMIENTOS)
    finally:
        conn.close()
    print(
        "OK: dbo.CargasResumenBancario y dbo.CargasResumenBancario_Movimientos "
        f"listas en {DATABASE}."
    )


if __name__ == "__main__":
    main()
