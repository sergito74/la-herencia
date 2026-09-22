"""Índices e integridad para las tablas de remitos/stock, idempotente (WC).

Hallazgo de la revisión SQL: `Remitos_Detalles` y `tblRemitoCompra` no tenían PK
ni índice único, lo que permitía duplicar un vínculo renglón↔factura si dos
pedidos llegaban a la vez. No se toca el esquema de columnas heredado de Access.
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

SENTENCIAS = [
    # PK sobre las identity que no la tenían (no cambia columnas ni datos).
    """
    IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = 'PK_Remitos_Detalles')
        ALTER TABLE dbo.Remitos_Detalles ADD CONSTRAINT PK_Remitos_Detalles PRIMARY KEY (IdDetalleRemito)
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = 'PK_tblRemitoCompra')
        ALTER TABLE dbo.tblRemitoCompra ADD CONSTRAINT PK_tblRemitoCompra PRIMARY KEY (IdRemitoCompra)
    """,
    # Único: un mismo renglón de remito no puede vincularse dos veces al mismo
    # renglón de factura (cierra la carrera de `vincular_renglones`).
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_tblRemitoCompra_Renglon_Compra')
        CREATE UNIQUE INDEX UX_tblRemitoCompra_Renglon_Compra ON dbo.tblRemitoCompra (IdDetalleRemito, IdDetalleCompra)
    """,
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Remitos_Detalles_IdRemito') CREATE INDEX IX_Remitos_Detalles_IdRemito ON dbo.Remitos_Detalles (IdRemito)",
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Remitos_Detalles_IdFormulado') CREATE INDEX IX_Remitos_Detalles_IdFormulado ON dbo.Remitos_Detalles (IdFormulado)",
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_tblRemitoCompra_IdDetalleRemito') CREATE INDEX IX_tblRemitoCompra_IdDetalleRemito ON dbo.tblRemitoCompra (IdDetalleRemito)",
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_tblRemitoCompra_IdDetalleCompra') CREATE INDEX IX_tblRemitoCompra_IdDetalleCompra ON dbo.tblRemitoCompra (IdDetalleCompra)",
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Remitos_Proveedor_Nro') CREATE INDEX IX_Remitos_Proveedor_Nro ON dbo.Remitos (IdProveedor, NroRemito)",
]


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cur = conn.cursor()
        for s in SENTENCIAS:
            cur.execute(s)
        conn.commit()
        print(f"OK: {len(SENTENCIAS)} sentencias aplicadas (o ya existentes).")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
