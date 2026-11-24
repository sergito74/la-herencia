"""Corrige 4 vínculos remito↔factura marcados por el control permanente (aprobado por Sergio 24/11/2026).

  · Heat 1,75 kg (remito 110, Lartirigoyen 27/11/2020): de FC/ND Bayá → FC Lartirigoyen 0149-00008895 "Kg. Heat" 5 (envases 0,35 kg).
  · Versión 80 L (remito 178, Cargill 16/01/2024): de ND Cargill 2021 → FC 5850-00007063, 9 renglones aceite metilado (80 L).
  · Baguette 2.920 kg (remito 125, Yanquelen 18/06/2021): se desvincula de la ND Nidera 0303-0015276 (es de otro remito).
  · LT725TRE +23 (remito 200, Bayá 08/09/2025): se desvincula de FC 0020-00451184 (anulada por NC 0020-00135455; neto 0).
Una transacción, respaldo en backups/, saldos antes = después.
Uso (desde backend/): python -m scripts.corregir_vinculos_raros_20261124 [--aplicar]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import execute_write_transaction, fetch_all  # noqa: E402
from scripts.aplicar_vinculos_remitos import BACKUPS, saldos  # noqa: E402

# IdDetalleRemito → [(IdDetalleCompra, cantidad en unidad de factura)]; reemplazan TODOS sus vínculos ([] = desvincular)
NUEVOS: dict[int, list[tuple[int, float]]] = {
    217: [(2141371425, 5.0)],
    409: [(2141375730, 6.188), (2141375674, 15.0), (2141375731, 2.549), (2141375732, 9.263), (2141376935, 15.27),
          (2141376936, 2.73), (2141377061, 26.0), (2141377098, 2.147), (2141376001, 0.853)],
    271: [],
    482: [],
}


def main():
    aplicar = "--aplicar" in sys.argv
    ids = list(NUEVOS)
    marcas = ",".join("?" * len(ids))
    antes = fetch_all(f"SELECT * FROM dbo.tblRemitoCompra WHERE IdDetalleRemito IN ({marcas})", ids)
    compras = [i for v in NUEVOS.values() for i, _ in v]
    det = {f["i"]: f for f in fetch_all(
        f"SELECT IdDetalleCompra i, IdCompra idc, [Producto/Servicio] t, Cantidad q FROM dbo.Det_Compras WHERE IdDetalleCompra IN ({','.join('?' * len(compras))})",
        compras)}
    rem = {f["d"]: f["p"] for f in fetch_all(
        f"SELECT rd.IdDetalleRemito d, p.Producto p FROM dbo.Remitos_Detalles rd LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = rd.IdFormulado WHERE rd.IdDetalleRemito IN ({marcas})", ids)}
    ocupados = fetch_all(f"SELECT IdDetalleCompra i, SUM(CantidadRemitida) v FROM dbo.tblRemitoCompra WHERE IdDetalleCompra IN ({','.join('?' * len(compras))}) AND IdDetalleRemito NOT IN ({marcas}) GROUP BY IdDetalleCompra", compras + ids)
    if ocupados:
        sys.exit(f"Renglones ya vinculados a otro remito: {ocupados}")
    for i, q in (x for v in NUEVOS.values() for x in v):
        assert abs(float(det[i]["q"]) - q) < 0.001, (i, det[i]["q"], q)

    stmts = [(f"DELETE FROM dbo.tblRemitoCompra WHERE IdDetalleRemito IN ({marcas})", ids)]
    for r, items in NUEVOS.items():
        for i, q in items:
            stmts.append(("INSERT INTO dbo.tblRemitoCompra (IdDeuda, IdDetalleRemito, IdDetalleCompra, CantidadRemitida, "
                          "DescripFormuladoRemito, DescripProductoFactura) VALUES (?, ?, ?, ?, ?, ?)",
                          (det[i]["idc"], r, i, q, (rem.get(r) or "")[:255], (det[i]["t"] or "")[:255])))
    print(f"Vínculos a borrar: {len(antes)}; a insertar: {len(stmts) - 1}")
    if not aplicar:
        print("Simulación (usar --aplicar para escribir)")
        return
    s0 = saldos()
    BACKUPS.mkdir(exist_ok=True)
    resp = BACKUPS / f"vinculos-raros-antes-{datetime.now():%Y%m%d-%H%M%S}.json"
    resp.write_text(json.dumps(antes, default=str, ensure_ascii=False, indent=1), encoding="utf-8")
    execute_write_transaction(stmts)
    s1 = saldos()
    dif = {c: (s0.get(c), s1.get(c)) for c in set(s0) | set(s1) if s0.get(c) != s1.get(c)}
    print(f"Aplicado. Respaldo: {resp}. Saldos con cambio: {len(dif)} {dif if dif else ''}")


if __name__ == "__main__":
    main()
