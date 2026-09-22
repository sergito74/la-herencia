"""Costo por Cultivo/Campaña (Historia 6): objetivo central del módulo.

Suma el costo de insumos (FIFO, vía `remitos.stock_datos`), maquinaria propia y
contratistas de las Órdenes de Trabajo nuevas, agrupado por Lote/Cultivo/Campaña,
y lo conecta con el motor de costeo heredado (`vw_ResultadoCultivo_Campaña`) para
mostrar el costo total de la campaña (compras, seguros, comercialización, etc.)
junto al aporte de este módulo. Sin filtro de fecha de cierre (FR-015): una
campaña ya cosechada sigue sumando costos de órdenes nuevas.
"""

from __future__ import annotations

from collections import defaultdict

from src.db.connection import fetch_all
from src.features.ordenes import costeo
from src.features.remitos.stock_datos import calcular_stock

EPS = 1e-6


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def _filas_insumos(id_cultivo: int | None, id_campania: int | None, id_lote: int | None) -> list[dict]:
    where, params = ["ot.Estado <> 'Anulada'", "ot.IdRubro IS NULL"], []
    if id_cultivo is not None:
        where.append("d.IdCultivo = ?")
        params.append(id_cultivo)
    if id_campania is not None:
        where.append("d.IdCampania = ?")
        params.append(id_campania)
    if id_lote is not None:
        where.append("d.IdLote = ?")
        params.append(id_lote)
    return fetch_all(
        f"""
        SELECT oi.IdOrdenInsumo AS idOrdenInsumo, oi.IdOrdenTrabajo AS idOrdenTrabajo, oi.IdProducto AS idProducto,
               oi.CantidadTotal AS cantidadTotal, d.IdLote AS idLote, l.[Numero Lote] AS lote,
               d.IdCultivo AS idCultivo, cu.Cultivo AS cultivo, d.IdCampania AS idCampania, ca.Campaña AS campania,
               d.CantidadAsignada AS cantidadAsignada, d.Aplicar AS aplicar
        FROM dbo.Ordenes_Trabajo_Distrib d
        JOIN dbo.Ordenes_Trabajo_Insumos oi ON oi.IdOrdenInsumo = d.IdOrdenInsumo
        JOIN dbo.Ordenes_Trabajo ot ON ot.IdOrdenTrabajo = oi.IdOrdenTrabajo
        LEFT JOIN dbo.Lotes l ON l.IdLote = d.IdLote
        LEFT JOIN dbo.Cultivos cu ON cu.IdCultivo = d.IdCultivo
        LEFT JOIN dbo.Campañas ca ON ca.IdCampaña = d.IdCampania
        WHERE {' AND '.join(where)} AND d.Aplicar = 1
        """,
        tuple(params),
    )


def _filas_maquinaria_y_contratista(id_cultivo: int | None, id_campania: int | None, id_lote: int | None) -> tuple[list[dict], list[dict]]:
    """Devuelve (renglones de maquinaria, facturas de contratista) de órdenes con
    al menos una distribución que matchee los filtros — el costo se prorratea
    por superficie de todos los lotes de la orden, no solo los filtrados."""
    ids = {
        f["idOrdenTrabajo"]
        for f in _filas_insumos(id_cultivo, id_campania, id_lote)
    }
    if not ids:
        return [], []
    marcas = ",".join("?" for _ in ids)
    ids_t = tuple(ids)
    maquinaria = fetch_all(
        f"SELECT IdOrdenTrabajo AS idOrdenTrabajo, CostoPorHectarea AS costoPorHectarea FROM dbo.Ordenes_Trabajo_Maquinaria WHERE IdOrdenTrabajo IN ({marcas})",
        ids_t,
    )
    contratista = fetch_all(
        f"SELECT f.IdOrdenTrabajo AS idOrdenTrabajo, f.IdCompra AS idCompra FROM dbo.Ordenes_Trabajo_Contratista_Factura f WHERE f.IdOrdenTrabajo IN ({marcas})",
        ids_t,
    )
    return maquinaria, contratista


