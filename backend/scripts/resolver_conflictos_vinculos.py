"""Resuelve los conflictos de la auditoría de vínculos (21/11/2026): un renglón de factura que la propuesta asigna a su
remito (A) pero que hoy retiene otro remito (B), casi siempre de OTRO proveedor o de años de distancia.

  · A recibe su propuesta (como en aplicar_vinculos_remitos.py).
  · B pierde solo los vínculos a renglones que pasan a A; conserva el resto.
  · Asignaciones manuales verificadas (MANUAL) para B cuando su factura propia es clara.
Una transacción, respaldo en backups/, control de sobre-vínculo y saldos antes = después.
Uso (desde backend/): python -m scripts.resolver_conflictos_vinculos <json> [--aplicar]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import execute_write_transaction, fetch_all  # noqa: E402
from scripts.aplicar_vinculos_remitos import BACKUPS, saldos  # noqa: E402

# IdDetalleRemito → [(IdDetalleCompra, cantidad en unidad de factura)]; reemplazan TODOS los vínculos de ese remito.
MANUAL: dict[int, list[tuple[int, float]]] = {
    149: [(2141369760, 80.0)],  # Trac 50 FL 80 L ↔ Bayá 0020-00202518 (renglón de 141,53 repartido)
    157: [(2141369760, 61.53), (2141369766, 18.47)],  # Trac 50 FL 80 L ↔ mismo renglón (resto) + 18,47
    176: [(2141370089, 10.0)],  # Hulk 200 kg (Criadero Don Pedro) ↔ 0004-00003502 10 bolsas × 20 kg
    17: [(2141368028, 24.0)],  # Nidera AX 7761 516 kg ↔ 7028-00003931 24 bolsas AX 7761
    18: [(2141368027, 24.0)],  # Nidera AX 7784 352,8 kg ↔ 7028-00003931 24 bolsas AX 7784
}


def main():
    prop = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    aplicar = "--aplicar" in sys.argv
    asign: dict[int, list[tuple[int, float]]] = {}
    for c in prop["conflictos"]:
        if c["idDetalleRemito"] not in MANUAL:
            asign[c["idDetalleRemito"]] = [(it["idDetalleCompra"], float(it["cantidadFactura"])) for it in c["items"]]
    asign.update(MANUAL)
    a_lineas = {i for v in asign.values() for i, _ in v}

    hoy = fetch_all("SELECT IdRemitoCompra AS id, IdDetalleRemito AS r, IdDetalleCompra AS c, CantidadRemitida AS q, "
                    "DescripFormuladoRemito AS dr, DescripProductoFactura AS dp FROM dbo.tblRemitoCompra")
    borrar = [v for v in hoy if v["r"] in asign or v["c"] in a_lineas]  # A/MANUAL: todo; B: solo lo que pasa a A
    det = {r["id"]: r for r in fetch_all("SELECT IdDetalleCompra AS id, IdCompra AS idc, Cantidad AS q, [Producto/Servicio] AS t FROM dbo.Det_Compras")}
    rem = {r["id"]: r["n"] for r in fetch_all("SELECT rd.IdDetalleRemito AS id, pb.Producto AS n FROM dbo.Remitos_Detalles rd "
                                              "LEFT JOIN dbo.vw_ProductosBase pb ON pb.IdProducto = rd.IdFormulado")}
    ids_borrar = {v["id"] for v in borrar}
    total = defaultdict(float)
    for v in hoy:
        if v["id"] not in ids_borrar:
            total[v["c"]] += float(v["q"] or 0)
    for lineas in asign.values():
        for i, q in lineas:
            total[i] += q
    sobre = [(i, total[i], float(det[i]["q"] or 0)) for i in a_lineas if total[i] > float(det[i]["q"] or 0) * 1.02 + 1e-6]
    if sobre:
        print("ABORTA, sobre-vínculo:", sobre)
        sys.exit(1)
    b_afectados = sorted({v["r"] for v in borrar if v["r"] not in asign})
    print(f"remitos A/manual: {len(asign)} | B que pierden renglones ajenos: {b_afectados} | borrar {len(borrar)} | insertar {sum(map(len, asign.values()))}")
    if not aplicar:
        print("SIMULACIÓN")
        return
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    (BACKUPS / f"conflictos-vinculos-antes-{marca}.json").write_text(json.dumps(borrar, default=str, ensure_ascii=False), encoding="utf-8")
    stmts = [("DELETE FROM dbo.tblRemitoCompra WHERE IdRemitoCompra = ?", (v["id"],)) for v in borrar]
    for r, lineas in asign.items():
        for i, q in lineas:
            stmts.append(("INSERT INTO dbo.tblRemitoCompra (IdDeuda, IdDetalleRemito, IdDetalleCompra, CantidadRemitida, "
                          "DescripFormuladoRemito, DescripProductoFactura) VALUES (?, ?, ?, ?, ?, ?)",
                          (det[i]["idc"], r, i, round(q, 6), (rem.get(r) or "")[:255], (det[i]["t"] or "")[:255])))
    antes = saldos()
    execute_write_transaction(stmts)
    dif = {k for k in set(antes) | set(saldos()) if antes.get(k) != saldos().get(k)}
    print("escrito; respaldo", BACKUPS / f"conflictos-vinculos-antes-{marca}.json", "| saldos cambiados:", len(dif))


if __name__ == "__main__":
    main()
