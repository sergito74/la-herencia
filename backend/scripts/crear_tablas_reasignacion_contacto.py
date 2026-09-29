"""Crea el esquema del módulo de reasignación de contacto en movimientos de
cuenta corriente (022-reasignacion-contacto). Idempotente: si las tablas ya
existen no hace nada. Nunca corre contra `LaHerencia`. Ver
specs/022-reasignacion-contacto/data-model.md para el detalle de cada columna.

Ambas tablas son insert-only (nunca UPDATE/DELETE), mismo patrón que
`MovimientosCuentaSocio` (021): la fila vigente es siempre la de mayor
Id* para su clave (Origen, IdOrigen).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tablas_reasignacion_contacto
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_REASIGNACIONES_CONTACTO = """
IF OBJECT_ID('dbo.ReasignacionesContacto', 'U') IS NULL
CREATE TABLE dbo.ReasignacionesContacto (
    IdReasignacion      int NOT NULL IDENTITY PRIMARY KEY,
    Origen               varchar(30) NOT NULL,
    IdOrigen             bigint NOT NULL,
    IdContactoAnterior   int NOT NULL,
    IdContactoNuevo      int NOT NULL,
    Motivo               nvarchar(500) NULL,
    Usuario              nvarchar(100) NOT NULL,
    Fecha                datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_ReasignacionesContacto_ContactoAnterior FOREIGN KEY (IdContactoAnterior) REFERENCES dbo.Contactos (IdContacto),
    CONSTRAINT FK_ReasignacionesContacto_ContactoNuevo FOREIGN KEY (IdContactoNuevo) REFERENCES dbo.Contactos (IdContacto),
    CONSTRAINT CK_ReasignacionesContacto_Distinto CHECK (IdContactoNuevo <> IdContactoAnterior)
)
"""

DDL_INDICE_REASIGNACIONES = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_ReasignacionesContacto_Origen' AND object_id = OBJECT_ID('dbo.ReasignacionesContacto')
)
CREATE INDEX IX_ReasignacionesContacto_Origen ON dbo.ReasignacionesContacto (Origen, IdOrigen, IdReasignacion DESC)
"""

DDL_CANDIDATOS_DESCARTADOS = """
IF OBJECT_ID('dbo.CandidatosDescartados', 'U') IS NULL
CREATE TABLE dbo.CandidatosDescartados (
    IdDescarte           int NOT NULL IDENTITY PRIMARY KEY,
    Origen               varchar(30) NOT NULL,
    IdOrigen             bigint NOT NULL,
    IdContactoSugerido   int NOT NULL,
    Usuario              nvarchar(100) NOT NULL,
    Fecha                datetime2 NOT NULL DEFAULT SYSUTCDATETIME()
)
"""

DDL_INDICE_UNICO_DESCARTADOS = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_CandidatosDescartados' AND object_id = OBJECT_ID('dbo.CandidatosDescartados')
)
CREATE UNIQUE INDEX UX_CandidatosDescartados ON dbo.CandidatosDescartados (Origen, IdOrigen, IdContactoSugerido)
"""


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        for ddl in (
            DDL_REASIGNACIONES_CONTACTO,
            DDL_INDICE_REASIGNACIONES,
            DDL_CANDIDATOS_DESCARTADOS,
            DDL_INDICE_UNICO_DESCARTADOS,
        ):
            cursor.execute(ddl)
        print("OK: esquema de reasignación de contacto listo (creado o ya existente).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
