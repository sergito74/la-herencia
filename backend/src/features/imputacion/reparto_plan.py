"""Reparto por superficie del plan agrícola (050 US4, research R-08).

Los costos "a cultivo" que son de la campaña y no de un cultivo (asesoramiento, análisis, comercialización común,
seguro sin cultivo) se reparten entre los cultivos de esa campaña según la superficie planificada. El costo va por
cultivo/campaña, sin lote. Las labores de contratista no pasan por acá: siguen el reparto por orden de la spec 048.
"""

from __future__ import annotations

from src.db.connection import fetch_all

# Partes de la estructura de costo que se reparten por superficie (no son labores con orden).
PARTES_REPARTIBLES = (7, 8, 9)  # Seguro agrícola, Asesoramiento/Análisis, Comercialización


def repartir(total: float, superficies: dict[int, float]) -> dict[int, float]:
    """Pura. {cultivo: importe} proporcional a la superficie; el último cultivo absorbe los centavos de redondeo."""
    validas = {c: float(s) for c, s in superficies.items() if s and float(s) > 0}
    if not validas:
        return {}
    suma = sum(validas.values())
    cultivos = sorted(validas)
    out = {c: round(total * validas[c] / suma, 2) for c in cultivos[:-1]}
    out[cultivos[-1]] = round(total - sum(out.values()), 2)
    return out


def superficie_por_cultivo(id_campania: int) -> dict[int, float]:
    """{IdCultivo: hectáreas planificadas} de la campaña (sin el lote de prueba)."""
    return {
        int(f["c"]): float(f["ha"] or 0)
        for f in fetch_all(
            """
            SELECT p.IdCultivo AS c, SUM(ISNULL(l.Superficie, 0)) AS ha
            FROM dbo.PlanAgricola p JOIN dbo.Lotes l ON l.IdLote = p.IdLote
            WHERE p.[IdCampaña] = ? AND l.[Numero Lote] <> 'PRUE' AND p.IdCultivo IS NOT NULL
            GROUP BY p.IdCultivo
            """,
            (id_campania,),
        )
        if f["ha"] and float(f["ha"]) > 0
    }
