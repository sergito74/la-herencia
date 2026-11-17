"""050 (17/11/2026): marca en el plan agrícola los cultivos planificados que no se sembraron.

Sergio: Trigo 2025/26 y Sorgo 2025/26 no se sembraron; en esos lotes se sembró otro cultivo (Soja 1ª, Pastura 2026,
Avena 2026). Lo ya imputado a esos cultivos queda como costo hundido. En el reparto por superficie del plan, un lote
cuenta una sola vez: si tiene un cultivo sembrado, el no sembrado no suma esa superficie.
Solo WC. Re-corrible.
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc


def main() -> None:
    _assert_target_is_wc()
    with pyodbc.connect(CONNECTION_STRING) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        cur.execute("IF COL_LENGTH('dbo.PlanAgricola', 'NoSembrado') IS NULL "
                    "ALTER TABLE dbo.PlanAgricola ADD NoSembrado bit NOT NULL CONSTRAINT DF_PlanAgricola_NoSembrado DEFAULT 0")
        conn.commit()
        cur.execute(
            "UPDATE p SET NoSembrado = 1 FROM dbo.PlanAgricola p "
            "JOIN dbo.[Campañas] ca ON ca.[IdCampaña] = p.[IdCampaña] JOIN dbo.Cultivos cu ON cu.IdCultivo = p.IdCultivo "
            "WHERE ca.[Campaña] = '2025/2026' AND cu.Cultivo IN ('Trigo', 'Sorgo')"
        )
        conn.commit()
        print("No sembrados:", cur.execute("SELECT COUNT(*) FROM dbo.PlanAgricola WHERE NoSembrado = 1").fetchone()[0])


if __name__ == "__main__":
    main()
