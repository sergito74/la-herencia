"""Crea las tablas del recuento físico de stock con reparto a órdenes de trabajo, en `WC`.

Regla de Sergio (2026-10-15): la diferencia de un recuento no es una pérdida aparte;
se reparte entre las órdenes que usaron el producto desde el recuento anterior (en el
primero, desde la última vez que el stock quedó en cero), proporcional a lo usado.
Cada orden conserva lo cargado y recibe un ajuste vinculado. Si no hubo órdenes en el
período, la diferencia queda como faltante/sobrante sin imputar (Stock_Ajustes).

Idempotente; hace un respaldo verificado antes de crear.

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tablas_recuento
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

TABLAS = [
    """
    IF OBJECT_ID('dbo.Stock_Recuentos', 'U') IS NULL
    CREATE TABLE dbo.Stock_Recuentos (
        IdRecuento      int IDENTITY(1,1) PRIMARY KEY,
        Fecha           date          NOT NULL,
        Motivo          nvarchar(255) NOT NULL,
        FechaCarga      datetime2     NOT NULL DEFAULT SYSDATETIME(),
        Anulado         bit           NOT NULL DEFAULT 0,
        MotivoAnulacion nvarchar(255) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Stock_Recuentos_Detalle', 'U') IS NULL
    CREATE TABLE dbo.Stock_Recuentos_Detalle (
        IdRecuentoDetalle int IDENTITY(1,1) PRIMARY KEY,
        IdRecuento        int           NOT NULL,
        IdProducto        int           NOT NULL,
        Sistema           decimal(18,4) NOT NULL,   -- existencia del sistema a la fecha del recuento, antes del ajuste
        Contado           decimal(18,4) NOT NULL,
        DesdeFecha        date          NULL,       -- inicio del período cuyas órdenes absorben la diferencia
        IdAjusteSinImputar int          NULL,       -- Stock_Ajustes con la parte que no se pudo repartir
        Observaciones     nvarchar(255) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Ordenes_Trabajo_AjustesRecuento', 'U') IS NULL
    CREATE TABLE dbo.Ordenes_Trabajo_AjustesRecuento (
        IdAjusteRecuento  int IDENTITY(1,1) PRIMARY KEY,
        IdRecuentoDetalle int           NOT NULL,
        IdOrdenInsumo     int           NOT NULL,
        Cantidad          decimal(18,4) NOT NULL    -- en unidad base: + consumió más (faltante), − consumió menos (sobrante)
    )
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_OT_AjustesRecuento_Insumo')
    CREATE INDEX IX_OT_AjustesRecuento_Insumo ON dbo.Ordenes_Trabajo_AjustesRecuento (IdOrdenInsumo)
    """,
]


def main() -> None:
    _assert_target_is_wc()
    from src.features.vinculos.backup import backup_verificado

    print(f"Respaldo verificado: {backup_verificado('tablas-recuento')}")
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cur = conn.cursor()
        for sql in TABLAS:
            cur.execute(sql)
    print("Tablas de recuento listas.")


if __name__ == "__main__":
    main()
