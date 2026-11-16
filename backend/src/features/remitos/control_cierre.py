"""Control de cierre por producto desde la activación de la imputación automática (050, 16/11/2026).

Por producto (en su unidad base): facturado, remitido, usado por órdenes (con ajustes de recuento), faltantes y
sobrantes sin imputar, stock del sistema y último recuento. Alertas de lo que no cierra:
  · facturado sin remito (no llegó o quedó en el proveedor);
  · remitido sin factura (falta cargar la factura);
  · stock negativo (se usó algo que no tiene remito de entrada);
  · faltante/sobrante de recuento sin órdenes para repartir (revisar si el recuento siguiente lo compensa).
Solo lectura.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from src.db.connection import fetch_all
from src.features.remitos.stock_datos import calcular_stock, equivalencias, factor_a_base, fecha as _fecha, unidades_base

INICIO = date(2025, 5, 12)  # recuento de apertura de la imputación automática
TOL = 0.01


def _a_base(pid, unidad, q, bases, equiv) -> float:
    u = (unidad or "").strip().upper()
    f, falta = factor_a_base(pid, unidad, bases, equiv)
    if u.startswith("TON") and (falta or f == 1.0):
        return q * 1000
    return q * (f if not falta else 1.0)


def control(desde: date = INICIO) -> dict:
    bases, equiv = unidades_base(), equivalencias()
    prod = defaultdict(lambda: defaultdict(float))
    nombres = {int(f["i"]): f for f in fetch_all(
        "SELECT CAST(IdProducto AS int) i, Producto n, TipoProducto t FROM dbo.vw_ProductosBase WHERE IdProducto IS NOT NULL")}

    # Facturado (renglones de stock aprobados por el tamiz) y cuánto de eso tiene remito.
    for f in fetch_all(
        """
        SELECT d.IdFormulado p, d.Cantidad q, d.Unidad u,
               ISNULL((SELECT SUM(t.CantidadRemitida) FROM dbo.tblRemitoCompra t WHERE t.IdDetalleCompra = d.IdDetalleCompra), 0) v
        FROM dbo.TamizRenglones tz JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        WHERE tz.Vigente = 1 AND tz.Destino = 'CultivoStock' AND tz.Estado = 'Aprobada' AND c.[Tipo documento] = 'Factura'
          AND NULLIF(d.IdFormulado, 0) IS NOT NULL AND ISNULL(d.Unidad, '') NOT IN ('ARS', 'USD') AND ISNULL(d.Cantidad, 0) > 0
        """
    ):
        p = int(f["p"])
        q, v = float(f["q"] or 0), min(float(f["v"] or 0), float(f["q"] or 0))
        prod[p]["facturado"] += _a_base(p, f["u"], q, bases, equiv)
        prod[p]["facturadoSinRemito"] += _a_base(p, f["u"], q - v, bases, equiv)

    # Remitido desde el inicio y lo que no tiene ninguna factura vinculada.
    for f in fetch_all(
        """
        SELECT rd.IdFormulado p, rd.Cantidad q, rd.[Unidad Medida] u,
               CASE WHEN EXISTS (SELECT 1 FROM dbo.tblRemitoCompra t WHERE t.IdDetalleRemito = rd.IdDetalleRemito) THEN 1 ELSE 0 END v
        FROM dbo.Remitos_Detalles rd JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito
        LEFT JOIN dbo.Remitos_Extra x ON x.IdRemito = r.IdRemito
        WHERE r.Fecha >= ? AND ISNULL(x.Anulado, 0) = 0 AND rd.IdFormulado > 0
        """,
        (desde,),
    ):
        p = int(f["p"])
        q = _a_base(p, f["u"], float(f["q"] or 0), bases, equiv)
        prod[p]["remitido"] += q
        if not f["v"] and q > 0:
            prod[p]["remitidoSinFactura"] += q

    # Último recuento vigente por producto.
    ultimo = {}
    for f in fetch_all(
        """
        SELECT d.IdProducto p, r.Fecha f, d.Contado c, d.Sistema s FROM dbo.Stock_Recuentos_Detalle d
        JOIN dbo.Stock_Recuentos r ON r.IdRecuento = d.IdRecuento WHERE r.Anulado = 0 ORDER BY r.Fecha
        """
    ):
        ultimo[int(f["p"])] = f

    stock = calcular_stock()
    filas = []
    for p in set(prod) | {k for k, s in stock.items() if abs(s["existencia"]) > TOL}:
        s = stock.get(p, {})
        d = prod.get(p, {})
        usado = faltante = sobrante = 0.0
        for sid, c in s.get("consumos", {}).items():
            meta = s.get("salidaMeta", {}).get(sid, {})
            fe = _fecha(meta.get("fecha"))
            if fe is None or fe < desde:
                continue
            cant = sum(float(i["cantidad"]) for i in c["items"]) + float(c.get("sin_cobertura") or 0)
            if meta.get("tipo") == "faltante":
                faltante += cant
            elif meta.get("tipo") in ("ordenTrabajo", "orden"):
                usado += cant
        for capa in s.get("capas", []):
            if capa.get("origen") == "sobrante" and _fecha(capa.get("fecha")) and _fecha(capa["fecha"]) >= desde:
                sobrante += float(capa["cantidad"])
        u = ultimo.get(p)
        existencia = float(s.get("existencia") or 0)
        alertas = []
        if d.get("facturadoSinRemito", 0) > TOL:
            alertas.append("Facturado sin remito")
        if d.get("remitidoSinFactura", 0) > TOL:
            alertas.append("Remitido sin factura")
        if faltante > TOL or sobrante > TOL:
            alertas.append("Faltante o sobrante de recuento sin órdenes")
        if existencia < -TOL:
            alertas.append("Stock negativo")
        n = nombres.get(p, {})
        filas.append({
            "idProducto": p, "producto": n.get("n") or f"Producto {p}", "tipo": n.get("t"), "unidad": s.get("unidadBase"),
            "facturado": round(d.get("facturado", 0), 3), "facturadoSinRemito": round(d.get("facturadoSinRemito", 0), 3),
            "remitido": round(d.get("remitido", 0), 3), "remitidoSinFactura": round(d.get("remitidoSinFactura", 0), 3),
            "usado": round(usado, 3), "faltante": round(faltante, 3), "sobrante": round(sobrante, 3),
            "existencia": round(existencia, 3),
            "ultimoRecuento": {"fecha": u["f"], "contado": float(u["c"] or 0), "sistema": float(u["s"] or 0)} if u else None,
            "alertas": alertas,
        })
    filas.sort(key=lambda f: (not f["alertas"], f["producto"]))
    return {"desde": desde, "items": filas, "conAlertas": sum(1 for f in filas if f["alertas"])}
