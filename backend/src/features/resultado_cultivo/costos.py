"""Costo de un Cultivo/Campaña: combina los costos heredados (compras, seguros)
con el costo de las Órdenes de Trabajo nuevas (011), evitando contar dos veces
la factura de un contratista que ya esté en el costeo heredado (FR-004)."""

from __future__ import annotations

from collections import defaultdict

from src.db.connection import fetch_all
from src.features.remitos.stock_datos import calcular_stock
from src.features.resultado_cultivo import mapeo

_EPS = 1e-6


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def costos_heredados(id_cultivo: int, id_campania: int) -> list[dict]:
    """Líneas de `vw_ResultadosCultivo_CostosBase` + `Seguros` para el
    `IdDestino` de este Cultivo, ya multiplicadas por `Signo` (cargo/crédito).
    Lista vacía si el Cultivo no tiene `IdDestino` mapeado."""
    id_destino = mapeo.idCultivo_a_destino(id_cultivo)
    if id_destino is None:
        return []
    base = fetch_all(
        """
        SELECT c.Concepto AS concepto, r.Rubro AS rubro, ABS(c.Pesos) * c.Signo AS montoPesos, ABS(c.Dolares) * c.Signo AS montoDolares,
               CASE WHEN c.Origen = 'MaqPropia' THEN 'MaquinariaPropia' ELSE 'Compra' END AS origen, c.IdCompra AS idCompra, c.IdDetalleCompra AS idDetalleCompra
        FROM dbo.vw_ResultadosCultivo_CostosBase c
        LEFT JOIN dbo.Rubros r ON r.IdRubro = c.IdRubro
        WHERE c.IdDestino = ? AND c.IdCampaña = ?
        """,
        (id_destino, id_campania),
    )
    seguros = fetch_all(
        """
        SELECT 'Seguro agrícola' AS concepto, 'Seguros' AS rubro, s.SeguroPesos AS montoPesos, s.SeguroDolares AS montoDolares,
               'Seguro' AS origen, NULL AS idCompra, NULL AS idDetalleCompra
        FROM dbo.vw_ResultadosCultivo_Seguros s
        WHERE s.IdDestino = ? AND s.IdCampaña = ?
        """,
        (id_destino, id_campania),
    )
    for f in base + seguros:
        f["idOrdenTrabajo"] = None
    return base + seguros


def costo_ordenes_trabajo(id_cultivo: int, id_campania: int) -> list[dict]:
    """Insumos FIFO, estimado manual de maquinaria propia y factura imputada.

    No se reparte el contratista por superficie ni por cantidad de insumos.
    """
    distrib = fetch_all(
        """
        SELECT oi.IdOrdenInsumo AS idOrdenInsumo, oi.IdOrdenTrabajo AS idOrdenTrabajo, oi.IdProducto AS idProducto,
               oi.CantidadTotal AS cantidadTotal, d.CantidadAsignada AS cantidadAsignada,
               d.IdLote AS idLote, d.Superficie AS superficie
        FROM dbo.Ordenes_Trabajo_Distrib d
        JOIN dbo.Ordenes_Trabajo_Insumos oi ON oi.IdOrdenInsumo = d.IdOrdenInsumo
        JOIN dbo.Ordenes_Trabajo ot ON ot.IdOrdenTrabajo = oi.IdOrdenTrabajo
        WHERE ot.Estado <> 'Anulada' AND d.IdCultivo = ? AND d.IdCampania = ? AND d.Aplicar = 1
        """,
        (id_cultivo, id_campania),
    )
    resultado: list[dict] = []
    if not distrib:
        return costos_contratista(id_cultivo, id_campania)

    productos = {f["idProducto"] for f in distrib}
    costo_renglon: dict[int, float] = {}
    for pid in productos:
        stock = calcular_stock(pid).get(pid, {})
        for sid, consumo in stock.get("consumos", {}).items():
            if sid.startswith("OT"):
                costo_renglon[int(sid[2:])] = consumo["costo"]

    ordenes_ids = {f["idOrdenTrabajo"] for f in distrib}
    for f in distrib:
        total_renglon = _f(f["cantidadTotal"]) or 1.0
        proporcion = _f(f["cantidadAsignada"]) / total_renglon
        costo = costo_renglon.get(f["idOrdenInsumo"], 0.0) * proporcion
        if abs(costo) > _EPS:
            resultado.append(
                {
                    "concepto": "Insumo", "rubro": None, "montoPesos": round(costo, 2), "montoDolares": None,
                    "origen": "OrdenTrabajo", "idCompra": None, "idDetalleCompra": None, "idOrdenTrabajo": f["idOrdenTrabajo"],
                }
            )

    # La superficie de un lote no se multiplica por la cantidad de insumos.
    marcas = ",".join("?" for _ in ordenes_ids)
    ids_t = tuple(ordenes_ids)
    superficies = defaultdict(dict)
    for f in distrib:
        superficies[f["idOrdenTrabajo"]][f["idLote"]] = max(
            superficies[f["idOrdenTrabajo"]].get(f["idLote"], 0), _f(f["superficie"])
        )

    maquinaria = fetch_all(
        f"SELECT IdOrdenTrabajo, CostoPorHectarea, TipoCambioBna FROM dbo.Ordenes_Trabajo_Maquinaria WHERE IdOrdenTrabajo IN ({marcas})",
        ids_t,
    )
    for m in maquinaria:
        monto = round(_f(m["CostoPorHectarea"]) * sum(superficies[m["IdOrdenTrabajo"]].values()), 2)
        tc = _f(m["TipoCambioBna"])
        resultado.append(
            {
                "concepto": "Maquinaria propia", "rubro": None, "montoPesos": monto, "montoDolares": round(monto / tc, 2) if tc > 0 else None,
                "origen": "OrdenTrabajo", "idCompra": None, "idDetalleCompra": None, "idOrdenTrabajo": m["IdOrdenTrabajo"],
            }
        )

    # Las facturas se imputan por sus renglones, no por superficie de la orden.
    resultado.extend(costos_contratista(id_cultivo, id_campania))

    return resultado


