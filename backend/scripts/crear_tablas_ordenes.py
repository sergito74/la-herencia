"""Crea las tablas nuevas del módulo Órdenes de Trabajo (011-ordenes-trabajo) en `WC`.

Idempotente. Nunca corre contra `LaHerencia`. Las tablas heredadas (`Ordenes`,
`Ordenes_Detalles`, `Ordenes_Detalles_Distrib`, `Ordenes_Lotes`, `Lotes`,
`Cultivos`, `Campañas`, `Tipo Labores`, `Contactos`) no se alteran de esquema.

NO EJECUTAR sin backup de `WC` verificado y autorización explícita del usuario
(Constitución, Principio II).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tablas_ordenes
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

TABLAS = [
    """
    IF OBJECT_ID('dbo.Ordenes_Trabajo', 'U') IS NULL
    CREATE TABLE dbo.Ordenes_Trabajo (
        IdOrdenTrabajo     int IDENTITY(1,1) PRIMARY KEY,
        FechaPedido        date          NOT NULL,
        FechaEjecucion     date          NULL,
        IdTipoLabor        int           NOT NULL,
        IdContratistaContacto int        NULL,
        Estado             nvarchar(20)  NOT NULL DEFAULT 'Planificada',  -- Planificada | Ejecutada | Anulada
        MotivoAnulacion    nvarchar(255) NULL,
        IdRubro            int           NULL,   -- solo órdenes sin cultivo específico (Historia 5)
        IdCentroCostos     int           NULL,
        Observaciones      nvarchar(500) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Ordenes_Trabajo_Insumos', 'U') IS NULL
    CREATE TABLE dbo.Ordenes_Trabajo_Insumos (
        IdOrdenInsumo    int IDENTITY(1,1) PRIMARY KEY,
        IdOrdenTrabajo   int           NOT NULL,
        IdProducto       int           NOT NULL,
        CantidadTotal    decimal(18,4) NOT NULL,   -- suma de las distribuciones, recalculada al guardar
        Unidad           nvarchar(10)  NOT NULL,
        RevisarMigracion bit           NOT NULL DEFAULT 0   -- renglón heredado donde Total Aplicado no cerraba contra lo distribuido (13 de 820)
    )
    """,
    # Idempotente: agrega la columna si la tabla ya existía sin ella (creada por
    # una versión anterior de este script, antes de sumar RevisarMigracion).
    """
    IF COL_LENGTH('dbo.Ordenes_Trabajo_Insumos', 'RevisarMigracion') IS NULL
        ALTER TABLE dbo.Ordenes_Trabajo_Insumos ADD RevisarMigracion bit NOT NULL DEFAULT 0
    """,
    """
    IF OBJECT_ID('dbo.Ordenes_Trabajo_Distrib', 'U') IS NULL
    CREATE TABLE dbo.Ordenes_Trabajo_Distrib (
        IdDistrib        int IDENTITY(1,1) PRIMARY KEY,
        IdOrdenInsumo    int           NOT NULL,
        IdLote           int           NOT NULL,
        IdCultivo        int           NOT NULL,
        IdCampania       int           NOT NULL,
        DosisHa          decimal(18,4) NOT NULL,
        Superficie       decimal(18,4) NOT NULL,
        CantidadAsignada decimal(18,4) NOT NULL,  -- = DosisHa * Superficie
        Aplicar          bit           NOT NULL DEFAULT 1
    )
    """,
    """
    IF OBJECT_ID('dbo.Ordenes_Trabajo_Devoluciones', 'U') IS NULL
    CREATE TABLE dbo.Ordenes_Trabajo_Devoluciones (
        IdDevolucion   int IDENTITY(1,1) PRIMARY KEY,
        IdOrdenInsumo  int           NOT NULL,
        Fecha          date          NOT NULL,
        Cantidad       decimal(18,4) NOT NULL,
        Observaciones  nvarchar(500) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Ordenes_Trabajo_Maquinaria', 'U') IS NULL
    CREATE TABLE dbo.Ordenes_Trabajo_Maquinaria (
        IdOrdenMaquinaria int IDENTITY(1,1) PRIMARY KEY,
        IdOrdenTrabajo    int           NOT NULL,
        Descripcion       nvarchar(255) NOT NULL,
        CostoPorHectarea  decimal(18,2) NOT NULL,
        TipoCambioBna     decimal(18,4) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Ordenes_Trabajo_Contratista_Factura', 'U') IS NULL
    CREATE TABLE dbo.Ordenes_Trabajo_Contratista_Factura (
        IdOrdenTrabajo int NOT NULL PRIMARY KEY,
        IdCompra       int NOT NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Formularios_Retiro', 'U') IS NULL
    CREATE TABLE dbo.Formularios_Retiro (
        IdFormularioRetiro int IDENTITY(1,1) PRIMARY KEY,
        IdOrdenTrabajo     int      NOT NULL UNIQUE,
        FechaEmision       datetime NOT NULL DEFAULT GETDATE()
    )
    """,
]


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cur = conn.cursor()
        for ddl in TABLAS:
            cur.execute(ddl)
        conn.commit()
    finally:
        conn.close()
    print(f"OK: tablas de órdenes de trabajo listas en {DATABASE}.")


if __name__ == "__main__":
    main()
