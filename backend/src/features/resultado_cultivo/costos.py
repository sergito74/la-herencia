"""Costo de un Cultivo/Campaña: combina los costos heredados (compras, seguros)
con el costo de las Órdenes de Trabajo nuevas (011), evitando contar dos veces
la factura de un contratista que ya esté en el costeo heredado (FR-004)."""

from __future__ import annotations

from collections import defaultdict

from src.db.connection import fetch_all, fetch_one
from src.features.imputacion import tamiz_repository
from src.features.remitos import capas_factura
from src.features.remitos.stock_datos import calcular_stock
from src.features.imputacion.repository import RUBROS_FUERA_REPARTO
from src.features.resultado_cultivo import mapeo

_FUERA = ",".join("?" * len(RUBROS_FUERA_REPARTO))
# 048: reparto vigente de cada documento de contratista = su última corrida APROBADA, si tiene alguna fracción con
# orden (una aprobada sin orden es un retiro; una Pendiente posterior no la reemplaza).
_REPARTO_VIGENTE = """(
    SELECT x.IdDetalleCompra AS idCompra, x.IdCorrida AS idCorrida FROM (
        SELECT IdDetalleCompra, IdCorrida, MAX(CASE WHEN IdOrdenTrabajo IS NOT NULL THEN 1 ELSE 0 END) AS conOrden,
               ROW_NUMBER() OVER (PARTITION BY IdDetalleCompra ORDER BY MAX(FechaCalculo) DESC, MAX(IdPropuesta) DESC) AS rn
        FROM dbo.ImputacionPropuestas WHERE Origen = 'Contratista' AND Estado = 'Aprobada'
        GROUP BY IdDetalleCompra, IdCorrida) x
    WHERE x.rn = 1 AND x.conOrden = 1)"""

_EPS = 1e-6

# 17/11/2026: dólares del costo con la misma regla de la vista heredada (vw_ResultadosCultivo_CostosBase): comprobante
# en dólares -> sus US$ (pesos / TC del comprobante); en pesos -> pesos / BNA comprador divisa del día del comprobante;
# los que ajustan el tipo de cambio no suman dólares.
_USD_SQL = ("CASE WHEN c.Moneda = 'Dolares' THEN p.Importe / NULLIF(c.[Tipo de Cambio], 0) "
            "WHEN ISNULL(c.[Ajusta Tipo Cambio], 0) = 0 THEN p.Importe / NULLIF(tcb.TC_CompDivisa, 0) ELSE 0 END")


def _divisor_usd_capas() -> dict[str, float]:
    """TC con que se pasa a dólares el costo de cada capa de stock: el de su factura (en dólares, su TC; en pesos,
    BNA comprador divisa del día). Capas de remito (R...) por su factura vinculada; capas de factura (FC...) directo."""
    out: dict[str, float] = {}
    for f in fetch_all(
        """
        SELECT 'R' + CAST(t.IdDetalleRemito AS varchar(20)) AS id,
               MAX(CASE WHEN c.Moneda = 'Dolares' THEN c.[Tipo de Cambio] ELSE tcb.TC_CompDivisa END) AS tc
        FROM dbo.tblRemitoCompra t JOIN dbo.Det_Compras d ON d.IdDetalleCompra = t.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra LEFT JOIN dbo.vw_TC_BNA_PorCompra tcb ON tcb.IdDeuda = c.IdDeuda
        GROUP BY t.IdDetalleRemito
        UNION ALL
        SELECT 'FC' + CAST(d.IdDetalleCompra AS varchar(20)),
               CASE WHEN c.Moneda = 'Dolares' THEN c.[Tipo de Cambio] ELSE tcb.TC_CompDivisa END
        FROM dbo.TamizRenglones tz JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra LEFT JOIN dbo.vw_TC_BNA_PorCompra tcb ON tcb.IdDeuda = c.IdDeuda
        WHERE tz.Vigente = 1 AND tz.Destino = 'CultivoStock'
        """
    ):
        if f["tc"]:
            out[f["id"]] = float(f["tc"])
    return out


