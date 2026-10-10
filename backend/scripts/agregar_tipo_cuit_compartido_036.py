"""Agrega el tipo `cuit-compartido` a la tabla de reglas `AuditoriaConocidos` de WC (036, 2026-10-09).

Varios contactos legítimos comparten un CUIT (por ejemplo las estaciones de una misma operadora, cada una con su cuenta): la regla
deja de informarlos como "contacto duplicado". Solo cambia la restricción CHECK de la columna `Tipo`; no toca datos. Idempotente,
con respaldo verificado antes de cambiar.

Uso (desde backend/):  python -m scripts.agregar_tipo_cuit_compartido_036
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
        definicion = cur.execute("SELECT definition FROM sys.check_constraints WHERE name = 'CK_AuditoriaConocidos_Tipo'").fetchone()
        if definicion and "cuit-compartido" in definicion[0]:
            print("La restricción ya admite 'cuit-compartido'.")
            return
        conn.close()
        from src.features.vinculos.backup import backup_verificado
        print(f"Respaldo verificado: {backup_verificado('tipo-cuit-compartido-036')}")
        conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
        cur = conn.cursor()
        if definicion:
            cur.execute("ALTER TABLE dbo.AuditoriaConocidos DROP CONSTRAINT CK_AuditoriaConocidos_Tipo")
        cur.execute("ALTER TABLE dbo.AuditoriaConocidos ADD CONSTRAINT CK_AuditoriaConocidos_Tipo "
                    "CHECK (Tipo IN ('concepto-movimiento', 'cuenta', 'tc-pactado', 'cuit-compartido'))")
        print("Restricción actualizada: AuditoriaConocidos.Tipo admite 'cuit-compartido'.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
