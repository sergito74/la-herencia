"""Crea la tabla del módulo de aplicación de pagos/cobros (019-aplicacion-pagos-cobros).

Idempotente: si la tabla ya existe no hace nada. Nunca corre contra
`LaHerencia`. Ver specs/019-aplicacion-pagos-cobros/data-model.md para el
detalle de cada columna.

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tabla_aplicaciones_pago
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_APLICACIONES_PAGO = """
IF OBJECT_ID('dbo.AplicacionesPago', 'U') IS NULL
CREATE TABLE dbo.AplicacionesPago (
    IdAplicacion        int              NOT NULL IDENTITY PRIMARY KEY,
    OrigenMovimiento    varchar(20)      NOT NULL,
    IdMovimientoOrigen  bigint           NOT NULL,
    TipoDocumento       varchar(20)      NOT NULL,
    IdDocumentoAplicado int              NOT NULL,
    ImporteAplicado     money            NOT NULL,
    Fecha               datetime2        NOT NULL DEFAULT SYSUTCDATETIME(),
    Usuario             varchar(60)      NOT NULL,
    Anulada             bit              NOT NULL DEFAULT 0,
    MotivoAnulacion     nvarchar(255)    NULL,
    UsuarioAnulacion    varchar(60)      NULL,
    FechaAnulacion      datetime2        NULL,
    CONSTRAINT CK_AplicacionesPago_Origen CHECK (
        OrigenMovimiento IN ('bna', 'galicia', 'efectivo', 'valores-propios', 'valores-recibidos', 'tarjetas')
    ),
    CONSTRAINT CK_AplicacionesPago_TipoDocumento CHECK (
        TipoDocumento IN ('CompraDeuda', 'VentaHacienda', 'VentaGranos')
    ),
    CONSTRAINT CK_AplicacionesPago_Importe CHECK (ImporteAplicado > 0)
)
"""

DDL_INDICE_MOVIMIENTO = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_AplicacionesPago_Movimiento' AND object_id = OBJECT_ID('dbo.AplicacionesPago')
)
CREATE INDEX IX_AplicacionesPago_Movimiento ON dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen)
"""

DDL_INDICE_DOCUMENTO = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_AplicacionesPago_Documento' AND object_id = OBJECT_ID('dbo.AplicacionesPago')
)
CREATE INDEX IX_AplicacionesPago_Documento ON dbo.AplicacionesPago (TipoDocumento, IdDocumentoAplicado)
"""


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        for ddl in (DDL_APLICACIONES_PAGO, DDL_INDICE_MOVIMIENTO, DDL_INDICE_DOCUMENTO):
            cursor.execute(ddl)
        print("OK: dbo.AplicacionesPago lista (creada o ya existente).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
