"""Hectáreas ganaderas efectivas (052 FR-013, research R3). Método de Sergio (Superficie Campo.xlsx, "Sup Ganadera 2011"):
cada lote cuenta por los meses del período en que está en uso ganadero, sobre 12. Un lote es agrícola desde la siembra
hasta la cosecha de un cultivo agrícola del Plan; el resto del año (rastrojo, verdeo, pastura, campo natural) es ganadero.
Sin fechas reales se usa el calendario típico del cultivo (GanCalendarioCultivo). Un ajuste manual por lote y período
(GanSuperficieAjuste) reemplaza el cálculo, con motivo.
"""

from __future__ import annotations

from src.features.ganaderia import periodos


def ventana(anio_campania: int, mes_desde: int, mes_hasta: int) -> set[tuple[int, int]]:
    """Meses (año, mes) fuera de pastoreo de un cultivo de la campaña 'anio/anio+1'. La siembra de junio en adelante es
    del primer año (trigo jun–dic, soja 1.ª nov–abr); antes de junio, del segundo (soja 2.ª ene–abr)."""
    y = anio_campania if mes_desde >= 6 else anio_campania + 1
    out, m = set(), mes_desde
    while True:
        out.add((y, m))
        if m == mes_hasta:
            return out
        m += 1
        if m == 13:
            m, y = 1, y + 1


def meses_ganaderos(meses_periodo: list[tuple[int, int]], ventanas_agricolas: list[set[tuple[int, int]]]) -> int:
    ocupados = set().union(*ventanas_agricolas) if ventanas_agricolas else set()
    return sum(1 for m in meses_periodo if m not in ocupados)


def calcular(total_ha: float | None, ha_fijas: float | None, lotes: list[dict], plan: list[dict],
             calendario: dict[int, tuple[int, int]], ajustes: dict, anio: int, vista: str = "ejercicio") -> dict:
    """Función pura (Sergio 25/11/2026).
    - Período con ha fijas (antes de 2021/22: las de su planilla histórica) → esas.
    - Si no: ha efectivas = total del campo (loteo vigente) − Σ superficie de cada lote con cultivo agrícola × meses
      ocupados / 12. Cada lote cuenta una vez por mes aunque tenga dos cultivos (trigo y soja 2.ª).
    lotes: [{idLote, lote, superficie}]; plan: [{idLote, idCultivo, anioCampania, agricola}];
    calendario: {idCultivo: (mesDesde, mesHasta)}; ajustes: {(idLote, etiqueta): (meses ganaderos, motivo)}."""
    mp = periodos.meses(anio, vista)
    clave = periodos.etiqueta(anio)
    if ha_fijas is not None:
        return {"haEfectivas": round(float(ha_fijas), 2), "totalHa": None, "origen": "planilla", "lotesAgricolas": []}
    detalle, descuento = [], 0.0
    sup = {l["idLote"]: (l["lote"], float(l["superficie"] or 0)) for l in lotes}
    for id_lote, (nombre, ha) in sup.items():
        aj = ajustes.get((id_lote, clave))
        vents = [ventana(p["anioCampania"], *calendario[p["idCultivo"]]) for p in plan
                 if p["idLote"] == id_lote and p["agricola"] and p["idCultivo"] in calendario and p["anioCampania"] is not None]
        if aj:
            ocupados = 12 - float(aj[0])
        elif vents:
            ocupados = 12 - meses_ganaderos(mp, vents)
        else:
            continue
        if ocupados <= 0:
            continue
        descuento += ha * ocupados / 12
        detalle.append({"idLote": id_lote, "lote": nombre, "superficie": round(ha, 2), "mesesAgricolas": ocupados,
                        "haDescontadas": round(ha * ocupados / 12, 2), "origen": "ajuste" if aj else "plan",
                        "motivo": aj[1] if aj else None})
    total = float(total_ha or 0)
    return {"haEfectivas": round(max(total - descuento, 0.0), 2) if total_ha else None, "totalHa": total_ha,
            "origen": "plan", "lotesAgricolas": sorted(detalle, key=lambda d: d["lote"])}


def superficie(anio: int, vista: str = "ejercicio") -> dict:
    from src.db.connection import fetch_all

    base = fetch_all("SELECT TOP 1 TotalHa t, HaGanaderasFijas f, Fuente fu FROM dbo.GanSuperficieCampo "
                     "WHERE AnioDesde <= ? AND (AnioHasta IS NULL OR AnioHasta >= ?) ORDER BY AnioDesde DESC", (anio, anio))
    b = base[0] if base else {"t": None, "f": None, "fu": None}
    lotes = fetch_all("SELECT IdLote AS idLote, [Numero Lote] AS lote, Superficie AS superficie FROM dbo.Lotes "
                      "WHERE [Numero Lote] <> 'PRUE'")
    plan = fetch_all(
        "SELECT p.IdLote AS idLote, p.IdCultivo AS idCultivo, ca.Campaña AS campania, "
        "CASE WHEN ISNULL(m.EsGanaderia, 0) = 0 AND p.IdCultivo <> 10 THEN 1 ELSE 0 END AS agricola "
        "FROM dbo.PlanAgricola p JOIN dbo.Campañas ca ON ca.IdCampaña = p.IdCampaña "
        "LEFT JOIN dbo.Map_CultivoResultado m ON m.IdCultivo = p.IdCultivo")
    for p in plan:
        p["anioCampania"] = periodos.anio_campania_agricola(p["campania"])
    calendario = {r["c"]: (int(r["d"]), int(r["h"])) for r in fetch_all(
        "SELECT IdCultivo c, MesDesde d, MesHasta h FROM dbo.GanCalendarioCultivo")}
    ajustes = {(r["l"], r["e"]): (r["m"], r["mo"]) for r in fetch_all(
        "SELECT IdLote l, Ejercicio e, MesesGanaderos m, Motivo mo FROM dbo.GanSuperficieAjuste")}
    r = calcular(b["t"], b["f"], lotes, plan, calendario, ajustes, anio, vista)
    return {"periodo": periodos.etiqueta(anio), "fuente": b["fu"], **r}
