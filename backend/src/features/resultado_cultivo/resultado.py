"""Resultado económico de un Cultivo/Campaña y consolidado de una Campaña:
superficie, rinde, costo, venta, margen y rentabilidad, en pesos y dólares.
Todo se calcula en vivo (FR-005) — no hay caché heredado utilizable."""

from __future__ import annotations

from src.db.connection import fetch_all, fetch_one
from src.features.resultado_cultivo import costos, mapeo

UMBRAL_ADVERTENCIA = 0.20


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def superficie_sembrada(id_cultivo: int, id_campania: int) -> float:
    fila = fetch_one(
        """
        SELECT SUM(l.Superficie) AS total
        FROM dbo.PlanAgricola p
        JOIN dbo.Lotes l ON l.IdLote = p.IdLote
        WHERE p.IdCultivo = ? AND p.IdCampaña = ?
        """,
        (id_cultivo, id_campania),
    )
    return round(_f(fila["total"]), 2) if fila else 0.0


def superficie_cosechada(id_cultivo: int, id_campania: int) -> dict:
    fila = fetch_one(
        "SELECT SuperficieCosechada AS valor, Observaciones AS obs FROM dbo.ResultadoCultivo_Cierre WHERE IdCultivo = ? AND IdCampaña = ?",
        (id_cultivo, id_campania),
    )
    if fila is None:
        return {"valor": None, "estimada": False}
    obs = fila["obs"] or ""
    return {"valor": _f(fila["valor"]) if fila["valor"] is not None else None, "estimada": "Revisar manualmente" in obs}


def cantidad_cosechada(id_cultivo: int, id_campania: int) -> float | None:
    """`Datos Cosecha` (research.md §2, hallazgo durante la implementación):
    kg entregados/liquidados de la cosecha, por `IdDestino` + `IdCampaña`."""
    id_destino = mapeo.idCultivo_a_destino(id_cultivo)
    if id_destino is None:
        return None
    fila = fetch_one(
        'SELECT SUM([Cantidad a Liquidar]) AS total FROM dbo.[Datos Cosecha] WHERE IdDestino = ? AND IdCampaña = ?',
        (id_destino, id_campania),
    )
    if fila is None or fila["total"] is None:
        return None
    return round(_f(fila["total"]), 2)


def venta_neta(id_cultivo: int, id_campania: int) -> dict:
    id_grano = mapeo.idCultivo_a_grano(id_cultivo)
    if id_grano is None:
        return {"pesos": 0.0, "dolares": 0.0}
    campania_texto = mapeo.campania_id_a_texto(id_campania)
    if campania_texto is None:
        return {"pesos": 0.0, "dolares": 0.0}
    ventas = fetch_one(
        """
        SELECT SUM(v.VentaPesos + ISNULL(v.BonifPesos, 0)) AS pesos, SUM(v.VentaDolares + ISNULL(v.BonifDolares, 0)) AS dolares
        FROM dbo.vw_ResultadosCultivo_Ventas v WHERE v.IdCultivo = ? AND v.Campaña = ?
        """,
        (id_cultivo, campania_texto),
    )
    deducciones = fetch_one(
        "SELECT SUM(Pesos) AS pesos, SUM(Dolares) AS dolares FROM dbo.vw_ResultadosCultivo_Deducciones WHERE IdCultivo = ? AND Campaña = ?",
        (id_cultivo, campania_texto),
    )
    return {
        "pesos": round(_f(ventas["pesos"] if ventas else 0) - _f(deducciones["pesos"] if deducciones else 0), 2),
        "dolares": round(_f(ventas["dolares"] if ventas else 0) - _f(deducciones["dolares"] if deducciones else 0), 2),
    }


def detalle_costos(id_cultivo: int, id_campania: int) -> list[dict]:
    return costos.costos_heredados(id_cultivo, id_campania) + costos.costo_ordenes_trabajo(id_cultivo, id_campania)


def _costo_por_hectarea(costo: float, superficie: float | None) -> float | None:
    if not superficie or superficie <= 0:
        return None
    return round(costo / superficie, 2)


