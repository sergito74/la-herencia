"""Audita `dbo.ImputacionPropuestas` en busca de filas huérfanas — sin FK
real a `Det_Compras`/`Ordenes_Trabajo` (decisión consciente de spec 010/011,
para no bloquear la migración con constraints estrictas). Si se edita o
borra un renglón de factura/Orden desde el ABM correspondiente, la
propuesta que dependía de él queda huérfana e invisible hasta que alguien
la pise en el informe (hallazgo de revisión SQL Server, 2026-09-25).

Solo lee — no borra ni corrige nada. Correr periódicamente y revisar a
mano lo que reporte.

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.verificar_huerfanos_imputacion
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

CONSULTAS = {
    "IdDetalleCompra sin Det_Compras": """
        SELECT DISTINCT p.IdDetalleCompra
        FROM dbo.ImputacionPropuestas p
        WHERE NOT EXISTS (SELECT 1 FROM dbo.Det_Compras dc WHERE dc.IdDetalleCompra = p.IdDetalleCompra)
    """,
    "IdOrdenTrabajo sin Ordenes_Trabajo": """
        SELECT DISTINCT p.IdOrdenTrabajo
        FROM dbo.ImputacionPropuestas p
        WHERE p.IdOrdenTrabajo IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM dbo.Ordenes_Trabajo ot WHERE ot.IdOrdenTrabajo = p.IdOrdenTrabajo)
    """,
    "OrdenesContratistaFacturas.IdOrdenTrabajo sin Ordenes_Trabajo": """
        SELECT DISTINCT f.IdOrdenTrabajo
        FROM dbo.OrdenesContratistaFacturas f
        WHERE NOT EXISTS (SELECT 1 FROM dbo.Ordenes_Trabajo ot WHERE ot.IdOrdenTrabajo = f.IdOrdenTrabajo)
    """,
    "OrdenesContratistaFacturas.IdCompra sin Compras": """
        SELECT DISTINCT f.IdCompra
        FROM dbo.OrdenesContratistaFacturas f
        WHERE NOT EXISTS (SELECT 1 FROM dbo.Compras c WHERE c.IdDeuda = f.IdCompra)
    """,
}


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        total_huerfanos = 0
        for nombre, sql in CONSULTAS.items():
            cursor.execute(sql)
            filas = [r[0] for r in cursor.fetchall()]
            total_huerfanos += len(filas)
            estado = "OK" if not filas else f"{len(filas)} huérfano(s)"
            print(f"[{estado}] {nombre}" + (f": {filas[:20]}{' ...' if len(filas) > 20 else ''}" if filas else ""))
    finally:
        conn.close()

    print(f"\nTotal de huérfanos encontrados en {DATABASE}: {total_huerfanos}")
    if total_huerfanos:
        print("No se borró ni corrigió nada — revisar a mano antes de decidir qué hacer con cada caso.")


if __name__ == "__main__":
    main()
