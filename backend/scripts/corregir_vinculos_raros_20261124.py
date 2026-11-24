"""Corrige 4 vínculos remito↔factura marcados por el control permanente (aprobado por Sergio 24/11/2026).

  · Heat 1,75 kg (remito 110, Lartirigoyen 27/11/2020): de FC/ND Bayá → FC Lartirigoyen 0149-00008895 "Kg. Heat" 5 (envases 0,35 kg).
  · Versión 80 L (remito 178, Cargill 16/01/2024): de ND Cargill 2021 → FC 5850-00007063, 9 renglones aceite metilado (80 L).
  · Baguette 2.920 kg (remito 125, Yanquelen 18/06/2021): se desvincula de la ND Nidera 0303-0015276 (es de otro remito).
  · LT725TRE +23 (remito 200, Bayá 08/09/2025): se desvincula de FC 0020-00451184 (anulada por NC 0020-00135455; neto 0).
Una transacción, respaldo en backups/, saldos antes = después.
Uso (desde backend/): python -m scripts.corregir_vinculos_raros_20261124 [--tanda2] [--aplicar]
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
TANDA_1 = {  # aplicada 24/11/2026 08:49
    217: [(2141371425, 5.0)],
    409: [(2141375730, 6.188), (2141375674, 15.0), (2141375731, 2.549), (2141375732, 9.263), (2141376935, 15.27),
          (2141376936, 2.73), (2141377061, 26.0), (2141377098, 2.147), (2141376001, 0.853)],
    271: [],
    482: [],
}
# Tanda 2 (Sergio 24/11/2026): renglón entero de la factura (cantidad = Det_Compras.Cantidad, None)
TANDA_2 = {
    117: [(-2093290024, None)],                     # Acetoclor 5 L ↔ Coop. Bolívar 0015-00062603 (0,5; corte inicial)
    39: [(2141365942, None), (2141367321, None)],   # Action Alfa 10 L ↔ FEDEA 1003-00000395 Lambda Green 3+7 (refactura)
    38: [(2141365941, None)],                       # Clearsol 6 ↔ FEDEA 1003-00000395 (la 332 la anuló la NC 296)
    107: [(2141367888, None), (2141368555, None), (2141369814, None), (2141368760, None)],  # Metsulfurón ↔ Triticas 60% 1 kg
    167: [(2141369680, None)],                      # Betito 370 kg 2019 ↔ Garnica 00003-00000041 clasificación 10 bolsas
    271: [(2141374506, None)],                      # Baguette 2.920 kg ↔ Yanquelen 00002-00000023 Semillas Trigo 3.000 kg
    251: [(2141372282, None), (2141372059, None)],  # Dividend 10 L ↔ Sunanco 0003-00000018
    252: [(2141372063, None), (2141372346, None), (2141372347, None), (2141372348, None), (2141372349, None)],  # Power Plus 80 L ↔ Henderson 3911
    273: "ROCIO",                                   # Rocío 51 L ↔ Henderson 00004-00003911, 29 renglones
    482: [(2141381959, None)],                      # LT725TRE +23 ↔ Bayá 0020-00451184 (anulada por NC 0020-00135455; devolución −23)
}
NUEVOS = TANDA_2 if "--tanda2" in sys.argv else TANDA_1


def main():
    aplicar = "--aplicar" in sys.argv
    if NUEVOS.get(273) == "ROCIO":
        NUEVOS[273] = [(f["i"], None) for f in fetch_all(
            "SELECT IdDetalleCompra i FROM dbo.Det_Compras WHERE IdCompra = 2143513222 AND [Producto/Servicio] = 'Lts. Aceite Rocio'")]
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
    for r in NUEVOS:
        NUEVOS[r] = [(i, round(float(det[i]["q"]), 6) if q is None else q) for i, q in NUEVOS[r]]
    for i, q in (x for v in NUEVOS.values() for x in v):
        assert abs(float(det[i]["q"]) - q) < 0.001, (i, det[i]["q"], q)
    for r, items in NUEVOS.items():
        print(f"  {r} {rem.get(r)}: {sum(q for _, q in items):g} en {len(items)} renglones")

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