def resultado_cultivo(id_cultivo: int, id_campania: int) -> dict:
    cultivo = fetch_one("SELECT Cultivo AS nombre FROM dbo.Cultivos WHERE IdCultivo = ?", (id_cultivo,))
    campania = fetch_one("SELECT Campaña AS nombre FROM dbo.Campañas WHERE IdCampaña = ?", (id_campania,))
    if cultivo is None:
        raise ValueError(f"El cultivo {id_cultivo} no existe.")
    if campania is None:
        raise ValueError(f"La campaña {id_campania} no existe.")

    lineas_costo = detalle_costos(id_cultivo, id_campania)
    costo_pesos = round(sum(_f(l["montoPesos"]) for l in lineas_costo), 2)
    costo_dolares = round(sum(_f(l["montoDolares"]) for l in lineas_costo), 2)

    sup_sembrada = superficie_sembrada(id_cultivo, id_campania)
    cosecha = superficie_cosechada(id_cultivo, id_campania)
    sup_cosechada = cosecha["valor"]
    cant_cosechada = cantidad_cosechada(id_cultivo, id_campania)
    rinde = round(cant_cosechada / sup_cosechada, 2) if cant_cosechada is not None and sup_cosechada is not None and sup_cosechada > 0 and mapeo.idCultivo_a_grano(id_cultivo) is not None else None

    venta = venta_neta(id_cultivo, id_campania)
    margen_pesos = round(venta["pesos"] - costo_pesos, 2)
    margen_dolares = round(venta["dolares"] - costo_dolares, 2)
    rentabilidad_pesos = round(margen_pesos / costo_pesos, 4) if costo_pesos else None
    rentabilidad_dolares = round(margen_dolares / costo_dolares, 4) if costo_dolares else None

    return {
        "idCultivo": id_cultivo,
        "cultivo": cultivo["nombre"] if cultivo else None,
        "idCampania": id_campania,
        "campania": campania["nombre"] if campania else None,
        "superficieSembrada": sup_sembrada,
        "superficieCosechada": sup_cosechada,
        "superficiePicada": None,
        "rinde": rinde,
        "costoTotalPesos": costo_pesos,
        "costoTotalDolares": costo_dolares,
        "costoPorHectareaSembradaPesos": _costo_por_hectarea(costo_pesos, sup_sembrada),
        "costoPorHectareaSembradaDolares": _costo_por_hectarea(costo_dolares, sup_sembrada),
        "costoPorHectareaCosechadaPesos": _costo_por_hectarea(costo_pesos, sup_cosechada),
        "costoPorHectareaCosechadaDolares": _costo_por_hectarea(costo_dolares, sup_cosechada),
        "ventaNetaPesos": venta["pesos"],
        "ventaNetaDolares": venta["dolares"],
        "margenBrutoPesos": margen_pesos,
        "margenBrutoDolares": margen_dolares,
        "rentabilidadPesos": rentabilidad_pesos,
        "rentabilidadDolares": rentabilidad_dolares,
        "costeoDolaresIncompleto": any(l["montoDolares"] is None for l in lineas_costo),
        "supCosechaEstimada": cosecha["estimada"],
        "advertenciaMargenNoRepresentativo": venta["pesos"] > 0 and costo_pesos < UMBRAL_ADVERTENCIA * venta["pesos"],
    }


def _cultivos_con_datos(id_campania: int) -> list[int]:
    """Cultivos con algún dato (costeo heredado, orden de trabajo o venta) en
    esta Campaña — universo a consolidar en `resultado_campania`."""
    filas = fetch_all(
        """
        SELECT DISTINCT m.IdCultivo AS idCultivo
        FROM dbo.Map_CultivoResultado m
        WHERE m.Activo = 1 AND (
            EXISTS (SELECT 1 FROM dbo.vw_ResultadosCultivo_CostosBase c WHERE c.IdDestino = m.IdDestino AND c.IdCampaña = ?)
            OR EXISTS (SELECT 1 FROM dbo.PlanAgricola p WHERE p.IdCultivo = m.IdCultivo AND p.IdCampaña = ?)
            OR EXISTS (SELECT 1 FROM dbo.ResultadoCultivo_Cierre rc WHERE rc.IdCultivo = m.IdCultivo AND rc.IdCampaña = ?)
            OR EXISTS (SELECT 1 FROM dbo.vw_ResultadosCultivo_Seguros s WHERE s.IdDestino = m.IdDestino AND s.IdCampaña = ?)
            OR EXISTS (SELECT 1 FROM dbo.Ordenes_Trabajo_Distrib d
                       JOIN dbo.Ordenes_Trabajo_Insumos i ON i.IdOrdenInsumo = d.IdOrdenInsumo
                       JOIN dbo.Ordenes_Trabajo o ON o.IdOrdenTrabajo = i.IdOrdenTrabajo
                       WHERE d.IdCultivo = m.IdCultivo AND d.IdCampania = ? AND d.Aplicar = 1 AND o.Estado <> 'Anulada')
            OR EXISTS (SELECT 1 FROM dbo.Det_Compras dc
                       JOIN dbo.Ordenes_Trabajo_Contratista_Factura f ON f.IdCompra = dc.IdCompra
                       JOIN dbo.Ordenes_Trabajo o ON o.IdOrdenTrabajo = f.IdOrdenTrabajo
                       WHERE dc.IdDestino = m.IdDestino AND dc.IdCampaña = ? AND o.Estado <> 'Anulada')

            OR EXISTS (
                SELECT 1 FROM dbo.vw_ResultadosCultivo_Ventas v
                JOIN dbo.Campañas ca ON ca.Campaña = v.Campaña
                WHERE v.IdCultivo = m.IdCultivo AND ca.IdCampaña = ?
            )
        )
        """,
        (id_campania,) * 7,
    )
    return [f["idCultivo"] for f in filas]