def _bna(fecha) -> float | None:
    f = fetch_one("SELECT TOP 1 Comp_Divisa AS tc FROM dbo.[Dolar BNA] WHERE Fecha <= ? ORDER BY Fecha DESC", (fecha,))
    return float(f["tc"]) if f and f["tc"] else None

# 050 (17/11/2026, revisión de especialistas): una sola imputación vigente por renglón, la del origen que corresponde
# a su clasificación (Insumo ↔ Va a stock; Directo ↔ a cultivo, ganadería o gasto general). Desempate determinista.
VIGENTE_050 = """p.IdCorrida = (SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2
                             WHERE p2.IdDetalleCompra = p.IdDetalleCompra AND p2.Origen = p.Origen AND p2.Estado <> 'Reemplazada'
                             ORDER BY p2.FechaCalculo DESC, p2.IdPropuesta DESC)
          AND ((p.Origen = 'Insumo' AND tz.Destino = 'CultivoStock')
               OR (p.Origen = 'Directo' AND tz.Destino IN ('Cultivo', 'Ganaderia', 'Estructura')))"""


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def esquema_050_activo() -> bool:
    """050: con ImputacionConfig.Activo = 0 el resultado es idéntico al de antes."""
    return bool(tamiz_repository.config().get("activo"))


# 050: renglón en alcance = tiene clasificación vigente del tamiz; su costo entra por costos_alcance.
_NO_EN_ALCANCE = " AND NOT EXISTS (SELECT 1 FROM dbo.TamizRenglones tz WHERE tz.IdDetalleCompra = c.IdDetalleCompra AND tz.Vigente = 1)"


# 050 (17/11/2026): factura anterior al corte cuya mercadería entró por remito: su costo llega por el consumo de las
# órdenes (FIFO), así que la imputación manual de la factura no se suma. Rige para todas las campañas (Sergio
# 17/11/2026: primero desde 2023, después "Sí" a extenderlo a las anteriores). Solo cuenta un remito de hasta
# un año antes de la factura: los vínculos heredados de Access con remitos viejos (ej. semilla de sorgo 2023 contra
# un remito de 2019) no se consumen en la campaña de la factura y su costo se perdería.
_PASO_POR_STOCK = """
          AND NOT (EXISTS (SELECT 1 FROM dbo.tblRemitoCompra trc
                           JOIN dbo.Remitos_Detalles rdx ON rdx.IdDetalleRemito = trc.IdDetalleRemito
                           JOIN dbo.Remitos rx ON rx.IdRemito = rdx.IdRemito
                           JOIN dbo.Det_Compras dcx ON dcx.IdDetalleCompra = trc.IdDetalleCompra
                           JOIN dbo.Compras cpx ON cpx.IdDeuda = dcx.IdCompra
                           WHERE trc.IdDetalleCompra = c.IdDetalleCompra AND rx.Fecha >= DATEADD(day, -365, cpx.Fecha)))"""


def costos_heredados(id_cultivo: int, id_campania: int) -> list[dict]:
    """Líneas de `vw_ResultadosCultivo_CostosBase` (sin los cobros de seguro, que son ingreso) para el
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
                AND (rr.Rubro IS NULL OR rr.Rubro NOT IN ({_FUERA}))){_ALCANCE}{_STOCK}
        """.format(_REPARTO_VIGENTE=_REPARTO_VIGENTE, _FUERA=_FUERA, _ALCANCE=_NO_EN_ALCANCE if esquema_050_activo() else "",
                   _STOCK=_PASO_POR_STOCK if esquema_050_activo() else ""),
        (id_destino, id_campania, *RUBROS_FUERA_REPARTO),
    )
    # 17/11/2026: lo de Cultivos_Seguros_Cobros son indemnizaciones COBRADAS por siniestros: no son costo, son un
    # recupero que suma a la venta neta (resultado.recupero_seguro), como en el formulario de Access.
    for f in base:
        f["idOrdenTrabajo"] = None
    return base


