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


def calcular(lotes: list[dict], plan: list[dict], calendario: dict[int, tuple[int, int]], ajustes: dict,
             anio: int, vista: str = "ejercicio") -> list[dict]:
    """Función pura. lotes: [{idLote, lote, superficie}]; plan: [{idLote, idCultivo, anioCampania, agricola}];
    calendario: {idCultivo: (mesDesde, mesHasta)}; ajustes: {(idLote, etiqueta): (meses, motivo)}."""
    mp = periodos.meses(anio, vista)
    clave = periodos.etiqueta(anio)
    out = []
    for lote in lotes:
        aj = ajustes.get((lote["idLote"], clave))
        if aj:
            meses, origen, motivo = float(aj[0]), "ajuste", aj[1]
        else:
            vents = [ventana(p["anioCampania"], *calendario[p["idCultivo"]]) for p in plan
                     if p["idLote"] == lote["idLote"] and p["agricola"] and p["idCultivo"] in calendario
                     and p["anioCampania"] is not None]
            meses, motivo = float(meses_ganaderos(mp, vents)), None
            origen = "plan" if vents else "ganadero todo el año"
        sup = float(lote["superficie"] or 0)
        out.append({"idLote": lote["idLote"], "lote": lote["lote"], "superficie": round(sup, 2), "mesesGanaderos": meses,
                    "haEfectivas": round(sup * meses / 12, 2), "origen": origen, "motivo": motivo})
    return out


def superficie(anio: int, vista: str = "ejercicio") -> dict:
    from src.db.connection import fetch_all

    lotes = fetch_all("SELECT IdLote AS idLote, [Numero Lote] AS lote, Superficie AS superficie FROM dbo.Lotes "
                      "WHERE [Numero Lote] <> 'PRUE' ORDER BY [Numero Lote]")
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
    filas = calcular(lotes, plan, calendario, ajustes, anio, vista)
    return {"periodo": periodos.etiqueta(anio), "lotes": filas,
            "haEfectivas": round(sum(f["haEfectivas"] for f in filas), 2),
            "superficieTotal": round(sum(f["superficie"] for f in filas), 2),
            "sinPlan": not any(p["anioCampania"] in (anio - 1, anio, anio + 1) for p in plan)}
