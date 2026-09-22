"""Arma el stock FIFO de cada producto desde la base (`WC`).

Entradas: renglones de remitos no anulados (con el costo de las facturas
vinculadas) y sobrantes de ajustes. Salidas: consumos de órdenes de trabajo
(`Ordenes_Detalles`), bajas y faltantes de ajustes. Todo en la unidad base del
producto. Las vistas heredadas no se tocan; el cálculo se rehace siempre desde los
datos, así los costos provisorios se corrigen solos al vincular una factura.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from src.db.connection import fetch_all
from src.features.remitos.costeo import costo_unitario_renglon
from src.features.remitos.stock_fifo import Capa, Salida, asignar_fifo


def _f(v) -> float:
    """`Cantidad` es `real` (float32) en varias tablas heredadas: redondeamos a 4
    decimales para que las comparaciones de cantidad (FIFO, vínculos) no queden
    a merced del error de precisión del tipo original."""
    return round(float(v), 4) if v is not None else 0.0


# Conversiones físicas universales entre presentaciones y unidad base, no ligadas
# a un producto puntual (a diferencia de `Producto_Equivalencias`, que sí lo está,
# por ejemplo un bidón de 20 litros de un producto concreto). Hoy sólo toneladas:
# los fertilizantes a veces llegan en TN y siempre se llevan en KGS.
_CONVERSIONES_UNIVERSALES: dict[tuple[str, str], float] = {("TN", "KGS"): 1000.0}


def fecha(v):
    """Fecha como `date`: el driver devuelve `datetime` para las columnas datetime y
    texto para las `date`, y el orden FIFO necesita compararlas."""
    if v is None:
        return None
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    if isinstance(v, datetime):
        return v.date()
    return v


def _filtro(alias: str, id_producto: int | None) -> tuple[str, tuple]:
    return (f" AND {alias} = ?", (id_producto,)) if id_producto is not None else ("", ())


def unidades_base() -> dict[int, str]:
    return {r["idProducto"]: r["unidad"] for r in fetch_all("SELECT IdProducto AS idProducto, UnidadBase AS unidad FROM dbo.Producto_Unidad")}


def equivalencias() -> dict[tuple[int, str], float]:
    return {
        (r["idProducto"], r["unidad"]): _f(r["factor"])
        for r in fetch_all("SELECT IdProducto AS idProducto, Unidad AS unidad, FactorABase AS factor FROM dbo.Producto_Equivalencias")
    }


def factor_a_base(id_producto: int, unidad: str | None, bases: dict, equiv: dict) -> tuple[float, bool]:
    """Factor para pasar `unidad` a la unidad base del producto y si falta la
    equivalencia (se asume 1 y se avisa)."""
    unidad = (unidad or "").strip().upper()
    base = bases.get(id_producto)
    if base is None or unidad == base or not unidad:
        return 1.0, False
    if (unidad, base) in _CONVERSIONES_UNIVERSALES:
        return _CONVERSIONES_UNIVERSALES[(unidad, base)], False
    if (id_producto, unidad) in equiv:
        return equiv[(id_producto, unidad)], False
    return 1.0, True


def costos_de_renglones(id_producto: int | None = None) -> dict[int, dict]:
    """Costo unitario (por unidad del remito) y estado de vinculación de cada renglón."""
    filtro, params = _filtro("rd.IdFormulado", id_producto)
    filas = fetch_all(
        f"""
        SELECT t.IdDetalleRemito AS idDetalle, t.IdDetalleCompra AS idDetalleCompra,
               t.CantidadRemitida AS cantidadRemitida, dc.Cantidad AS cantidadCompra,
               dc.[Precio Unitario] AS precioUnitario, cm.Moneda AS moneda, cm.[Tipo de Cambio] AS tipoDeCambio,
               SUM(t.CantidadRemitida) OVER (PARTITION BY t.IdDetalleCompra) AS sumaRemitidaLineaCompra
        FROM dbo.tblRemitoCompra t
        JOIN dbo.Remitos_Detalles rd ON rd.IdDetalleRemito = t.IdDetalleRemito
        JOIN dbo.Det_Compras dc ON dc.IdDetalleCompra = t.IdDetalleCompra
        JOIN dbo.Compras cm ON cm.IdDeuda = dc.IdCompra
        WHERE 1 = 1{filtro}
        """,
        params,
    )
    por_renglon: dict[int, list[dict]] = defaultdict(list)
    for f in filas:
        por_renglon[f["idDetalle"]].append(
            {
                "idDetalleCompra": f["idDetalleCompra"],
                "cantidadRemitida": _f(f["cantidadRemitida"]),
                "cantidadCompra": _f(f["cantidadCompra"]),
                "precioUnitario": _f(f["precioUnitario"]),
                "moneda": f["moneda"],
                "tipoDeCambio": _f(f["tipoDeCambio"]) or None,
                "sumaRemitidaLineaCompra": _f(f["sumaRemitidaLineaCompra"]),
            }
        )
    return por_renglon


def calcular_stock(id_producto: int | None = None, excluir_remito: int | None = None) -> dict[int, dict]:
    """Stock FIFO por producto: `{idProducto: {existencia, valor, capas, consumos, ...}}`."""
    bases, equiv = unidades_base(), equivalencias()
    vinculos = costos_de_renglones(id_producto)
    filtro, params = _filtro("rd.IdFormulado", id_producto)
    if excluir_remito is not None:
        filtro += " AND rd.IdRemito <> ?"
        params = (*params, excluir_remito)
    entradas = fetch_all(
        f"""
        SELECT rd.IdDetalleRemito AS idDetalle, rd.IdRemito AS idRemito, r.Fecha AS fecha, r.NroRemito AS nroRemito,
               rd.IdFormulado AS idProducto, rd.Cantidad AS cantidad, rd.[Unidad Medida] AS unidad
        FROM dbo.Remitos_Detalles rd
        JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito
        LEFT JOIN dbo.Remitos_Extra e ON e.IdRemito = r.IdRemito
        WHERE ISNULL(e.Anulado, 0) = 0 AND rd.IdFormulado IS NOT NULL AND r.Fecha IS NOT NULL{filtro}
        ORDER BY r.Fecha, rd.IdDetalleRemito
        """,
        params,
    )
    capas: dict[int, list[Capa]] = defaultdict(list)
    meta: dict[str, dict] = {}
    flags: dict[int, dict] = defaultdict(lambda: {"sinUnidadBase": False, "equivalenciaPendiente": False})
    for e in entradas:
        prod = e["idProducto"]
        factor, falta = factor_a_base(prod, e["unidad"], bases, equiv)
        if prod not in bases:
            flags[prod]["sinUnidadBase"] = True
        if falta:
            flags[prod]["equivalenciaPendiente"] = True
        cantidad = _f(e["cantidad"])
        costo_remito, estado, vinculada = costo_unitario_renglon(vinculos.get(e["idDetalle"], []), cantidad)
        capa_id = f"R{e['idDetalle']}"
        capas[prod].append(
            Capa(
                id=capa_id,
                fecha=fecha(e["fecha"]),
                cantidad=cantidad * factor,
                costo_unitario=(costo_remito / factor) if costo_remito is not None else None,
                orden=e["idDetalle"],
            )
        )
        meta[capa_id] = {"origen": "remito", "idRemito": e["idRemito"], "nroRemito": e["nroRemito"], "idDetalle": e["idDetalle"],
                         "estadoCosto": estado, "cantidadEntrada": cantidad * factor}

    filtro_a, params_a = _filtro("a.IdProducto", id_producto)
    ajustes = fetch_all(
        f"""
        SELECT a.IdAjuste AS id, a.Fecha AS fecha, a.IdProducto AS idProducto, a.Cantidad AS cantidad,
               a.CostoUnitario AS costo, a.Motivo AS motivo
        FROM dbo.Stock_Ajustes a WHERE a.Anulado = 0{filtro_a} ORDER BY a.Fecha, a.IdAjuste
        """,
        params_a,
    )
    salidas: dict[int, list[Salida]] = defaultdict(list)
    salida_meta: dict[str, dict] = {}
    for a in ajustes:
        prod, cant = a["idProducto"], _f(a["cantidad"])
        if cant > 0:
            capa_id = f"A{a['id']}"
            capas[prod].append(Capa(id=capa_id, fecha=fecha(a["fecha"]), cantidad=cant, costo_unitario=_f(a["costo"]) if a["costo"] is not None else None, orden=10**9 + a["id"]))
            meta[capa_id] = {"origen": "sobrante", "idAjuste": a["id"], "motivo": a["motivo"], "estadoCosto": "manual" if a["costo"] is not None else "pendiente", "cantidadEntrada": cant}
        elif cant < 0:
            sid = f"F{a['id']}"
            salidas[prod].append(Salida(id=sid, fecha=fecha(a["fecha"]), cantidad=-cant, tipo="faltante", orden=a["id"]))
            salida_meta[sid] = {"tipo": "faltante", "idAjuste": a["id"], "fecha": fecha(a["fecha"]), "motivo": a["motivo"]}
    # Un sobrante sin costo informado toma el de la capa anterior más cercana.
    for prod, lista in capas.items():
        lista.sort(key=lambda c: (c.fecha, c.orden))
        ultimo = None
        for c in lista:
            if c.costo_unitario is not None:
                ultimo = c.costo_unitario
            elif meta[c.id]["origen"] == "sobrante" and ultimo is not None:
                c.costo_unitario = ultimo
                meta[c.id]["estadoCosto"] = "heredado"

    filtro_o, params_o = _filtro("od.IdFormulado", id_producto)
    for o in fetch_all(
        f"""
        SELECT od.IdDetalleOrden AS id, od.IdOrden AS idOrden, od.IdFormulado AS idProducto, od.[Total Aplicado] AS cantidad,
               COALESCE(o.[Fecha Ejecucion], o.[Fecha Pedido]) AS fecha
        FROM dbo.Ordenes_Detalles od JOIN dbo.Ordenes o ON o.IdOrden = od.IdOrden
        WHERE ISNULL(od.[Total Aplicado], 0) > 0{filtro_o}
        """,
        params_o,
    ):
        if o["fecha"] is None:
            continue
        sid = f"O{o['id']}"
        salidas[o["idProducto"]].append(Salida(id=sid, fecha=fecha(o["fecha"]), cantidad=_f(o["cantidad"]), tipo="orden", orden=o["id"]))
        salida_meta[sid] = {"tipo": "orden", "idOrden": o["idOrden"], "fecha": fecha(o["fecha"])}

    filtro_b, params_b = _filtro("d.IdProducto", id_producto)
    for b in fetch_all(
        f"""
        SELECT d.IdBajaDetalle AS id, b.IdBaja AS idBaja, d.IdProducto AS idProducto, d.Cantidad AS cantidad, b.Fecha AS fecha,
               b.Motivo AS motivo, b.IdRubro AS idRubro, b.IdCentro AS idCentro
        FROM dbo.Stock_Bajas_Detalle d JOIN dbo.Stock_Bajas b ON b.IdBaja = d.IdBaja
        WHERE b.Anulada = 0{filtro_b}
        """,
        params_b,
    ):
        sid = f"B{b['id']}"
        salidas[b["idProducto"]].append(Salida(id=sid, fecha=fecha(b["fecha"]), cantidad=_f(b["cantidad"]), tipo="baja", orden=b["id"]))
        salida_meta[sid] = {"tipo": "baja", "idBaja": b["idBaja"], "idBajaDetalle": b["id"], "fecha": fecha(b["fecha"]), "motivo": b["motivo"],
                            "idRubro": b["idRubro"], "idCentro": b["idCentro"]}

    resultado: dict[int, dict] = {}
    for prod in set(capas) | set(salidas):
        r = asignar_fifo(capas.get(prod, []), salidas.get(prod, []))
        r["capas"] = [
            {"id": c.id, "fecha": c.fecha, "cantidad": c.cantidad, "restante": r["restantes"][c.id], "costoUnitario": c.costo_unitario, **meta[c.id]}
            for c in sorted(capas.get(prod, []), key=lambda c: (c.fecha, c.orden))
        ]
        r["salidaMeta"] = {sid: salida_meta[sid] for sid in r["consumos"]}
        r["flags"] = dict(flags[prod])
        r["unidadBase"] = bases.get(prod)
        resultado[prod] = r
    return resultado