def consumos_sin_factura(id_cultivo: int, id_campania: int) -> list[dict]:
    """17/11/2026: insumos que las órdenes de este cultivo/campaña consumieron de remitos sin factura vinculada (o sin
    remito): valen $0 hasta que llegue la factura, así que el costo es provisorio. Por remito y producto."""
    filas: list[dict] = []
    costo_ordenes_trabajo(id_cultivo, id_campania, filas)
    agrupado: dict[tuple, dict] = {}
    for f in filas:
        k = (f["remito"], f["idProducto"])
        g = agrupado.setdefault(k, {**f, "cantidad": 0.0, "ordenes": set()})
        g["cantidad"] += f["cantidad"]
        g["ordenes"].add(f["idOrdenTrabajo"])
    from src.features.imputacion.tamiz_repository import nombre_producto
    out = []
    for g in agrupado.values():
        out.append({"remito": g["remito"] or "sin remito", "fecha": g["fecha"], "producto": nombre_producto(g["idProducto"]),
                    "cantidad": round(g["cantidad"], 2), "ordenes": sorted(o for o in g["ordenes"] if o)})
    return sorted(out, key=lambda x: (str(x["fecha"] or ""), x["remito"]))


def costo_ordenes_trabajo(id_cultivo: int, id_campania: int, pendientes: list | None = None) -> list[dict]:
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
    activo = esquema_050_activo()
    remitos_alcance = capas_factura.renglones_remito_en_alcance() if activo else {}
    divisor = _divisor_usd_capas()
    usd_renglon: dict[int, float] = {}
    pendiente_renglon: dict[int, list] = defaultdict(list)
    for pid in productos:
        stock = calcular_stock(pid).get(pid, {})
        cant_capa = {c["id"]: _f(c["cantidad"]) for c in stock.get("capas", [])}
        for sid, consumo in stock.get("consumos", {}).items():
            if sid.startswith("OT"):
                costo = consumo["costo"]
                usd = 0.0
                fecha = (stock.get("salidaMeta", {}).get(sid) or {}).get("fecha")
                bna_orden = None
                capas_meta = {c["id"]: c for c in stock.get("capas", [])}
                for it in consumo["items"]:
                    if it["costo_unitario"] is None:
                        # capa sin factura: costo pendiente (no suma pesos ni dólares); se informa como provisorio
                        if it["cantidad"] > 0.001:
                            m = capas_meta.get(it["capa"]) or {}
                            pendiente_renglon[int(sid[2:])].append(
                                {"idProducto": pid, "cantidad": it["cantidad"], "remito": m.get("nroRemito"),
                                 "idRemito": m.get("idRemito"), "fecha": m.get("fecha")})
                        continue
                    pesos = it["cantidad"] * it["costo_unitario"]
                    if activo:
                        # 050: lo consumido de capas en alcance ya está en las fracciones aprobadas (costos_alcance).
                        en_alcance = pesos * capas_factura.parte_en_alcance(it["capa"], cant_capa.get(it["capa"], 0.0), remitos_alcance)
                        costo -= en_alcance
                        pesos -= en_alcance
                    tc = divisor.get(it["capa"])
                    if tc is None and fecha is not None:
                        if bna_orden is None:
                            bna_orden = _bna(fecha) or 0.0
                        tc = bna_orden or None
                    usd += pesos / tc if tc else 0.0
                costo_renglon[int(sid[2:])] = costo
                usd_renglon[int(sid[2:])] = usd

    ordenes_ids = {f["idOrdenTrabajo"] for f in distrib}
    # 17/11/2026: una línea por renglón de orden (suma de sus lotes) y redondeo al final, para no perder centavos.
    por_renglon: dict[int, dict] = {}
    for f in distrib:
        total_renglon = _f(f["cantidadTotal"]) or 1.0
        proporcion = _f(f["cantidadAsignada"]) / total_renglon
        g = por_renglon.setdefault(f["idOrdenInsumo"], {"orden": f["idOrdenTrabajo"], "p": 0.0})
        g["p"] += proporcion
    for oi, g in por_renglon.items():
        costo = costo_renglon.get(oi, 0.0) * g["p"]
        for pe in pendiente_renglon.get(oi, []):
            if pendientes is not None:
                pendientes.append({**pe, "cantidad": pe["cantidad"] * g["p"], "idOrdenTrabajo": g["orden"]})
        if abs(costo) > _EPS:
            resultado.append(
                {
                    "concepto": "Insumo", "rubro": None, "montoPesos": round(costo, 2),
                    "montoDolares": round(usd_renglon.get(oi, 0.0) * g["p"], 2),
                    "origen": "OrdenTrabajo", "idCompra": None, "idDetalleCompra": None, "idOrdenTrabajo": g["orden"],
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
    campaña. Pesos = importe; dólares con la regla de la casa (_USD_SQL)."""
    return fetch_all(
        f"""
        SELECT 'Contratista' AS concepto, r.Rubro AS rubro, p.Importe AS montoPesos,
               {_USD_SQL} AS montoDolares,
               'OrdenTrabajo' AS origen, p.IdDetalleCompra AS idCompra, NULL AS idDetalleCompra,
               p.IdOrdenTrabajo AS idOrdenTrabajo
        FROM dbo.ImputacionPropuestas p
        JOIN {_REPARTO_VIGENTE} v ON v.idCorrida = p.IdCorrida
        JOIN dbo.Compras c ON c.IdDeuda = p.IdDetalleCompra
        LEFT JOIN dbo.vw_TC_BNA_PorCompra tcb ON tcb.IdDeuda = c.IdDeuda
        LEFT JOIN dbo.Ordenes_Trabajo o ON o.IdOrdenTrabajo = p.IdOrdenTrabajo
        LEFT JOIN dbo.Rubros r ON r.IdRubro = o.IdRubro
        WHERE p.IdCultivo = ? AND p.IdCampania = ? AND p.IdOrdenTrabajo IS NOT NULL
        """, (id_cultivo, id_campania),
    )


def costos_alcance(id_cultivo: int, id_campania: int) -> list[dict]:
    """050: fracciones Aprobadas (Insumo/Directo) de la corrida vigente de cada renglón en alcance."""
    if not esquema_050_activo():
        return []
    return fetch_all(
        """
        SELECT CASE WHEN p.Origen = 'Directo' THEN 'Compra' ELSE 'Insumo' END AS concepto, pe.Nombre AS rubro,
               p.Importe AS montoPesos,
               {usd} AS montoDolares,
               'Alcance050' AS origen, d.IdCompra AS idCompra, p.IdDetalleCompra AS idDetalleCompra,
               p.IdOrdenTrabajo AS idOrdenTrabajo, p.IdParte AS idParte
        FROM dbo.ImputacionPropuestas p
        JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = p.IdDetalleCompra AND tz.Vigente = 1
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = p.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.vw_TC_BNA_PorCompra tcb ON tcb.IdDeuda = c.IdDeuda
        LEFT JOIN dbo.PartesEstructuraCosto pe ON pe.IdParte = p.IdParte
        WHERE p.Origen IN ('Insumo', 'Directo') AND p.Estado = 'Aprobada' AND p.IdCultivo = ? AND p.IdCampania = ?
          AND {vigente}
          -- Factura de contratista con reparto por órdenes (048) vigente: manda ese reparto (no se cuenta dos veces).
          AND NOT (p.Origen = 'Directo' AND d.IdCompra IN (SELECT rv.idCompra FROM {reparto} rv)
                   AND NOT EXISTS (SELECT 1 FROM dbo.Rubros rr WHERE rr.IdRubro = d.IdRubro AND rr.Rubro IN ({fuera})))
        """.format(vigente=VIGENTE_050, reparto=_REPARTO_VIGENTE, fuera=_FUERA, usd=_USD_SQL),
        (id_cultivo, id_campania, *RUBROS_FUERA_REPARTO),
    )


def costo_total(id_cultivo: int, id_campania: int) -> dict:
    lineas = (costos_heredados(id_cultivo, id_campania) + costo_ordenes_trabajo(id_cultivo, id_campania)
              + gastos_caja(id_cultivo, id_campania) + costos_alcance(id_cultivo, id_campania))
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
