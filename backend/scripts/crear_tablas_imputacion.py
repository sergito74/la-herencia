"""Crea las tablas del motor de auto-clasificación (017-imputacion-automatica-costos).

Idempotente: si las tablas ya existen no hace nada. Nunca corre contra
`LaHerencia`. Ver specs/017-imputacion-automatica-costos/data-model.md para
el detalle de cada columna.

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tablas_imputacion
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_PROPUESTAS = """
IF OBJECT_ID('dbo.ImputacionPropuestas', 'U') IS NULL
CREATE TABLE dbo.ImputacionPropuestas (
    IdPropuesta     int              NOT NULL IDENTITY PRIMARY KEY,
    IdCorrida       uniqueidentifier NOT NULL,
    Origen          varchar(10)      NOT NULL,
    IdDetalleCompra int              NOT NULL,
    IdOrdenTrabajo  int              NULL,
    IdLote          int              NULL,
    IdCultivo       int              NULL,
    IdCampania      int              NULL,
    IdCentroCosto   int              NULL,
    EsGanaderia     bit              NULL,
    Importe         money            NOT NULL,
    Estado          varchar(20)      NOT NULL,
    FechaCalculo    datetime2        NOT NULL DEFAULT SYSUTCDATETIME(),
    FechaAprobacion datetime2        NULL
)
"""

DDL_INDICE_PROPUESTAS = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_ImputacionPropuestas_DetalleCompra' AND object_id = OBJECT_ID('dbo.ImputacionPropuestas')
)
CREATE INDEX IX_ImputacionPropuestas_DetalleCompra ON dbo.ImputacionPropuestas (IdDetalleCompra, IdCorrida)
"""

# Cubre el TOP 1 ... ORDER BY FechaCalculo DESC (corrida vigente) que se repite
# en casi todas las queries del informe/motor — sin esto, cae a lookup por fila
# en vez de index-only scan (hallazgo de revisión SQL Server, 2026-09-25).
DDL_INDICE_VIGENTE = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_ImputacionPropuestas_Vigente' AND object_id = OBJECT_ID('dbo.ImputacionPropuestas')
)
CREATE INDEX IX_ImputacionPropuestas_Vigente ON dbo.ImputacionPropuestas (IdDetalleCompra, FechaCalculo DESC)
INCLUDE (IdCorrida, Estado, Importe, IdLote, IdCultivo, IdCampania, IdCentroCosto, EsGanaderia)
"""

# Filtro por proveedor/fecha del informe de documentos (hallazgo de revisión
# SQL Server, 2026-09-25) — sin esto, listar_documentos_con_imputacion hace
# table scan de Compras al filtrar por proveedor.
DDL_INDICE_COMPRAS_CONTACTO_FECHA = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Compras_Contacto_Fecha' AND object_id = OBJECT_ID('dbo.Compras')
)
CREATE INDEX IX_Compras_Contacto_Fecha ON dbo.Compras (IdContacto, Fecha DESC)
"""

DDL_ORDENES_CONTRATISTA_FACTURAS = """
IF OBJECT_ID('dbo.OrdenesContratistaFacturas', 'U') IS NULL
CREATE TABLE dbo.OrdenesContratistaFacturas (
    IdVinculo      int NOT NULL IDENTITY PRIMARY KEY,
    IdOrdenTrabajo int NOT NULL,
    IdCompra       int NOT NULL
)
"""

DDL_REFERENCIAS = """
IF OBJECT_ID('dbo.ImputacionReferencias', 'U') IS NULL
CREATE TABLE dbo.ImputacionReferencias (
    IdProducto         int       NOT NULL,
    EsGanaderia         bit       NOT NULL,
    IdCultivo           int       NULL,
    IdCampania          int       NULL,
    FechaActualizacion  datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_ImputacionReferencias PRIMARY KEY (IdProducto, EsGanaderia)
)
"""


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute(DDL_PROPUESTAS)
        cursor.execute(DDL_INDICE_PROPUESTAS)
        cursor.execute(DDL_INDICE_VIGENTE)
        cursor.execute(DDL_INDICE_COMPRAS_CONTACTO_FECHA)
        cursor.execute(DDL_ORDENES_CONTRATISTA_FACTURAS)
        cursor.execute(DDL_REFERENCIAS)
    finally:
        conn.close()
    print(
        f"OK: ImputacionPropuestas, OrdenesContratistaFacturas e ImputacionReferencias listas en {DATABASE}."
    )


if __name__ == "__main__":
    main()
