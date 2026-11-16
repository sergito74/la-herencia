"""Propuestas de vínculo remito ↔ factura para revisar en pantalla (050, 16/11/2026).

Usa la misma regla de emparejamiento que la simulación (scripts/simulacion_vinculo_orden_050.py, validada por la
revisión forense): mismo proveedor, mismo producto o principio activo/familia, misma cantidad (±1%), remito
completo o renglón por renglón, hasta 270 días entre remito y factura; préstamos y refacturas como excepciones.

NO vincula nada: deja cada propuesta en dbo.VinculoRemitoPendiente con Tipo = 'propuesta050' (sin resolver).
La pantalla Remitos → Vínculos propuestos las muestra y graba en tblRemitoCompra solo las que Sergio aprueba.
Re-ejecutable: borra las propuestas 050 todavía no resueltas y las vuelve a calcular.

Uso (desde backend/):  python -m scripts.vinculo_propuesta_050
"""

from __future__ import annotations

import json

from src.db.connection import execute_write_transaction, fetch_all
from scripts import simulacion_vinculo_orden_050 as sim

TIPO = "propuesta050"


def calcular() -> list[dict]:
    r = sim.main(guardar=False)
    facturas = r["facturas"]
    ya = {f["i"] for f in fetch_all("SELECT DISTINCT IdDetalleCompra i FROM dbo.tblRemitoCompra")}
    out = []
    for k, x in facturas.items():
        if x.get("apertura") or not x.get("renglones"):
            continue
        v = sim.VINCULOS.get(k)
        for idd, q_base, q_orig in x["renglones"]:
            if idd in ya or q_orig <= 0:
                continue
            base = {"factura": x["nro"], "fechaFactura": x["fecha"].isoformat(), "proveedor": x["prov"], "producto": x["txt"],
                    "cantidadFactura": q_orig}
            if v is None:
                out.append({"idDetalleRemito": None, "idDetalleCompra": idd,
                            "datos": {**base, "regla": None}, "motivo": "Sin remito que coincida"})
                continue
            rem = v["remito"]
            out.append({"idDetalleRemito": rem["lineas"][v["linea"]][2], "idDetalleCompra": idd,
                        "datos": {**base, "regla": v["regla"], "remito": rem["nro"], "fechaRemito": rem["fecha"].isoformat(),
                                  "cantidadVincular": q_orig},
                        "motivo": f"Propuesto ({v['regla']})"})
    return out


def main() -> None:
    props = calcular()
    stmts = [("DELETE FROM dbo.VinculoRemitoPendiente WHERE Tipo = ? AND Resuelto = 0", (TIPO,))]
    for p in props:
        stmts.append(("INSERT INTO dbo.VinculoRemitoPendiente (IdDetalleRemito, IdDetalleCompra, Tipo, CandidatosJson, Motivo) VALUES (?, ?, ?, ?, ?)",
                      (p["idDetalleRemito"], p["idDetalleCompra"], TIPO, json.dumps(p["datos"], ensure_ascii=False), p["motivo"])))
    execute_write_transaction(stmts)
    con = sum(1 for p in props if p["idDetalleRemito"])
    print("propuestas", len(props), "con remito", con, "sin remito", len(props) - con)


if __name__ == "__main__":
    main()
