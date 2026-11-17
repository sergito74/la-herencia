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


TRIGO, SOJA_SEGUNDA = 8, 4  # doble cultivo: el lote se imputa 50% a cada uno (Sergio 17/11/2026)


def superficies_de_lotes(filas: list[dict]) -> dict:
    """Pura. `filas`: {idLote, idCultivo, superficie[, idCampania]} del plan; con idCampania la clave es
    (cultivo, campaña). Cada lote suma su superficie teórica al cultivo; el lote
    de doble cultivo Trigo/Soja de segunda suma la mitad a cada uno."""
    por_lote: dict = {}
    sup: dict = {}
    for f in filas:
        clave = (f["idCultivo"], f["idCampania"]) if "idCampania" in f else f["idCultivo"]
        por_lote.setdefault(f["idLote"], set()).add(clave)
        sup[f["idLote"]] = float(f["superficie"] or 0)
    out: dict = {}
    for lote, claves in por_lote.items():
        cult = {k[0] if isinstance(k, tuple) else k for k in claves}
        doble = {TRIGO, SOJA_SEGUNDA} <= cult
        for k in claves:
            c = k[0] if isinstance(k, tuple) else k
            out[k] = out.get(k, 0.0) + sup[lote] * (0.5 if doble and c in (TRIGO, SOJA_SEGUNDA) else 1.0)
    return {c: ha for c, ha in out.items() if ha > 0}


def superficie_por_cultivo(id_campania: int) -> dict[tuple[int, int], float]:
    """{(IdCultivo, IdCampaña): hectáreas} del plan agrícola de la campaña. Las pasturas y verdeos de invierno llevan el año de
    siembra (Avena 2025) y entran en la campaña de doble año que empieza ese año (2025/2026)."""
    filas = fetch_all(
        """
        SELECT p.IdLote AS idLote, p.IdCultivo AS idCultivo, p.[IdCampaña] AS idCampania, l.Superficie AS superficie
        FROM dbo.PlanAgricola p JOIN dbo.Lotes l ON l.IdLote = p.IdLote
        JOIN dbo.[Campañas] ca ON ca.[IdCampaña] = p.[IdCampaña]
        JOIN dbo.[Campañas] base ON base.[IdCampaña] = ?
        WHERE l.[Numero Lote] <> 'PRUE' AND p.IdCultivo IS NOT NULL
          AND (p.[IdCampaña] = base.[IdCampaña] OR ca.[Campaña] = LEFT(base.[Campaña], 4) AND LEN(base.[Campaña]) = 9)
        """,
        (id_campania,),
    )
    return superficies_de_lotes(filas)
