"""Índices de soporte para las tablas nuevas de Órdenes de Trabajo, idempotente (WC).

NO EJECUTAR sin backup de `WC` verificado y autorización explícita del usuario
(Constitución, Principio II). Correr después de `crear_tablas_ordenes.py`.
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

SENTENCIAS = [
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_OrdenesTrabajoInsumos_IdOrdenTrabajo') CREATE INDEX IX_OrdenesTrabajoInsumos_IdOrdenTrabajo ON dbo.Ordenes_Trabajo_Insumos (IdOrdenTrabajo)",
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_OrdenesTrabajoDistrib_IdOrdenInsumo') CREATE INDEX IX_OrdenesTrabajoDistrib_IdOrdenInsumo ON dbo.Ordenes_Trabajo_Distrib (IdOrdenInsumo)",
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_OrdenesTrabajoDevoluciones_IdOrdenInsumo') CREATE INDEX IX_OrdenesTrabajoDevoluciones_IdOrdenInsumo ON dbo.Ordenes_Trabajo_Devoluciones (IdOrdenInsumo)",
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_OrdenesTrabajoMaquinaria_IdOrdenTrabajo') CREATE INDEX IX_OrdenesTrabajoMaquinaria_IdOrdenTrabajo ON dbo.Ordenes_Trabajo_Maquinaria (IdOrdenTrabajo)",
    "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_OrdenesTrabajo_Estado') CREATE INDEX IX_OrdenesTrabajo_Estado ON dbo.Ordenes_Trabajo (Estado)",
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
