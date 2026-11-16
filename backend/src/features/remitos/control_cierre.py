"""Pendientes de carga de insumos (050, 16/11/2026): lista de acciones concretas para el usuario, por documento.

  · Remitos sin factura: llegó la mercadería y falta cargar o vincular la factura. Bayá Casal no se lista: factura
    cerca del vencimiento de cada pedido, así que su remito sin factura es lo normal (Sergio 16/11/2026); tampoco la
    semilla propia (proveedor Giamigli), que no tiene factura.
  · Insumos usados sin remito de entrada: una orden usó un producto del que no hay entrada (stock negativo): falta
    el remito o la orden tiene otro producto.
Las diferencias de recuento no se listan: se resuelven con la regla de recuentos (tomar juntos los que se compensan).
Solo lectura.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from src.db.connection import fetch_all
from src.features.remitos.stock_datos import calcular_stock

INICIO = date(2025, 5, 12)  # recuento de apertura de la imputación automática
_SIN_LISTAR = ("BAYA CASAL", "GIAMIGLI")  # Bayá factura al vencimiento; Giamigli = semilla propia, sin factura


def pendientes(desde: date = INICIO) -> dict:
    remitos: dict[int, dict] = {}
    for f in fetch_all(
        """
        SELECT r.IdRemito id, r.Fecha f, r.NroRemito n, co.[Razon Social] prov, p.Producto prod, rd.Cantidad q, rd.[Unidad Medida] u
        FROM dbo.Remitos_Detalles rd JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito
        LEFT JOIN dbo.Remitos_Extra x ON x.IdRemito = r.IdRemito
        LEFT JOIN dbo.Contactos co ON co.IdContacto = COALESCE(r.IdContacto, r.IdProveedor)
        LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = rd.IdFormulado
        WHERE r.Fecha >= ? AND ISNULL(x.Anulado, 0) = 0 AND ISNULL(rd.Cantidad, 0) > 0
          AND NOT EXISTS (SELECT 1 FROM dbo.tblRemitoCompra t WHERE t.IdDetalleRemito = rd.IdDetalleRemito)
        ORDER BY r.Fecha, r.IdRemito
        """,
        (desde,),
    ):
        prov = (f["prov"] or "").upper()
        if any(s in prov.replace("Á", "A") for s in _SIN_LISTAR):
            continue
        r = remitos.setdefault(f["id"], {"idRemito": f["id"], "fecha": f["f"], "remito": (f["n"] or "").strip(),
                                         "proveedor": f["prov"], "productos": []})
        r["productos"].append(f"{f['prod'] or 'Producto sin nombre'} {float(f['q']):g} {(f['u'] or '').strip()}".strip())

    sin_entrada = []
    stock = calcular_stock()
    nombres = {int(f["i"]): f["n"] for f in fetch_all("SELECT CAST(IdProducto AS int) i, Producto n FROM dbo.vw_ProductosBase WHERE IdProducto IS NOT NULL")}
    for pid, s in stock.items():
        ordenes = defaultdict(float)
        for sid, c in s.get("consumos", {}).items():
            meta = s.get("salidaMeta", {}).get(sid, {})
            falta = float(c.get("sin_cobertura") or 0)
            fe = meta.get("fecha")
            if falta > 0.005 and meta.get("idOrdenTrabajo") and fe is not None and str(fe)[:10] >= desde.isoformat():
                ordenes[(meta["idOrdenTrabajo"], meta.get("fecha"))] += falta
        if ordenes:
            sin_entrada.append({
                "idProducto": pid, "producto": nombres.get(pid, f"Producto {pid}"), "unidad": s.get("unidadBase"),
                "ordenes": [{"idOrdenTrabajo": o, "fecha": fe, "cantidad": round(q, 3)} for (o, fe), q in sorted(ordenes.items(), key=lambda x: str(x[0][1]))],
            })
    return {"remitosSinFactura": sorted(remitos.values(), key=lambda r: str(r["fecha"])), "usadosSinRemito": sin_entrada}
