"""Pendientes de carga de insumos (050, 16/11/2026): lista de acciones concretas para el usuario, por documento.

  · Remitos sin factura: llegó la mercadería y falta cargar o vincular la factura.
  · Insumos usados sin remito de entrada: una orden usó un producto del que no hay entrada (stock negativo): falta
    el remito o la orden tiene otro producto.
Las diferencias de recuento no se listan: se resuelven con la regla de recuentos (tomar juntos los que se compensan).

21/11/2026, integridad histórica (Sergio: «todo insumo que entró al stock tiene que estar vinculado a una factura»):
  · los remitos sin factura se buscan en TODA la historia. Bayá se lista solo si pasaron más de VENTANA_BAYA días
    (factura al vencimiento de cada pedido). Excepciones: semilla propia (Giamigli) y Flumeyt (sin factura, consumido);
  · renglones de factura vinculados por más de su cantidad (la misma mercadería costearía dos veces);
  · vínculos a un documento que no corresponde: factura de otro proveedor, nota de débito/crédito, renglón NoImputa o
    factura anulada por nota de crédito (24/11/2026);
  · consumos de órdenes que salieron sin costo (su remito de entrada no tiene factura).
Solo lectura.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from src.db.connection import fetch_all
from src.features.remitos.stock_datos import calcular_stock

INICIO = date(2025, 5, 12)  # recuento de apertura de la imputación automática
VENTANA_BAYA = 270  # días: Bayá factura al vencimiento de cada pedido
_SEMILLA_PROPIA = "GIAMIGLI"  # proveedor Giamigli = semilla propia, sin factura
_PRODUCTOS_SIN_FACTURA = {40958}  # Flumeyt: única entrada histórica sin factura (Sergio 21/11/2026), ya consumido
# Sin facturar, ya consumidos (Sergio 24/11/2026): Tordon 24K 5 L Lartirigoyen 22/11/2019; Betito 300 kg Yanquelen
# 30/11/2020 (Yanquelen mandó la semilla y no la facturó)
# y Calén INTA 2.058 kg Yanquelen 24/05/2023 (desde San Emilio, nunca facturada)
_RENGLONES_SIN_FACTURA = {163, 239, 371}
# (IdRemito, IdCompra) de otro proveedor verificados como correctos: Emerge 75 L comprado a Tierras de Henderson y
# entregado con remito de Sunanco (Sergio 24/11/2026)
# Sergio 24/11/2026: Syngenta (Dividend vía Sunanco, Power Plus vía Henderson), Betito 2019 = semilla propia valorizada
# por la clasificación de Garnica (Heredia), LT725TRE facturado y anulado por NC con devolución en el mismo remito.
_VINCULOS_ACEPTADOS = {(126, 2143513222), (121, 2143513221), (121, 2143513222), (82, 2143512373), (200, 2143517472)}


def _norm(t) -> str:
    return (t or "").upper().replace("Á", "A")


def pendientes() -> dict:
    remitos: dict[int, dict] = {}
    hoy = date.today()
    for f in fetch_all(
        """
        SELECT r.IdRemito id, r.Fecha f, r.NroRemito n, co.[Razon Social] prov, p.Producto prod, rd.Cantidad q, rd.[Unidad Medida] u,
               rd.IdFormulado idp, rd.IdDetalleRemito d
        FROM dbo.Remitos_Detalles rd JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito
        LEFT JOIN dbo.Remitos_Extra x ON x.IdRemito = r.IdRemito
        LEFT JOIN dbo.Contactos co ON co.IdContacto = COALESCE(r.IdContacto, r.IdProveedor)
        LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = rd.IdFormulado
        WHERE r.Fecha IS NOT NULL AND ISNULL(x.Anulado, 0) = 0 AND ISNULL(rd.Cantidad, 0) > 0
          AND NOT EXISTS (SELECT 1 FROM dbo.tblRemitoCompra t WHERE t.IdDetalleRemito = rd.IdDetalleRemito)
          -- entrada devuelta en el mismo remito (renglón negativo del mismo producto): neto 0, no espera factura
          AND (SELECT SUM(ISNULL(rd2.Cantidad, 0)) FROM dbo.Remitos_Detalles rd2
               WHERE rd2.IdRemito = rd.IdRemito AND rd2.IdFormulado = rd.IdFormulado) > 0.000001
        ORDER BY r.Fecha, r.IdRemito
        """
    ):
        prov = _norm(f["prov"])
        if _SEMILLA_PROPIA in prov or int(f["idp"] or 0) in _PRODUCTOS_SIN_FACTURA or f["d"] in _RENGLONES_SIN_FACTURA:
            continue
        if "BAYA CASAL" in prov and (hoy - f["f"].date()).days <= VENTANA_BAYA:
            continue
        r = remitos.setdefault(f["id"], {"idRemito": f["id"], "fecha": f["f"], "remito": (f["n"] or "").strip(),
                                         "proveedor": f["prov"], "productos": []})
        r["productos"].append(f"{f['prod'] or 'Producto sin nombre'} {float(f['q']):g} {(f['u'] or '').strip()}".strip())

    stock = calcular_stock()
    nombres = {int(f["i"]): f["n"] for f in fetch_all("SELECT CAST(IdProducto AS int) i, Producto n FROM dbo.vw_ProductosBase WHERE IdProducto IS NOT NULL")}
    excluidos = {int(x["d"]) for x in fetch_all(
        """SELECT rd.IdDetalleRemito d FROM dbo.Remitos_Detalles rd JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito
           LEFT JOIN dbo.Contactos co ON co.IdContacto = COALESCE(r.IdContacto, r.IdProveedor)
           WHERE UPPER(co.[Razon Social]) LIKE ? OR rd.IdFormulado IN (40958)""", ("%" + _SEMILLA_PROPIA + "%",))} | _RENGLONES_SIN_FACTURA
    sin_entrada, sin_costo = [], []
    for pid, s in stock.items():
        ordenes = defaultdict(float)
        pend = 0.0
        for sid, c in s.get("consumos", {}).items():
            meta = s.get("salidaMeta", {}).get(sid, {})
            falta = float(c.get("sin_cobertura") or 0)
            fe = meta.get("fecha")
            if falta > 0.005 and meta.get("idOrdenTrabajo") and fe is not None and str(fe)[:10] >= INICIO.isoformat():
                ordenes[(meta["idOrdenTrabajo"], meta.get("fecha"))] += falta
            # la parte que salió de una entrada cuyo remito no tiene factura (salvo las excepciones)
            for it in c.get("items", []):
                capa = str(it.get("capa"))
                if it.get("costo_unitario") is None and not (capa.startswith("R") and capa[1:].isdigit() and int(capa[1:]) in excluidos):
                    pend += float(it.get("cantidad") or 0)
        if pend > 0.005 and pid not in _PRODUCTOS_SIN_FACTURA:
            sin_costo.append({"idProducto": pid, "producto": nombres.get(pid, f"Producto {pid}"), "unidad": s.get("unidadBase"),
                              "cantidad": round(pend, 3)})
        if ordenes:
            sin_entrada.append({
                "idProducto": pid, "producto": nombres.get(pid, f"Producto {pid}"), "unidad": s.get("unidadBase"),
                "ordenes": [{"idOrdenTrabajo": o, "fecha": fe, "cantidad": round(q, 3)} for (o, fe), q in sorted(ordenes.items(), key=lambda x: str(x[0][1]))],
            })
    return {"remitosSinFactura": sorted(remitos.values(), key=lambda r: str(r["fecha"])), "usadosSinRemito": sin_entrada,
            "consumosSinCosto": sorted(sin_costo, key=lambda x: x["producto"]),
            "facturasSobreVinculadas": sobre_vinculadas(), "vinculosQueNoCorresponden": vinculos_que_no_corresponden()}


def sobre_vinculadas() -> list[dict]:
    """Renglones de factura vinculados a remitos por más de su cantidad (±2%)."""
    return [
        {"idCompra": f["idc"], "documento": (f["n"] or "").strip(), "fecha": f["f"], "proveedor": f["prov"], "renglon": f["t"],
         "cantidad": round(float(f["q"] or 0), 3), "vinculada": round(float(f["v"] or 0), 3)}
        for f in fetch_all(
            """
            SELECT dc.IdCompra idc, c.[Nro Documento] n, c.Fecha f, co.[Razon Social] prov, dc.[Producto/Servicio] t, dc.Cantidad q, x.v
            FROM (SELECT IdDetalleCompra, SUM(CantidadRemitida) v FROM dbo.tblRemitoCompra GROUP BY IdDetalleCompra) x
            JOIN dbo.Det_Compras dc ON dc.IdDetalleCompra = x.IdDetalleCompra
            JOIN dbo.Compras c ON c.IdDeuda = dc.IdCompra
            LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
            WHERE x.v > ABS(ISNULL(dc.Cantidad, 0)) * 1.02 + 0.000001
            ORDER BY c.Fecha
            """)
    ]


def vinculos_que_no_corresponden() -> list[dict]:
    """Remito vinculado a una factura de otro proveedor, a una nota de débito/crédito o a un renglón que no se imputa."""
    out = []
    for f in fetch_all(
        """
        SELECT DISTINCT r.IdRemito idr, r.NroRemito nr, r.Fecha fr, cr.[Razon Social] provr, p.Producto prod,
               dc.IdCompra idc, c.[Nro Documento] nc, c.[Tipo documento] tipo, cf.[Razon Social] provf,
               CASE WHEN COALESCE(r.IdContacto, r.IdProveedor) <> c.IdContacto THEN 'factura de otro proveedor'
                    WHEN c.[Tipo documento] <> 'Factura' THEN 'nota de débito o crédito'
                    ELSE 'renglón que no se imputa' END motivo
        FROM dbo.tblRemitoCompra t
        JOIN dbo.Remitos_Detalles rd ON rd.IdDetalleRemito = t.IdDetalleRemito
        JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito
        LEFT JOIN dbo.Remitos_Extra x ON x.IdRemito = r.IdRemito
        JOIN dbo.Det_Compras dc ON dc.IdDetalleCompra = t.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = dc.IdCompra
        LEFT JOIN dbo.Contactos cr ON cr.IdContacto = COALESCE(r.IdContacto, r.IdProveedor)
        LEFT JOIN dbo.Contactos cf ON cf.IdContacto = c.IdContacto
        LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = rd.IdFormulado
        WHERE ISNULL(x.Anulado, 0) = 0 AND t.CantidadRemitida > 0
          AND c.[Nro Documento] NOT LIKE 'PENDIENTE%'  -- factura provisoria de Bayá (precio del pedido): NoImputa a propósito
          AND (COALESCE(r.IdContacto, r.IdProveedor) <> c.IdContacto OR c.[Tipo documento] <> 'Factura'
               OR EXISTS (SELECT 1 FROM dbo.TamizRenglones tz WHERE tz.IdDetalleCompra = dc.IdDetalleCompra AND tz.Vigente = 1
                          AND tz.Destino = 'NoImputa'))
        ORDER BY r.Fecha
        """):
        if (f["idr"], f["idc"]) in _VINCULOS_ACEPTADOS:
            continue
        out.append({"idRemito": f["idr"], "remito": (f["nr"] or "").strip(), "fecha": f["fr"], "proveedor": f["provr"],
                    "producto": f["prod"], "idCompra": f["idc"], "documento": (f["nc"] or "").strip(), "tipo": f["tipo"],
                    "proveedorDocumento": f["provf"], "motivo": f["motivo"]})
    vistos = {(o["idRemito"], o["idCompra"]) for o in out}
    for o in facturas_anuladas_por_nc():
        if (o["idRemito"], o["idCompra"]) not in vistos and (o["idRemito"], o["idCompra"]) not in _VINCULOS_ACEPTADOS:
            out.append(o)
    return sorted(out, key=lambda o: str(o["fecha"]))


def facturas_anuladas_por_nc() -> list[dict]:
    """Remito vinculado a una factura cuyo renglón anuló una nota de crédito (24/11/2026, caso Avena Común Lartirigoyen
    2024: la FC 12509 la anuló la NC 1971 y la reemplazó la FC 12612). Mismo proveedor y moneda, NC posterior, mismo
    texto y cantidad, precio igual ±3%. Si hay más copias facturadas del renglón que NC que lo anulen (facturas
    duplicadas de FEDEA), alguna sigue vigente y no se avisa."""
    out = []
    for f in fetch_all(
        """
        SELECT r.IdRemito idr, r.NroRemito nr, r.Fecha fr, cr.[Razon Social] provr, p.Producto prod,
               c.IdDeuda idc, c.[Nro Documento] nc, cf.[Razon Social] provf,
               (SELECT COUNT(DISTINCT c2.IdDeuda) FROM dbo.Det_Compras d2 JOIN dbo.Compras c2 ON c2.IdDeuda = d2.IdCompra
                WHERE c2.IdContacto = c.IdContacto AND c2.[Tipo documento] = 'Factura' AND c2.Moneda = c.Moneda
                  AND ABS(DATEDIFF(day, c2.Fecha, c.Fecha)) <= 120
                  AND (d2.[Producto/Servicio] LIKE dc.[Producto/Servicio] + '%' OR dc.[Producto/Servicio] LIKE d2.[Producto/Servicio] + '%')
                  AND ABS(d2.Cantidad - dc.Cantidad) < 0.001
                  AND ABS(d2.[Precio Unitario] - dc.[Precio Unitario]) <= ABS(dc.[Precio Unitario]) * 0.03) nf,
               (SELECT COUNT(DISTINCT n.IdDeuda) FROM dbo.Det_Compras dn JOIN dbo.Compras n ON n.IdDeuda = dn.IdCompra
                WHERE n.IdContacto = c.IdContacto AND n.[Tipo documento] = 'Nota de Crédito' AND n.Moneda = c.Moneda
                  AND n.Fecha >= c.Fecha
                  AND (dn.[Producto/Servicio] LIKE dc.[Producto/Servicio] + '%' OR dc.[Producto/Servicio] LIKE dn.[Producto/Servicio] + '%')
                  AND ABS(ABS(dn.Cantidad) - ABS(dc.Cantidad)) < 0.001
                  AND ABS(ABS(dn.[Precio Unitario]) - ABS(dc.[Precio Unitario])) <= ABS(dc.[Precio Unitario]) * 0.03
                  AND dn.Cantidad * dn.[Precio Unitario] < 0) nn
        FROM dbo.tblRemitoCompra t
        JOIN dbo.Remitos_Detalles rd ON rd.IdDetalleRemito = t.IdDetalleRemito
        JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito
        LEFT JOIN dbo.Remitos_Extra x ON x.IdRemito = r.IdRemito
        JOIN dbo.Det_Compras dc ON dc.IdDetalleCompra = t.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = dc.IdCompra AND c.[Tipo documento] = 'Factura'
        LEFT JOIN dbo.Contactos cr ON cr.IdContacto = COALESCE(r.IdContacto, r.IdProveedor)
        LEFT JOIN dbo.Contactos cf ON cf.IdContacto = c.IdContacto
        LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = rd.IdFormulado
        WHERE ISNULL(x.Anulado, 0) = 0 AND t.CantidadRemitida > 0 AND ISNULL(dc.Cantidad, 0) > 0
        """):
        if f["nn"] and f["nn"] >= f["nf"]:
            out.append({"idRemito": f["idr"], "remito": (f["nr"] or "").strip(), "fecha": f["fr"], "proveedor": f["provr"],
                        "producto": f["prod"], "idCompra": f["idc"], "documento": (f["nc"] or "").strip(), "tipo": "Factura",
                        "proveedorDocumento": f["provf"], "motivo": "factura anulada por nota de crédito"})
    seen, unicos = set(), []
    for o in out:
        k = (o["idRemito"], o["idCompra"], o["producto"])
        if k not in seen:
            seen.add(k); unicos.append(o)
    return unicos
