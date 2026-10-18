"""Anula la retención 0000-2021-000023 de La Esperanza Agropecuaria (036, 2026-10-18).

En Access (base LaHerencia) la fila está en $0, sin contacto: se anuló y el pago
del 08/09/2021 se rehízo con la transferencia Galicia de $10.733,80 + la
retención 0000-2021-000025 ($353,76). La carga de certificados SICORE del
2026-10-01 la había vuelto a completar con $11.087,56 (ahora está en OMITIDOS).
Agrega la columna dbo.Retenciones.Observaciones (nullable) para la nota "Anulada".
Idempotente; hace respaldo verificado antes de escribir.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.anular_retencion_esperanza_036
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado


def main() -> None:
    _assert_target_is_wc()
    print(f"Respaldo verificado: {backup_verificado('anular-retencion-23')}")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT COL_LENGTH('dbo.Retenciones', 'Observaciones')").fetchone()[0] is None:
            cur.execute("ALTER TABLE dbo.Retenciones ADD Observaciones nvarchar(255) NULL")
        n = cur.execute("UPDATE dbo.Retenciones SET Importe = 0, IdContacto = NULL, Observaciones = N'Anulada' "
                        "WHERE IdRetencionSQL = 27 AND [Numero Certificado] = '0000-2021-000023'").rowcount
        if n != 1:
            raise RuntimeError(f"Se esperaba 1 fila, se actualizaron {n}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Retención 0000-2021-000023 anulada.")


if __name__ == "__main__":
    main()
