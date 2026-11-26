"""26/11/2026 (Sergio: "corregí también la vista de cultivos"): en vw_ResultadosCultivo_CostosBase el renglón
negativo de una factura (descuento, bonificación, remediación) sumaba como costo por ABS(). Ahora resta; ABS queda solo
para las notas de crédito (que después llevan el signo −1). Mismo arreglo que ganaderia/costos.py (Cabaña Las Lilas).
Afecta 16 renglones (el mayor: Gutierrez 00002-00000565, remediación lote 9B −$ 308.280).
Simula por defecto; con --aplicar hace BACKUP verificado y ALTER VIEW en WC.
Uso (desde backend/): python -m scripts.vista_costos_descuentos_20261126 [--aplicar]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ganaderia_tablas_20261125 import _backup  # noqa: E402
from src.db.connection import fetch_all, get_connection  # noqa: E402

VIEJO = "ELSE ABS(ISNULL(DC.Cantidad, 0) * ISNULL(DC.[Precio Unitario], 0)) END"
NUEVO = ("WHEN CP.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Credito' "
         "THEN ABS(ISNULL(DC.Cantidad, 0) * ISNULL(DC.[Precio Unitario], 0)) "
         "/* 26/11/2026: renglón negativo de factura = descuento, resta */ "
         "ELSE ISNULL(DC.Cantidad, 0) * ISNULL(DC.[Precio Unitario], 0) END")
TOTAL = "SELECT COUNT(*) n, SUM(Pesos) p, SUM(Dolares) u FROM dbo.vw_ResultadosCultivo_CostosBase"


def main(aplicar: bool) -> None:
    d = fetch_all("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_ResultadosCultivo_CostosBase')) d")[0]["d"]
    if NUEVO in d:
        print("Ya aplicado")
        return
    n = d.count(VIEJO)
    if n != 4:
        raise RuntimeError(f"Se esperaban 4 ocurrencias y hay {n}")
    i = d.upper().index("CREATE VIEW")
    nueva = d[:i] + "CREATE OR ALTER VIEW" + d[i + len("CREATE VIEW"):].replace(VIEJO, NUEVO)
    print("Antes:", fetch_all(TOTAL))
    if not aplicar:  # el ALTER VIEW no se puede simular: la conexión hace commit de los DDL
        print("SIMULACIÓN: se cambiarían", n, "expresiones")
        return
    print("Backup:", _backup())
    with get_connection() as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cur.execute(nueva)
        print("Después:", tuple(cur.execute(TOTAL).fetchone()))
        conn.commit()
    print("APLICADO")


if __name__ == "__main__":
    main("--aplicar" in sys.argv)
