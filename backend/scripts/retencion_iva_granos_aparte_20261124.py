"""Retención de IVA de granos APARTE de la venta (Sergio 24/11/2026): la venta queda igual a la LPG y cada certificado
RETIVA es un movimiento propio.

  · vw_CnsRetencionesIVAGranos: además de la fila del crédito con ARCA (AFIP, ya existía), una fila por certificado en la
    cuenta del AGENTE que retuvo (Cargill): «Retención IVA granos», Crédito = −importe retenido (lo que no pagó).
  · [Venta Granos].[Retencion IVA] = 0 en las ventas cuyo COE tiene certificados del agente (convención 036 del 20/10,
    que la descontaba dentro de la venta).
  · Se borran los 4 «Pagos efectivo» forma 27 (Retención IVA) de 05-06/2020 que ya representaban 4 certificados
    (1079-00019236/293/294/435): los reemplaza el movimiento del certificado.
Control: el único cambio de saldo es el de Cargill por la venta 1237 (−259.344,58: su retención se había puesto en 0
sin movimiento). Una transacción, respaldo en backups/.
Uso (desde backend/): python -m scripts.retencion_iva_granos_aparte_20261124 [--aplicar]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import fetch_all, get_connection  # noqa: E402
from scripts.aplicar_vinculos_remitos import BACKUPS, saldos  # noqa: E402

VISTA = """CREATE OR ALTER VIEW dbo.vw_CnsRetencionesIVAGranos
AS
-- Crédito con ARCA por la retención (se cancela con la devolución que acredita AFIP).
SELECT
    vg.Fecha,
    CAST(119 AS int) AS IdContacto,
    CAST('AFIP' AS varchar(100)) AS [Razon Social],
    CAST('Certificado Retencion' AS varchar(50)) AS Documento,
    rig.[Nro Certificado] AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(rig.[Importe devolucion] AS money) AS Credito,
    CAST(rig.IdLiquidacion AS bigint) AS IdOrigen
FROM dbo.[Venta Granos] AS vg
INNER JOIN dbo.[Retenciones IVA Granos] AS rig
    ON vg.IdVenta = rig.IdLiquidacion
UNION ALL
-- 24/11/2026: lo que el agente (Cargill) no pagó de la liquidación por la retención; la venta queda igual a la LPG.
SELECT
    vg.Fecha,
    rig.[Agente Retencion] AS IdContacto,
    ct.[Razon Social],
    CAST('Retención IVA granos' AS varchar(50)) AS Documento,
    rig.[Nro Certificado] AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(-rig.[Importe Retenido] AS money) AS Credito,
    CAST(rig.IdLiquidacion AS bigint) AS IdOrigen
FROM dbo.[Venta Granos] AS vg
INNER JOIN dbo.[Retenciones IVA Granos] AS rig
    ON vg.IdVenta = rig.IdLiquidacion
INNER JOIN dbo.Contactos AS ct
    ON ct.IdContacto = rig.[Agente Retencion]
WHERE rig.[Agente Retencion] IS NOT NULL AND ISNULL(rig.[Importe Retenido], 0) <> 0"""

PAGOS_2020 = (1892, 1893, 1894, 1895)


def main():
    aplicar = "--aplicar" in sys.argv
    coes = {r["n"].split(" ")[0] for r in fetch_all(
        "SELECT DISTINCT v.[Nro Documento] AS n FROM dbo.[Retenciones IVA Granos] r JOIN dbo.[Venta Granos] v "
        "ON v.IdVenta = r.IdLiquidacion WHERE r.[Agente Retencion] IS NOT NULL AND r.[Importe Retenido] > 0")}
    ventas = [v for v in fetch_all("SELECT IdVenta AS i, IdConsignatario AS c, [Nro Documento] AS n, [Retencion IVA] AS r "
                                   "FROM dbo.[Venta Granos] WHERE ISNULL([Retencion IVA], 0) <> 0")
              if (v["n"] or "").split(" ")[0] in coes]
    pagos = fetch_all(f"SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo IN ({','.join(map(str, PAGOS_2020))}) "
                      "AND IdFormaPago = 27 AND IdContacto = 258")
    assert len(pagos) == 4, pagos
    print(f"Ventas a dejar igual a la LPG: {len(ventas)} (Ret. IVA {sum(float(v['r']) for v in ventas):,.2f}); "
          f"pagos efectivo 2020 a reemplazar: {len(pagos)}")
    if not aplicar:
        print("Simulación (usar --aplicar)")
        return
    s0 = saldos()
    resp = BACKUPS / f"retencion-iva-granos-aparte-antes-{datetime.now():%Y%m%d-%H%M%S}.json"
    vista_vieja = fetch_all("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_CnsRetencionesIVAGranos')) AS d")[0]["d"]
    resp.write_text(json.dumps({"ventas": ventas, "pagosEfectivo": pagos, "vista": vista_vieja}, default=str,
                               ensure_ascii=False, indent=1), encoding="utf-8")
    with get_connection(readonly=False) as cn:
        cn.autocommit = False
        cur = cn.cursor()
        try:
            cur.execute(VISTA)
            for v in ventas:
                cur.execute("UPDATE dbo.[Venta Granos] SET [Retencion IVA] = 0 WHERE IdVenta = ?", v["i"])
            cur.execute(f"DELETE FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo IN ({','.join(map(str, PAGOS_2020))}) "
                        "AND IdFormaPago = 27 AND IdContacto = 258")
            cn.commit()
        except Exception:
            cn.rollback()
            raise
    s1 = saldos()
    dif = {c: round((s1.get(c) or 0) - (s0.get(c) or 0), 2) for c in set(s0) | set(s1) if s0.get(c) != s1.get(c)}
    print(f"Aplicado. Respaldo: {resp}. Cambios de saldo: {dif}")


if __name__ == "__main__":
    main()