def costos_contratista(id_cultivo: int, id_campania: int) -> list[dict]:
    """Renglones de facturas vinculadas, con su destino y campaña registrados."""
    return fetch_all(
        """
        SELECT 'Contratista' AS concepto, r.Rubro AS rubro,
               CASE WHEN c.Moneda = 'Dolares' THEN v.neto * c.[Tipo de Cambio]
                    ELSE v.neto END AS montoPesos,
               CASE WHEN c.Moneda = 'Dolares' THEN v.neto
                    ELSE v.neto / NULLIF(c.[Tipo de Cambio], 0) END AS montoDolares,
               'OrdenTrabajo' AS origen, d.IdCompra AS idCompra,
               d.IdDetalleCompra AS idDetalleCompra,
               (SELECT MIN(f.IdOrdenTrabajo) FROM dbo.Ordenes_Trabajo_Contratista_Factura f
                JOIN dbo.Ordenes_Trabajo o ON o.IdOrdenTrabajo = f.IdOrdenTrabajo
                WHERE f.IdCompra = d.IdCompra AND o.Estado <> 'Anulada') AS idOrdenTrabajo
        FROM dbo.Det_Compras d
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.Map_CultivoResultado m ON m.IdDestino = d.IdDestino
        LEFT JOIN dbo.Rubros r ON r.IdRubro = d.IdRubro
        CROSS APPLY (SELECT ABS(ISNULL(d.Cantidad, 0) * ISNULL(d.[Precio Unitario], 0)) *
            CASE WHEN c.[Tipo documento] COLLATE Latin1_General_CI_AI = 'Nota de Credito'
                 THEN -1 ELSE 1 END AS neto) v
        WHERE m.IdCultivo = ? AND d.IdCampaña = ?
          AND EXISTS (SELECT 1 FROM dbo.Ordenes_Trabajo_Contratista_Factura f
                      JOIN dbo.Ordenes_Trabajo o ON o.IdOrdenTrabajo = f.IdOrdenTrabajo
                      WHERE f.IdCompra = d.IdCompra AND o.Estado <> 'Anulada')
          AND NOT EXISTS (SELECT 1 FROM dbo.vw_ResultadosCultivo_CostosBase b
                          WHERE b.IdCompra = d.IdCompra)
        """, (id_cultivo, id_campania),
    )


def costo_total(id_cultivo: int, id_campania: int) -> dict:
    lineas = costos_heredados(id_cultivo, id_campania) + costo_ordenes_trabajo(id_cultivo, id_campania)
    return {
        "pesos": round(sum(_f(l["montoPesos"]) for l in lineas), 2),
        "dolares": round(sum(_f(l["montoDolares"]) for l in lineas), 2),
        "lineas": lineas,
    }
