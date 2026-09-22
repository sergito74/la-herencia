"""Crea las tablas nuevas del módulo Remitos / stock de insumos (010-remitos) en `WC`.

Idempotente. Nunca corre contra `LaHerencia`. Las tablas heredadas (`Remitos`,
`Remitos_Detalles`, `Remitos_Facturas`, `tblRemitoCompra`) no se alteran de esquema.
Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tablas_remitos
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

TABLAS = [
    """
    IF OBJECT_ID('dbo.Remitos_Extra', 'U') IS NULL
    CREATE TABLE dbo.Remitos_Extra (
        IdRemito          int           NOT NULL PRIMARY KEY,
        IdEstablecimiento int           NULL,
        Observaciones     nvarchar(500) NULL,
        Archivo           nvarchar(400) NULL,
        Anulado           bit           NOT NULL DEFAULT 0,
        MotivoAnulacion   nvarchar(255) NULL,
        RevisarDuplicado  bit           NOT NULL DEFAULT 0
    )
    """,
    """
    IF OBJECT_ID('dbo.Unidades_Medida', 'U') IS NULL
    CREATE TABLE dbo.Unidades_Medida (
        Codigo   nvarchar(10) NOT NULL PRIMARY KEY,
        Nombre   nvarchar(40) NOT NULL,
        Magnitud nvarchar(10) NULL,      -- Volumen | Masa | Unidad (solo unidades base)
        EsBase   bit          NOT NULL,
        Orden    int          NOT NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Producto_Unidad', 'U') IS NULL
    CREATE TABLE dbo.Producto_Unidad (
        IdProducto int          NOT NULL PRIMARY KEY,
        UnidadBase nvarchar(10) NOT NULL,
        Confirmada bit          NOT NULL DEFAULT 0,
        Origen     nvarchar(60) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Producto_Equivalencias', 'U') IS NULL
    CREATE TABLE dbo.Producto_Equivalencias (
        IdProducto   int          NOT NULL,
        Unidad       nvarchar(10) NOT NULL,
        FactorABase  float        NOT NULL,   -- 1 <Unidad> = FactorABase <unidad base del producto>
        PRIMARY KEY (IdProducto, Unidad)
    )
    """,
    """
    IF OBJECT_ID('dbo.Stock_Bajas', 'U') IS NULL
    CREATE TABLE dbo.Stock_Bajas (
        IdBaja          int IDENTITY(1,1) PRIMARY KEY,
        Fecha           date          NOT NULL,
        Motivo          nvarchar(30)  NOT NULL,   -- Deterioro | Vencimiento | UsoInterno | Otro
        Detalle         nvarchar(255) NULL,
        IdRubro         int           NOT NULL,
        IdCentro        int           NOT NULL,
        Anulada         bit           NOT NULL DEFAULT 0,
        MotivoAnulacion nvarchar(255) NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.Stock_Bajas_Detalle', 'U') IS NULL
    CREATE TABLE dbo.Stock_Bajas_Detalle (
        IdBajaDetalle int IDENTITY(1,1) PRIMARY KEY,
        IdBaja        int   NOT NULL,
        IdProducto    int   NOT NULL,
        Cantidad      float NOT NULL              -- en la unidad base del producto
    )
    """,
    """
    IF OBJECT_ID('dbo.Stock_Ajustes', 'U') IS NULL
    CREATE TABLE dbo.Stock_Ajustes (
        IdAjuste        int IDENTITY(1,1) PRIMARY KEY,
        Fecha           date          NOT NULL,
        IdProducto      int           NOT NULL,
        Cantidad        float         NOT NULL,   -- + sobrante / - faltante, en la unidad base
        CostoUnitario   money         NULL,       -- solo sobrantes: costo de la nueva capa
        Motivo          nvarchar(255) NOT NULL,
        Anulado         bit           NOT NULL DEFAULT 0,
        MotivoAnulacion nvarchar(255) NULL
    )
    """,
]

UNIDADES = [
    # codigo, nombre, magnitud, esBase, orden
    ("LTS", "Litros", "Volumen", 1, 1),
    ("KGS", "Kilos", "Masa", 1, 2),
    ("UNI", "Unidades", "Unidad", 1, 3),
    ("BIDON", "Bidón", None, 0, 4),
    ("BOLSA", "Bolsa", None, 0, 5),
    ("PACK", "Pack", None, 0, 6),
    ("TAMBOR", "Tambor", None, 0, 7),
    ("CAJA", "Caja", None, 0, 8),
    ("ENVASE", "Envase", None, 0, 9),
    ("TN", "Tonelada", "Masa", 0, 10),  # 1 TN = 1000 KGS (conversión universal, ver stock_datos._CONVERSIONES_UNIVERSALES)
]


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cur = conn.cursor()
        for ddl in TABLAS:
            cur.execute(ddl)
        for cod, nombre, mag, base, orden in UNIDADES:
            cur.execute(
                "IF NOT EXISTS (SELECT 1 FROM dbo.Unidades_Medida WHERE Codigo = ?) "
                "INSERT INTO dbo.Unidades_Medida (Codigo, Nombre, Magnitud, EsBase, Orden) VALUES (?, ?, ?, ?, ?)",
                (cod, cod, nombre, mag, base, orden),
            )
        conn.commit()
    finally:
        conn.close()
    print(f"OK: tablas de remitos / stock listas en {DATABASE}.")


if __name__ == "__main__":
    main()
