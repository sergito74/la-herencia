"""Costo de un Cultivo/Campaña: combina los costos heredados (compras, seguros)
con el costo de las Órdenes de Trabajo nuevas (011), evitando contar dos veces
la factura de un contratista que ya esté en el costeo heredado (FR-004)."""

from __future__ import annotations

from collections import defaultdict

from src.db.connection import fetch_all
from src.features.remitos.stock_datos import calcular_stock
from src.features.imputacion.repository import RUBROS_FUERA_REPARTO
from src.features.resultado_cultivo import mapeo

_FUERA = ",".join("?" * len(RUBROS_FUERA_REPARTO))
# 048: reparto vigente de cada documento de contratista = su última corrida APROBADA, si tiene alguna fracción con
# orden (una aprobada sin orden es un retiro; una Pendiente posterior no la reemplaza).
_REPARTO_VIGENTE = """(
    SELECT x.IdDetalleCompra AS idCompra, x.IdCorrida AS idCorrida FROM (
        SELECT IdDetalleCompra, IdCorrida, MAX(CASE WHEN IdOrdenTrabajo IS NOT NULL THEN 1 ELSE 0 END) AS conOrden,
               ROW_NUMBER() OVER (PARTITION BY IdDetalleCompra ORDER BY MAX(FechaCalculo) DESC) AS rn
        FROM dbo.ImputacionPropuestas WHERE Origen = 'Contratista' AND Estado = 'Aprobada'
        GROUP BY IdDetalleCompra, IdCorrida) x
    WHERE x.rn = 1 AND x.conOrden = 1)"""

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
          AND NOT EXISTS (  -- 048: renglón ya repartido por las órdenes de trabajo (reparto de contratista vigente)
              SELECT 1 FROM dbo.Det_Compras dd LEFT JOIN dbo.Rubros rr ON rr.IdRubro = dd.IdRubro
              WHERE dd.IdDetalleCompra = c.IdDetalleCompra AND c.IdCompra IN (SELECT rv.idCompra FROM {_REPARTO_VIGENTE} rv)
                AND (rr.Rubro IS NULL OR rr.Rubro NOT IN ({_FUERA})))
        """.format(_REPARTO_VIGENTE=_REPARTO_VIGENTE, _FUERA=_FUERA),
        (id_destino, id_campania, *RUBROS_FUERA_REPARTO),
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
    """048: fracciones del reparto vigente (última corrida APROBADA de contratista con orden) de este cultivo y
    campaña. Pesos = importe; dólares al TC del comprobante."""
    return fetch_all(
        f"""
        SELECT 'Contratista' AS concepto, r.Rubro AS rubro, p.Importe AS montoPesos,
               p.Importe / NULLIF(CASE WHEN c.Moneda = 'Dolares' THEN c.[Tipo de Cambio] END, 0) AS montoDolares,
               'OrdenTrabajo' AS origen, p.IdDetalleCompra AS idCompra, NULL AS idDetalleCompra,
               p.IdOrdenTrabajo AS idOrdenTrabajo
        FROM dbo.ImputacionPropuestas p
        JOIN {_REPARTO_VIGENTE} v ON v.idCorrida = p.IdCorrida
        JOIN dbo.Compras c ON c.IdDeuda = p.IdDetalleCompra
        LEFT JOIN dbo.Ordenes_Trabajo o ON o.IdOrdenTrabajo = p.IdOrdenTrabajo
        LEFT JOIN dbo.Rubros r ON r.IdRubro = o.IdRubro
        WHERE p.IdCultivo = ? AND p.IdCampania = ? AND p.IdOrdenTrabajo IS NOT NULL
        """, (id_cultivo, id_campania),
    )


def costo_total(id_cultivo: int, id_campania: int) -> dict:
    lineas = (costos_heredados(id_cultivo, id_campania) + costo_ordenes_trabajo(id_cultivo, id_campania)
              + gastos_caja(id_cultivo, id_campania))
    return {
        "pesos": round(sum(_f(l["montoPesos"]) for l in lineas), 2),
        "dolares": round(sum(_f(l["montoDolares"]) for l in lineas), 2),
        "lineas": lineas,
    }


def gastos_caja(id_cultivo: int, id_campania: int) -> list[dict]:
    """038: cada reparto vigente es un costo no fiscal, sin duplicar compras."""
    destino = mapeo.idCultivo_a_destino(id_cultivo)
    if destino is None:
        return []
    return fetch_all(
        "SELECT g.Concepto concepto,r.Rubro rubro,d.ImportePesos montoPesos,"
        "CASE WHEN g.ImporteUSD IS NULL THEN NULL ELSE g.ImporteUSD*d.ImportePesos/g.ImportePesos END montoDolares,"
        "'GastoCaja' origen,g.IdGasto idGasto,d.IdReparto idReparto,g.IdOperacion idOperacion,"
        "NULL idCompra,NULL idDetalleCompra,NULL idOrdenTrabajo "
        "FROM dbo.GastoCajaEfectivo g JOIN dbo.RepartosGastoCaja d ON d.IdGasto=g.IdGasto "
        "JOIN dbo.OperacionesCajaEfectivo op ON op.IdOperacion=g.IdOperacion "
        "JOIN dbo.Rubros r ON r.IdRubro=d.IdRubro "
        "WHERE g.Anulada=0 AND op.Estado='Vigente' AND d.IdDestino=? AND d.IdCampania=?",
        (destino, id_campania),
    )
