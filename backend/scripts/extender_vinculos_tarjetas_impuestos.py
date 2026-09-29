"""Extiende `dbo.Tarjetas_Resumenes_Lineas_Compras` (1.598 filas reales en
producción) para poder vincular una línea de resumen de tarjeta también a
un pago de Impuestos, no solo a una Compra (025-conciliacion-tarjetas-
impuestos). Cambio aditivo (research.md §1): `IdCompra` pasa de NOT NULL a
NULL, se agrega `IdImpuesto` NULL con FK a `Impuestos`, y una CHECK exige
que exactamente uno de los dos esté cargado. Las 1.598 filas existentes ya
cumplen esa condición (todas tienen `IdCompra`, ninguna tiene `IdImpuesto`).

Backup verificado de `WC` tomado antes de correr este script — ver
specs/025-conciliacion-tarjetas-impuestos/tasks.md T001: backup +
RESTORE VERIFYONLY confirmados el 2026-09-29 (archivo
WC_pre_025_tarjetas_impuestos_20260929_091442.bak en el Backup path de la
instancia SQL Server local — el backup anterior era del 28/9, con
escrituras reales de por medio, así que se tomó uno nuevo).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.extender_vinculos_tarjetas_impuestos
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_COLUMNA_NULLABLE = """
IF EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.Tarjetas_Resumenes_Lineas_Compras')
      AND name = 'IdCompra' AND is_nullable = 0
)
ALTER TABLE dbo.Tarjetas_Resumenes_Lineas_Compras ALTER COLUMN IdCompra int NULL
"""

DDL_COLUMNA_ID_IMPUESTO = """
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.Tarjetas_Resumenes_Lineas_Compras') AND name = 'IdImpuesto'
)
ALTER TABLE dbo.Tarjetas_Resumenes_Lineas_Compras ADD IdImpuesto int NULL
"""

DDL_FK_IMPUESTO = """
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_TarjetasResumenesLineasCompras_Impuesto'
)
ALTER TABLE dbo.Tarjetas_Resumenes_Lineas_Compras
    ADD CONSTRAINT FK_TarjetasResumenesLineasCompras_Impuesto
    FOREIGN KEY (IdImpuesto) REFERENCES dbo.Impuestos (IdImpuesto)
"""

DDL_CHECK_ORIGEN_UNICO = """
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints WHERE name = 'CK_TarjetasResumenesLineasCompras_OrigenUnico'
)
ALTER TABLE dbo.Tarjetas_Resumenes_Lineas_Compras
    ADD CONSTRAINT CK_TarjetasResumenesLineasCompras_OrigenUnico
    CHECK (
        (IdCompra IS NOT NULL AND IdImpuesto IS NULL)
        OR (IdCompra IS NULL AND IdImpuesto IS NOT NULL)
    )
"""


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM dbo.Tarjetas_Resumenes_Lineas_Compras")
        total_antes = cursor.fetchone()[0]
        print(f"Vínculos existentes antes del cambio: {total_antes}")

        for ddl in (DDL_COLUMNA_NULLABLE, DDL_COLUMNA_ID_IMPUESTO, DDL_FK_IMPUESTO, DDL_CHECK_ORIGEN_UNICO):
            cursor.execute(ddl)
        print("OK: esquema extendido (IdCompra nullable, IdImpuesto + FK + CHECK).")

        cursor.execute("SELECT COUNT(*) FROM dbo.Tarjetas_Resumenes_Lineas_Compras")
        total_despues = cursor.fetchone()[0]
        assert total_despues == total_antes, (
            f"El conteo de vínculos cambió ({total_antes} -> {total_despues}) — no debería, es un cambio aditivo."
        )
        print(f"OK: {total_despues} vínculos existentes, sin cambios (T003).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
