"""Rutina separada en dos (06/11/2026): agrega `Rutina_Corridas.Alcance` (solo en `WC`), idempotente.

    'documentos' = mails + carpetas de Compras e Impuestos · 'portales' = cuentas de la bóveda · 'todo' = ambas
    (las corridas anteriores quedan como 'todo').

Uso (desde backend/):  python -m scripts.rutina_alcance_048
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

DDL = [
    """
    IF COL_LENGTH('dbo.Rutina_Corridas', 'Alcance') IS NULL
    ALTER TABLE dbo.Rutina_Corridas ADD Alcance nvarchar(12) NOT NULL
        CONSTRAINT DF_Rutina_Corridas_Alcance DEFAULT 'todo'
        CONSTRAINT CK_Rutina_Corridas_Alcance CHECK (Alcance IN ('todo', 'documentos', 'portales'))
    """,
]


def main() -> None:
    _assert_target_is_wc()
    with pyodbc.connect(CONNECTION_STRING) as conn:
        cur = conn.cursor()
        for s in DDL:
            cur.execute(s)
        conn.commit()
        print("Columna", "lista" if cur.execute("SELECT COL_LENGTH('dbo.Rutina_Corridas', 'Alcance')").fetchone()[0]
              else "NO creada")


if __name__ == "__main__":
    main()
