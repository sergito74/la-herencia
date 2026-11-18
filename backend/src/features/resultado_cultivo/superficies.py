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
