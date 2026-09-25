"""Esquema del módulo de conciliación histórica de cuentas corrientes
(020-conciliacion-historica-cuentas-corrientes).

Agrega a `AplicacionesPago` (019) las columnas que distinguen una
aplicación generada por el proceso histórico de una manual, y crea
`SaldosReferenciaAccess` (saldo de referencia cargado desde una
exportación puntual del sistema Access, ver data-model.md).

Idempotente (mismo patrón que `crear_tabla_aplicaciones_pago.py`): si las
columnas/tabla ya existen no hace nada. Nunca corre contra `LaHerencia`.

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.migrar_conciliacion_historico_esquema
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_COLUMNAS_ORIGEN = """
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.AplicacionesPago') AND name = 'Origen'
)
ALTER TABLE dbo.AplicacionesPago ADD
    Origen varchar(20) NOT NULL CONSTRAINT DF_AplicacionesPago_Origen DEFAULT 'manual',
    NotaConciliacion nvarchar(255) NULL
"""

DDL_CHECK_ORIGEN = """
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints WHERE name = 'CK_AplicacionesPago_Origen_Conciliacion'
)
ALTER TABLE dbo.AplicacionesPago ADD CONSTRAINT CK_AplicacionesPago_Origen_Conciliacion CHECK (
    Origen IN ('manual', 'automatica-exacta', 'automatica-mejor-esfuerzo')
)
"""

DDL_SALDOS_REFERENCIA = """
IF OBJECT_ID('dbo.SaldosReferenciaAccess', 'U') IS NULL
CREATE TABLE dbo.SaldosReferenciaAccess (
    IdContacto  int            NOT NULL PRIMARY KEY,
    SaldoAccess money          NOT NULL,
    FechaCorte  date           NOT NULL,
    FechaCarga  datetime2      NOT NULL DEFAULT SYSUTCDATETIME()
)
"""

# Corrige el ancho original (bug real, ver tasks.md): 'automatica-mejor-esfuerzo'
# tiene 25 caracteres, no entraba en varchar(20).
DDL_ANCHO_ORIGEN = """
IF EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'AplicacionesPago' AND COLUMN_NAME = 'Origen' AND CHARACTER_MAXIMUM_LENGTH < 30
)
ALTER TABLE dbo.AplicacionesPago ALTER COLUMN Origen varchar(30) NOT NULL
"""

# Log persistente de cada corrida del script de conciliación (dry-run o
# --apply): la pantalla de revisión (US2) lee de acá en vez de reprocesar
# los ~12.700 movimientos en vivo (~10 minutos por la cantidad de consultas
# por movimiento, medido corriendo el script real el 2026-09-25).
DDL_LOG_CONCILIACION = """
IF OBJECT_ID('dbo.ConciliacionHistoricoLog', 'U') IS NULL
CREATE TABLE dbo.ConciliacionHistoricoLog (
    OrigenMovimiento   varchar(20)   NOT NULL,
    IdMovimientoOrigen bigint        NOT NULL,
    IdContacto         int           NULL,
    Clasificacion      varchar(30)   NOT NULL,
    Subcategoria       varchar(40)   NULL,
    Detalle            nvarchar(255) NULL,
    FechaProceso       datetime2     NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_ConciliacionHistoricoLog PRIMARY KEY (OrigenMovimiento, IdMovimientoOrigen)
)
"""

DDL_INDICE_LOG_CONTACTO = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_ConciliacionHistoricoLog_Contacto' AND object_id = OBJECT_ID('dbo.ConciliacionHistoricoLog')
)
CREATE INDEX IX_ConciliacionHistoricoLog_Contacto ON dbo.ConciliacionHistoricoLog (IdContacto)
"""


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        for ddl in (
            DDL_COLUMNAS_ORIGEN,
            DDL_CHECK_ORIGEN,
            DDL_SALDOS_REFERENCIA,
            DDL_ANCHO_ORIGEN,
            DDL_LOG_CONCILIACION,
            DDL_INDICE_LOG_CONTACTO,
        ):
            cursor.execute(ddl)
        print("OK: esquema de conciliación histórica listo (creado o ya existente).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
