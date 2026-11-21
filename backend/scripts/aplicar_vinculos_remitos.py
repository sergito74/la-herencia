"""Aplica la propuesta APROBADA de la auditoría de vínculos remito ↔ factura (auditoria_vinculos_remitos.py).

Lee specs/050-tamizado-imputacion-cultivos/auditoria-vinculos-remitos-AAAAMMDD.json (lo que se aprobó es lo que se
escribe) y, en UNA transacción:
  1. respalda en backups/ las filas de tblRemitoCompra y Det_Compras.IdFormulado que va a tocar;
  2. por cada remito NUEVO/CAMBIO borra sus vínculos de hoy e inserta los propuestos (cantidad en unidad de factura,
     como la lee costeo.costo_unitario_renglon);
  3. completa Det_Compras.IdFormulado solo si está vacío o si el código no coincide con el texto del renglón.
Controles: ningún renglón de factura queda vinculado por más de su cantidad; saldos de cuentas antes = después
(los vínculos no los tocan, se verifica igual).

Uso (desde backend/):  python -m scripts.aplicar_vinculos_remitos <json>            (simula, no escribe)
                       python -m scripts.aplicar_vinculos_remitos <json> --aplicar  (escribe)
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import execute_write_transaction, fetch_all  # noqa: E402
import scripts.auditoria_vinculos_remitos as A  # noqa: E402

BACKUPS = Path(__file__).resolve().parents[2] / "backups"


def corregir_producto(p: dict) -> bool:
    """Vacío, o código que no coincide con el texto del renglón (genérico/mal cargado)."""
    if p["IdFormulado hoy"] in (None, 0):
        return True
    hoy = A.norm(p["Producto hoy"] or "")
    return not (A.tokens(hoy) & A.tokens(p["Texto"])) and not A._nombre_en_texto(hoy, p["Texto"])


def saldos() -> dict:
    return {r["c"]: round(float(r["s"] or 0), 2) for r in fetch_all(
        "SELECT IdContacto AS c, SUM(ISNULL(Deuda, 0) - ISNULL(Credito, 0)) AS s FROM dbo.vw_MovimientosCuenta_Base GROUP BY IdContacto")}


def main():
    archivo = Path(sys.argv[1])
    aplicar = "--aplicar" in sys.argv
    prop = json.loads(archivo.read_text(encoding="utf-8"))
    vinculos = prop["vinculos"]
    en_tanda = {it["idDetalleCompra"] for v in vinculos for it in v["items"]}
    productos = [p for p in prop["productos"] if p["IdDetalleCompra"] in en_tanda and corregir_producto(p)]

    ids_r = [v["idDetalleRemito"] for v in vinculos]
    hoy = [v for v in fetch_all("SELECT IdRemitoCompra AS id, IdDeuda, IdDetalleRemito, IdDetalleCompra, CantidadRemitida, "
                                "DescripFormuladoRemito, DescripProductoFactura FROM dbo.tblRemitoCompra")]
    borrar = [v for v in hoy if v["IdDetalleRemito"] in set(ids_r)]
    quedan = defaultdict(float)
    for v in hoy:
        if v["IdDetalleRemito"] not in set(ids_r):
            quedan[v["IdDetalleCompra"]] += float(v["CantidadRemitida"] or 0)

    det = {r["id"]: r for r in fetch_all("SELECT d.IdDetalleCompra AS id, d.IdCompra AS idCompra, d.Cantidad AS cant, "
                                         "d.[Producto/Servicio] AS texto, d.IdFormulado AS prod FROM dbo.Det_Compras d")}
    rem = {r["id"]: r for r in fetch_all("SELECT rd.IdDetalleRemito AS id, rd.IdFormulado AS prod, pb.Producto AS nombre "
                                         "FROM dbo.Remitos_Detalles rd LEFT JOIN dbo.vw_ProductosBase pb ON pb.IdProducto = rd.IdFormulado")}
    # Control: ningún renglón de factura sobre-vinculado
    total = defaultdict(float, quedan)
    for v in vinculos:
        for it in v["items"]:
            total[it["idDetalleCompra"]] += float(it["cantidadFactura"])
    exceso = {c: (q, float(det[c]["cant"] or 0)) for c, q in total.items() if c in det and q > float(det[c]["cant"] or 0) * 1.02 + 1e-6}
    previos = {c: v for c, v in exceso.items() if c not in en_tanda}
    if previos:
        print(f"aviso: {len(previos)} renglones de factura YA sobre-vinculados hoy (fuera de esta tanda, no se tocan):", list(previos.items())[:10])
    sobre = [(c, *v) for c, v in exceso.items() if c in en_tanda]
    if sobre:
        print("ABORTA: renglones de factura sobre-vinculados:", sobre[:10])
        sys.exit(1)

    stmts = []
    for v in borrar:
        stmts.append(("DELETE FROM dbo.tblRemitoCompra WHERE IdRemitoCompra = ?", (v["id"],)))
    for v in vinculos:
        r = rem[v["idDetalleRemito"]]
        for it in v["items"]:
            d = det[it["idDetalleCompra"]]
            stmts.append(("INSERT INTO dbo.tblRemitoCompra (IdDeuda, IdDetalleRemito, IdDetalleCompra, CantidadRemitida, "
                          "DescripFormuladoRemito, DescripProductoFactura) VALUES (0, ?, ?, ?, ?, ?)",
                          (v["idDetalleRemito"], it["idDetalleCompra"], round(float(it["cantidadFactura"]), 6),
                           (r["nombre"] or "")[:255], (d["texto"] or "")[:255])))
    for p in productos:
        stmts.append(("UPDATE dbo.Det_Compras SET IdFormulado = ? WHERE IdDetalleCompra = ?",
                      (p["IdFormulado propuesto"], p["IdDetalleCompra"])))

    print(f"remitos: {len(vinculos)} | vínculos a borrar: {len(borrar)} | a insertar: {sum(len(v['items']) for v in vinculos)} "
          f"| productos a completar/corregir en factura: {len(productos)}")
    if not aplicar:
        print("SIMULACIÓN: no se escribió nada. Agregar --aplicar para escribir.")
        return
    BACKUPS.mkdir(exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    respaldo = {"tblRemitoCompra_borradas": borrar,
                "Det_Compras_IdFormulado_antes": [{"IdDetalleCompra": p["IdDetalleCompra"], "IdFormulado": det[p["IdDetalleCompra"]]["prod"]} for p in productos]}
    (BACKUPS / f"vinculos-remitos-antes-{marca}.json").write_text(json.dumps(respaldo, default=str, ensure_ascii=False), encoding="utf-8")
    antes = saldos()
    execute_write_transaction(stmts)
    despues = saldos()
    dif = {c: (antes.get(c), despues.get(c)) for c in set(antes) | set(despues) if antes.get(c) != despues.get(c)}
    print("escrito. respaldo:", BACKUPS / f"vinculos-remitos-antes-{marca}.json")
    print("saldos de cuentas cambiados:", len(dif), list(dif.items())[:5])


if __name__ == "__main__":
    main()
