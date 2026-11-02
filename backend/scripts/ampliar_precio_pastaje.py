"""039: PrecioPromedio con 6 decimales (el promedio INMAG ya no se redondea desde 11/2026).
Toma un backup verificado de WC antes de cambiar la columna. Re-corrible."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import _assert_target_is_wc, get_connection  # noqa: E402
from src.features.vinculos.backup import backup_verificado  # noqa: E402

COLUMNA = "SELECT NUMERIC_SCALE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='PastajeLiquidaciones' AND COLUMN_NAME='PrecioPromedio'"
PRECIOS = "SELECT IdLiquidacion, CAST(PrecioPromedio AS decimal(18,6)) FROM dbo.PastajeLiquidaciones ORDER BY 1"


def lista(cursor):
    return [tuple(r) for r in cursor.execute(PRECIOS).fetchall()]


_assert_target_is_wc()
with get_connection() as conn:
    cursor = conn.cursor()
    escala = cursor.execute(COLUMNA).fetchone()[0]
    antes = lista(cursor)
if escala == 6:
    print("ya aplicado")
    raise SystemExit
print("backup", backup_verificado("pastaje_precio_promedio"))
with get_connection(readonly=False) as conn:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE dbo.PastajeLiquidaciones ALTER COLUMN PrecioPromedio decimal(18,6) NULL")
    conn.commit()
with get_connection() as conn:
    cursor = conn.cursor()
    print("escala", cursor.execute(COLUMNA).fetchone()[0], "datos iguales:", lista(cursor) == antes)
