"""Migra `Ordenes_Trabajo_Contratista_Factura` a `OrdenesContratistaFacturas`
(017-imputacion-automatica-costos).

La tabla vieja es 1 a 1 (una Orden, una factura); la nueva generaliza a N a N
(specs/017-imputacion-automatica-costos/research.md). Copia idempotente:
si una fila (IdOrdenTrabajo, IdCompra) ya existe en la tabla nueva, no la
duplica. No borra ni modifica la tabla vieja — queda de referencia histórica.

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.migrar_vinculo_contratista
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

COPIAR = """
INSERT INTO dbo.OrdenesContratistaFacturas (IdOrdenTrabajo, IdCompra)
SELECT viejo.IdOrdenTrabajo, viejo.IdCompra
FROM dbo.Ordenes_Trabajo_Contratista_Factura viejo
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.OrdenesContratistaFacturas nuevo
    WHERE nuevo.IdOrdenTrabajo = viejo.IdOrdenTrabajo AND nuevo.IdCompra = viejo.IdCompra
)
"""


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute(COPIAR)
        copiadas = cursor.rowcount
        cursor.execute("SELECT COUNT(*) FROM dbo.Ordenes_Trabajo_Contratista_Factura")
        total_viejo = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM dbo.OrdenesContratistaFacturas")
        total_nuevo = cursor.fetchone()[0]
    finally:
        conn.close()
    print(
        f"OK: {copiadas} filas copiadas en {DATABASE}. "
        f"Ordenes_Trabajo_Contratista_Factura={total_viejo}, OrdenesContratistaFacturas={total_nuevo}."
    )
    if total_nuevo < total_viejo:
        print("ADVERTENCIA: la tabla nueva tiene menos filas que la vieja — revisar antes de continuar.")


if __name__ == "__main__":
    main()
