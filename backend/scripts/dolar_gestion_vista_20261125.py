"""052 FR-016 (Sergio 25/11/2026): la vista de TC por compra pasa al BNA comprador divisa del día hábil anterior,
igual que granos, caja y precios de mercado. Respaldo de la definición anterior en
backups/vw_TC_BNA_PorCompra-antes-20261125.sql. Uso (desde backend/): python -m scripts.dolar_gestion_vista_20261125 [--aplicar]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import fetch_all, get_connection  # noqa: E402

VISTA = """CREATE OR ALTER VIEW dbo.vw_TC_BNA_PorCompra
AS
SELECT
    CP.IdDeuda,
    (
        SELECT TOP (1) DBNA.Comp_Divisa
        FROM dbo.[Dolar BNA] AS DBNA
        WHERE DBNA.Fecha < CAST(CP.Fecha AS date) AND DBNA.Comp_Divisa > 0
        ORDER BY DBNA.Fecha DESC
    ) AS TC_CompDivisa
FROM dbo.Compras AS CP;"""


def main():
    n = fetch_all("SELECT COUNT(*) n FROM dbo.Compras c CROSS APPLY (SELECT TOP 1 Comp_Divisa a FROM dbo.[Dolar BNA] "
                  "WHERE Fecha <= CAST(c.Fecha AS date) ORDER BY Fecha DESC) x CROSS APPLY (SELECT TOP 1 Comp_Divisa b "
                  "FROM dbo.[Dolar BNA] WHERE Fecha < CAST(c.Fecha AS date) AND Comp_Divisa > 0 ORDER BY Fecha DESC) y "
                  "WHERE x.a <> y.b")[0]["n"]
    print(f"Compras cuyo TC de gestión cambia: {n}")
    if "--aplicar" not in sys.argv:
        print("Simulación (usar --aplicar)")
        return
    with get_connection(readonly=False) as cn:
        cn.cursor().execute(VISTA)
        cn.commit()
    print("Vista actualizada")


if __name__ == "__main__":
    main()