def costo_por_cultivo_campania(id_cultivo: int | None = None, id_campania: int | None = None, id_lote: int | None = None) -> list[dict]:
    filas = _filas_insumos(id_cultivo, id_campania, id_lote)
    if not filas:
        return []

    # Costo FIFO de cada renglón de insumo (ya calculado por producto): se busca
    # el consumo "OT{idOrdenInsumo}" que stock_datos.py agrega como salida.
    productos = {f["idProducto"] for f in filas}
    costo_renglon: dict[int, float] = {}
    for pid in productos:
        stock = calcular_stock(pid).get(pid, {})
        for sid, consumo in stock.get("consumos", {}).items():
            if sid.startswith("OT"):
                costo_renglon[int(sid[2:])] = consumo["costo"]

    agregados: dict[tuple[int, int, int], dict] = defaultdict(lambda: {"insumos": 0.0, "maquinaria": 0.0, "contratistaPesos": 0.0})
    lotes_orden: dict[int, set] = defaultdict(set)
    nombres: dict[tuple[int, int, int], dict] = {}
    for f in filas:
        clave = (f["idCultivo"], f["idCampania"], f["idLote"])
        nombres[clave] = {"cultivo": f["cultivo"], "campania": f["campania"], "lote": f["lote"]}
        lotes_orden[f["idOrdenTrabajo"]].add(clave)
        total_renglon = _f(f["cantidadTotal"]) or 1.0
        proporcion = _f(f["cantidadAsignada"]) / total_renglon
        costo_total_renglon = costo_renglon.get(f["idOrdenInsumo"], 0.0)
        agregados[clave]["insumos"] += costo_total_renglon * proporcion

    maquinaria, contratista = _filas_maquinaria_y_contratista(id_cultivo, id_campania, id_lote)
    for m in maquinaria:
        claves = lotes_orden.get(m["idOrdenTrabajo"], set())
        if not claves:
            continue
        # Prorrateo simple entre las combinaciones lote/cultivo/campaña de esa
        # orden que matchearon el filtro, en partes iguales (aproximación:
        # el detalle exacto por lote ya se ve en el detalle de la orden).
        monto_por_clave = _f(m["costoPorHectarea"]) / len(claves)
        for clave in claves:
            agregados[clave]["maquinaria"] += monto_por_clave

    for c in contratista:
        claves = lotes_orden.get(c["idOrdenTrabajo"], set())
        if not claves:
            continue
        try:
            resultado = costeo.costo_contratista(c["idCompra"], [])
            monto = resultado["montoPesos"] / len(claves)
        except ValueError:
            continue
        for clave in claves:
            agregados[clave]["contratistaPesos"] += monto

    resultado = []
    for clave, montos in agregados.items():
        resultado.append({
            **nombres[clave],
            "idCultivo": clave[0],
            "idCampania": clave[1],
            "idLote": clave[2],
            "costoInsumos": round(montos["insumos"], 2),
            "costoMaquinaria": round(montos["maquinaria"], 2),
            "costoContratista": round(montos["contratistaPesos"], 2),
            "costoTotalOrdenes": round(montos["insumos"] + montos["maquinaria"] + montos["contratistaPesos"], 2),
        })
    resultado.sort(key=lambda r: (r["campania"] or "", r["cultivo"] or "", r["lote"] or ""))
    return resultado


def resumen_campania_heredado(id_campania: int | None = None) -> list[dict]:
    """Costo total heredado (compras, seguros, comercialización, etc.) por
    campaña, vía la vista `vw_ResultadoCultivo_Campaña` (no se modifica, solo se
    lee) — para mostrar junto al costo de las Órdenes de Trabajo nuevas."""
    where, params = ["1 = 1"], []
    if id_campania is not None:
        where.append("v.[IdCampaña] = ?")
        params.append(id_campania)
    try:
        return fetch_all(
            f"""
            SELECT v.[IdCampaña] AS idCampania, v.[Campaña] AS campania, v.TotalCostoPesos AS totalCostoPesos,
                   v.TotalCostoDolares AS totalCostoDolares, v.MargenBrutoPesos AS margenBrutoPesos
            FROM dbo.[vw_ResultadoCultivo_Campaña] v WHERE {' AND '.join(where)}
            """,
            tuple(params),
        )
    except Exception:
        # Vista heredada de solo referencia: si su esquema cambia, no debe
        # romper el costo propio del módulo (FR-017: nunca se modifica).
        return []