def costo_sin_clasificar(id_campania: int) -> dict | None:
    fila = fetch_one(
        """
        SELECT SUM(ABS(c.Pesos) * c.Signo) AS pesos, SUM(ABS(c.Dolares) * c.Signo) AS dolares
        FROM dbo.vw_ResultadosCultivo_CostosBase c
        WHERE c.IdCampaña IS NULL OR (c.IdCampaña = ?
          AND NOT EXISTS (SELECT 1 FROM dbo.Map_CultivoResultado m WHERE m.IdDestino = c.IdDestino))
        """,
        (id_campania,),
    )
    if fila is None or (fila["pesos"] is None and fila["dolares"] is None):
        return None
    motivo = "Sin cultivo asociado en esta campaña o sin campaña asignada (todas las campañas). No incluido en los totales."
    return {"montoPesos": round(_f(fila["pesos"]), 2), "montoDolares": round(_f(fila["dolares"]), 2), "motivo": motivo}


def resultado_campania(id_campania: int) -> dict:
    campania = fetch_one("SELECT Campaña AS nombre FROM dbo.Campañas WHERE IdCampaña = ?", (id_campania,))
    if campania is None:
        raise ValueError([f"La campaña {id_campania} no existe."])

    cultivos = [resultado_cultivo(idc, id_campania) for idc in _cultivos_con_datos(id_campania)]
    sin_clasificar = costo_sin_clasificar(id_campania)

    sup_total = round(sum(c["superficieSembrada"] for c in cultivos), 2)
    cosechadas_con_dato = [c["superficieCosechada"] for c in cultivos if c["superficieCosechada"] is not None]
    cosecha_completa = bool(cultivos) and len(cosechadas_con_dato) == len(cultivos)
    sup_cosechada = round(sum(cosechadas_con_dato), 2) if cosechadas_con_dato else None
    costo_pesos = round(sum(c["costoTotalPesos"] for c in cultivos), 2)
    costo_dolares = round(sum(c["costoTotalDolares"] for c in cultivos), 2)
    venta_pesos = round(sum(c["ventaNetaPesos"] for c in cultivos), 2)
    venta_dolares = round(sum(c["ventaNetaDolares"] for c in cultivos), 2)
    margen_pesos = round(venta_pesos - costo_pesos, 2)
    margen_dolares = round(venta_dolares - costo_dolares, 2)

    return {
        "idCampania": id_campania,
        "campania": campania["nombre"],
        "superficieSembrada": sup_total,
        "superficieCosechada": sup_cosechada,
        "superficieCosechadaCompleta": cosecha_completa,
        "superficiePicada": None,
        "costoTotalPesos": costo_pesos,
        "costoTotalDolares": costo_dolares,
        "costoPorHectareaSembradaPesos": _costo_por_hectarea(costo_pesos, sup_total),
        "costoPorHectareaSembradaDolares": _costo_por_hectarea(costo_dolares, sup_total),
        "costoPorHectareaCosechadaPesos": _costo_por_hectarea(costo_pesos, sup_cosechada) if cosecha_completa else None,
        "costoPorHectareaCosechadaDolares": _costo_por_hectarea(costo_dolares, sup_cosechada) if cosecha_completa else None,
        "ventaNetaPesos": venta_pesos,
        "ventaNetaDolares": venta_dolares,
        "margenBrutoPesos": margen_pesos,
        "margenBrutoDolares": margen_dolares,
        "rentabilidadPesos": round(margen_pesos / costo_pesos, 4) if costo_pesos else None,
        "rentabilidadDolares": round(margen_dolares / costo_dolares, 4) if costo_dolares else None,
        "costeoDolaresIncompleto": any(c.get("costeoDolaresIncompleto", False) for c in cultivos),
        "cultivos": cultivos,
        "costoSinClasificar": sin_clasificar,
    }
