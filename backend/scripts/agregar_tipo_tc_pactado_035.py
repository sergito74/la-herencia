"""Agrega el tipo `tc-pactado` a la tabla de reglas `AuditoriaConocidos` de WC (035, 2026-10-07).

El proveedor factura en dólares a un tipo de cambio pactado: los pagos en pesos se pasan a dólares con el tipo de cambio de
sus facturas y no con el dólar BNA. Solo cambia la restricción CHECK de la columna `Tipo`; no toca datos. Idempotente.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.agregar_tipo_tc_pactado_035
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        definicion = cur.execute(
            "SELECT definition FROM sys.check_constraints WHERE name = 'CK_AuditoriaConocidos_Tipo'").fetchone()
        if definicion and "tc-pactado" in definicion[0]:
            print("La restricción ya admite 'tc-pactado'.")
            return
        if definicion:
            cur.execute("ALTER TABLE dbo.AuditoriaConocidos DROP CONSTRAINT CK_AuditoriaConocidos_Tipo")
        cur.execute("ALTER TABLE dbo.AuditoriaConocidos ADD CONSTRAINT CK_AuditoriaConocidos_Tipo "
                    "CHECK (Tipo IN ('concepto-movimiento', 'cuenta', 'tc-pactado'))")
        print("Restricción actualizada: AuditoriaConocidos.Tipo admite 'tc-pactado'.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
