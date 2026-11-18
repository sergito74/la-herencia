"""Superficies de un cultivo/campaña y cuál se usa para cada indicador (18/11/2026, regla general para todos los
cultivos agrícolas; ver specs/050-tamizado-imputacion-cultivos/reglas-superficies.md).

- Bruta (afectada): suma de los lotes asignados en el plan agrícola. Solo control y aprovechamiento.
- Sembrada: facturas de siembra (y siembra con maquinaria propia); si se cosechó más, la cosechada. Es el
  denominador del costo por ha y del margen bruto por ha. Sin siembra registrada se usa la bruta, marcada "teórica".
- Cosechada: cierre del cultivo. Denominador del rinde y del costo de cosecha por ha.
- Aprovechamiento: sembrada / bruta (cabeceras, bajos, caminos y rincones no sembrados).
Las ha no sembradas de un lote sembrado no se separan: su costo queda en el cultivo, dividido por las ha sembradas.
"""

from __future__ import annotations

from src.db.connection import fetch_one


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def base_por_ha(bruta: float, sembrada_real: float | None, cosechada: float | None, no_sembrada: float = 0.0) -> dict:
    """Pura: arma las superficies y elige el denominador por ha. Lotes marcados "no sembrado" en el plan no son
    superficie del cultivo; si todo el cultivo quedó sin sembrar, no hay costo por ha (costo hundido)."""
    cos = round(_f(cosechada), 1)
    if sembrada_real is None and bruta <= 0 and no_sembrada > 0:
        return {"bruta": 0.0, "sembrada": 0.0, "teorica": False, "segunCosecha": False, "cosechada": None,
                "aprovechamiento": None, "noSembrado": True, "noSembradaHa": round(no_sembrada, 1)}
    if sembrada_real is None:
        sembrada, teorica, segun_cosecha = round(bruta, 1), True, False
    else:
        sembrada, teorica, segun_cosecha = max(round(sembrada_real, 1), cos), False, cos > round(sembrada_real, 1)
    return {"bruta": round(bruta, 1), "sembrada": sembrada, "teorica": teorica, "segunCosecha": segun_cosecha,
            "cosechada": cos if cosechada is not None else None,
            "aprovechamiento": round(sembrada / bruta, 4) if bruta > 0 and not teorica else None,
            "noSembrado": False, "noSembradaHa": round(no_sembrada, 1)}


def superficies(id_cultivo: int, id_campania: int) -> dict:
    from src.features.resultado_cultivo import formularios_access as F

    f = fetch_one(
        "SELECT SUM(CASE WHEN X.ns = 0 THEN L.Superficie ELSE 0 END) AS s, SUM(CASE WHEN X.ns = 1 THEN L.Superficie ELSE 0 END) AS ns "
        "FROM dbo.Lotes L JOIN (SELECT P.IdLote, MIN(CAST(ISNULL(P.NoSembrado, 0) AS int)) AS ns FROM dbo.PlanAgricola P "
        "WHERE P.IdCultivo = ? AND P.IdCampaña = ? GROUP BY P.IdLote) X ON L.IdLote = X.IdLote", (id_cultivo, id_campania)) or {}
    bruta, no_sembrada = _f(f.get("s")), _f(f.get("ns"))
    try:
        id_destino = F._destino(id_cultivo)[0]
    except ValueError:
        id_destino = None
    real = F.superficie_sembrada_real(id_destino, id_campania) if id_destino is not None else None
    cierre = fetch_one("SELECT SuperficieCosechada AS s FROM dbo.ResultadoCultivo_Cierre WHERE IdCultivo = ? AND IdCampaña = ?",
                       (id_cultivo, id_campania))
    return base_por_ha(bruta, real, cierre["s"] if cierre and cierre["s"] is not None else None, no_sembrada)


def ordenes_de_siembra(id_cultivo: int, id_campania: int) -> dict[str, float]:
    """Superficie de cada lote en las órdenes de siembra (vieja y nueva) del cultivo/campaña; si un lote aparece en
    varias órdenes (resiembra, siembra en dos pasadas) se toma la mayor."""
    from src.db.connection import fetch_all

    por_lote: dict[str, float] = {}
    for f in fetch_all(
            "SELECT l.[Numero Lote] AS lote, ol.Superficie AS ha FROM dbo.Ordenes o JOIN dbo.Ordenes_Lotes ol ON ol.IdOrden = o.IdOrden "
            "JOIN dbo.Lotes l ON l.IdLote = ol.IdLote WHERE o.IdTipoLabor = 3 AND ol.IdCultivo = ? AND ol.IdCampaña = ? "
            "UNION ALL SELECT l.[Numero Lote], MAX(d.Superficie) FROM dbo.Ordenes_Trabajo o "
            "JOIN dbo.Ordenes_Trabajo_Insumos i ON i.IdOrdenTrabajo = o.IdOrdenTrabajo JOIN dbo.Ordenes_Trabajo_Distrib d ON d.IdOrdenInsumo = i.IdOrdenInsumo "
            "JOIN dbo.Lotes l ON l.IdLote = d.IdLote WHERE o.IdTipoLabor = 3 AND o.Estado <> 'Anulada' AND d.IdCultivo = ? AND d.IdCampania = ? "
            "GROUP BY o.IdOrdenTrabajo, l.[Numero Lote]", (id_cultivo, id_campania, id_cultivo, id_campania)):
        k = str(f["lote"]).strip().upper()
        por_lote[k] = max(por_lote.get(k, 0.0), _f(f["ha"]))
    return por_lote


def repartir_por_lote(ordenes: dict[str, float], sembrada: float) -> dict[str, float]:
    """Pura (regla 9): la superficie sembrada de la factura repartida entre los lotes en proporción a la orden de siembra."""
    total = sum(ordenes.values())
    if total <= 0 or sembrada <= 0:
        return {}
    reparto = {k: round(v * sembrada / total, 1) for k, v in ordenes.items()}
    ajuste = round(sembrada - sum(reparto.values()), 1)  # el redondeo va al lote más grande
    if ajuste and reparto:
        mayor = max(reparto, key=reparto.get)
        reparto[mayor] = round(reparto[mayor] + ajuste, 1)
    return reparto


def sembrada_por_lote(id_cultivo: int, id_campania: int) -> list[dict]:
    S = superficies(id_cultivo, id_campania)
    ordenes = ordenes_de_siembra(id_cultivo, id_campania)
    if S["teorica"] or S["noSembrado"] or not ordenes:
        return [{"lote": k, "orden": round(v, 1), "sembrada": None} for k, v in sorted(ordenes.items())]
    reparto = repartir_por_lote(ordenes, S["sembrada"])
    return [{"lote": k, "orden": round(v, 1), "sembrada": reparto.get(k)} for k, v in sorted(ordenes.items())]
