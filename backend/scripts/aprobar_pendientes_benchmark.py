"""Aprueba en bloque, SIN revisión, todas las propuestas `Pendiente` del motor
de imputación (017-imputacion-automatica-costos).

**Herramienta puntual de benchmark, no parte del flujo normal del sistema.**
El flujo real (spec 017, FR-006) exige que el usuario revise y apruebe cada
propuesta antes de que cuente — este script existe solo para poder comparar
en bloque el criterio del motor contra la clasificación manual histórica
(pedido explícito del usuario, 2026-09-24), sin tener que aprobar a mano
miles de fracciones. Nunca toca `Det_Compras` (la clasificación manual
declarada al cargar la compra) ni ninguna vista del motor heredado (012):
solo marca `Estado='Aprobada'` en `dbo.ImputacionPropuestas`, la tabla
propia de este motor.

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.aprobar_pendientes_benchmark
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dbo.ImputacionPropuestas WHERE Estado = 'Pendiente'")
        antes = cursor.fetchone()[0]
        cursor.execute(
            "UPDATE dbo.ImputacionPropuestas SET Estado = 'Aprobada', FechaAprobacion = SYSUTCDATETIME() "
            "WHERE Estado = 'Pendiente'"
        )
        aprobadas = cursor.rowcount
    finally:
        conn.close()
    print(f"OK: {aprobadas} fracciones pendientes aprobadas en bloque en {DATABASE} (había {antes}).")


if __name__ == "__main__":
    main()
