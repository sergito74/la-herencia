"""Réplica exacta de los formularios Access FrmCostos y FrmResultados (AdmLaHerenciaVer3.accdb), 12/11/2026.

Sergio pidió que Costos y Resultado de cultivo tengan el formato y los cálculos que mostraba Access. La lógica sale
del código VBA de cada formulario (CmdConsulta_Click) y de los mismos objetos SQL que usa Access
(sp_FrmCostos_Resumen / _ImplantacionAgrupado / _DetalleRubro y las vistas vw_ResultadosCultivo_*).
Solo lectura. Única diferencia: la fecha de inicio también mira las órdenes de trabajo nuevas (Ordenes_Trabajo),
que Access no conoce.
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import fetch_all, fetch_one


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def _destino(id_cultivo: int) -> tuple[int, str]:
    fila = fetch_one(
        "SELECT TOP 1 IdDestino AS id, Destino AS nombre FROM dbo.DestinoCompras "
        "WHERE IdCultivo = ? AND ISNULL(Destino, '') <> 'No Aplica' ORDER BY IdDestino", (id_cultivo,))
    if not fila:
        raise ValueError("Este cultivo no está asociado a un destino de compras.")
    return fila["id"], fila["nombre"]


def _campania(id_campania: int) -> str:
    fila = fetch_one("SELECT Campaña AS c FROM dbo.Campañas WHERE IdCampaña = ?", (id_campania,))
    if not fila:
        raise ValueError("Campaña inexistente.")
    return fila["c"]


def _fecha(v) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def _fecha_inicio(id_cultivo: int, id_campania: int, fecha_access) -> date | None:
    nueva = fetch_one(
        "SELECT MIN(o.FechaEjecucion) AS f FROM dbo.Ordenes_Trabajo o "
        "WHERE o.FechaEjecucion IS NOT NULL AND o.Estado <> 'Anulada' AND EXISTS (SELECT 1 FROM dbo.Ordenes_Trabajo_Distrib d "
        "JOIN dbo.Ordenes_Trabajo_Insumos i ON i.IdOrdenInsumo = d.IdOrdenInsumo "
        "WHERE i.IdOrdenTrabajo = o.IdOrdenTrabajo AND d.IdCultivo = ? AND d.IdCampania = ?)", (id_cultivo, id_campania))
    fechas = [x for x in (_fecha(fecha_access), _fecha((nueva or {}).get("f"))) if x]
    return min(fechas) if fechas else None


def campanias_de_cultivo(id_cultivo: int) -> list[dict]:
    """Combo Campaña de Access: campañas con ese cultivo en la planificación."""
    return fetch_all(
        "SELECT DISTINCT C.IdCampaña AS idCampania, C.Campaña AS campania FROM dbo.PlanAgricola P "
        "JOIN dbo.Campañas C ON C.IdCampaña = P.IdCampaña WHERE P.IdCultivo = ? AND ISNULL(C.Campaña, '') <> 'No Aplica' "
        "ORDER BY C.Campaña DESC", (id_cultivo,))


def superficie_sembrada_real(id_destino: int, id_campania: int) -> float | None:
    """Superficie realmente sembrada según las facturas de siembra (12/11/2026, reglas de Sergio):
    - mismo contratista con varias facturas del mismo cultivo/campaña: se toma la mayor (la otra suele ser un adelanto
      financiero que repite la superficie); contratistas distintos se suman;
    - dentro de una factura se suman sus líneas, salvo la misma superficie repetida para el mismo lote
      ("c/sembradora propia"), resiembras, diferencias de cambio, ajustes financieros y notas de crédito/débito.
    None si no hay factura de siembra (se muestra la superficie planificada como teórica)."""
    import re

    filas = fetch_all(
        "SELECT c.IdDeuda AS compra, c.IdContacto AS contratista, dc.Cantidad AS ha, dc.[Producto/Servicio] AS item "
        "FROM dbo.Det_Compras dc JOIN dbo.Compras c ON c.IdDeuda = dc.IdCompra JOIN dbo.Rubros r ON r.IdRubro = dc.IdRubro "
        "WHERE r.Rubro = 'Siembra' AND dc.IdDestino = ? AND dc.IdCampaña = ? AND ISNULL(dc.[Ajuste financiero], 0) = 0 "
        "AND c.[Tipo documento] NOT LIKE 'Nota de%' AND ISNULL(dc.Cantidad, 0) > 0", (id_destino, id_campania))
    por_factura: dict[tuple, dict] = {}
    for f in filas:
        item = (f["item"] or "").lower()
        if "resiembra" in item or "dif" in item and "cambio" in item:
            continue
        lote = re.search(r"\(([^)]*)\)", item)
        clave = (lote.group(1).strip() if lote else item.replace("c/sembradora propia", "").strip(), round(_f(f["ha"]), 2))
        lineas = por_factura.setdefault((f["contratista"], f["compra"]), {})
        lineas[clave] = _f(f["ha"])  # misma superficie del mismo lote repetida en la factura: cuenta una vez
    # Siembra con maquinaria propia ([Labores Maquinaria propia], 2018/19 en adelante): también es superficie sembrada.
    propia = {str(f["lote"]).strip().upper(): _f(f["ha"]) for f in fetch_all(
        "SELECT Lote AS lote, SUM(Superficie) AS ha FROM dbo.[Labores Maquinaria propia] "
        "WHERE Labor LIKE 'Siembra%' AND IdDestino = ? AND IdCampaña = ? GROUP BY Lote", (id_destino, id_campania))}
    if not por_factura and not propia:
        return None
    por_contratista: dict = {}
    por_lote: dict[str, float] = dict(propia)
    for (contratista, _), lineas in por_factura.items():
        sin_lote = 0.0
        for (lote, _), ha in lineas.items():
            codigo = re.match(r"\s*(\d+[a-z]*)", lote)
            if codigo and len(lote) <= 12:  # factura con el lote indicado: un mismo lote no se cuenta dos veces
                k = codigo.group(1).upper()
                por_lote[k] = max(por_lote.get(k, 0.0), ha)
            else:
                sin_lote += ha
        if sin_lote:
            por_contratista[contratista] = max(por_contratista.get(contratista, 0.0), sin_lote)
    return round(sum(por_contratista.values()) + sum(por_lote.values()), 1)


# ------------------------------------------------------------------ FrmCostos

# Cosecha agrupa tres rubros (igual que los procedimientos de Access).
# 17/11/2026: un solo cálculo de costo. Las pantallas con formato Access agrupan las líneas de costos.lineas_clasificadas
# (el mismo costo que usa el resto del sistema: órdenes de trabajo, contratistas, imputación 050, caja y compras), con las
# mismas fórmulas de FrmCostos / FrmResultados. Antes leían solo la vista heredada y daban otro número.
_COSECHA_RUBROS = (12, 2047893500, 2047893473)


def _grupo(l: dict) -> tuple[int, str]:
    if l.get("idRubro") in _COSECHA_RUBROS:
        return 12, "Cosecha"
    return l.get("idRubro") or 0, l.get("rubroNombre") or "Sin rubro"


def _es_implantacion(l: dict) -> bool:
    return l.get("clasif") == 1 or l.get("origen") == "MaquinariaPropia"


def _lineas(id_cultivo: int, id_campania: int) -> list[dict]:
    from src.features.resultado_cultivo import costos as _costos
    return _costos.lineas_clasificadas(id_cultivo, id_campania)


def _sumar(lineas) -> tuple[float, float]:
    return sum(_f(l.get("montoPesos")) for l in lineas), sum(_f(l.get("montoDolares")) for l in lineas)


def _agrupar(lineas) -> list[dict]:
    g: dict[tuple, list] = {}
    for l in lineas:
        g.setdefault(_grupo(l), []).append(l)
    out = []
    for (id_rubro, concepto), ls in sorted(g.items(), key=lambda kv: kv[0][1]):
        p_, d_ = _sumar(ls)
        out.append({"idRubro": id_rubro, "concepto": concepto, "pesos": p_, "dolares": d_})
    return out


_GRUPO_RUBRO = "CASE WHEN B.IdRubro IN (12, 2047893500, 2047893473) THEN 12 ELSE B.IdRubro END"
_GRUPO_CONCEPTO = "CASE WHEN B.IdRubro IN (12, 2047893500, 2047893473) THEN 'Cosecha' ELSE B.Concepto END"

def formulario_costos(id_cultivo: int, id_campania: int) -> dict:
    id_destino, cultivo = _destino(id_cultivo)
    campania = _campania(id_campania)
    # Superficie, fecha de inicio y picado como dbo.sp_FrmCostos_Resumen; los importes, del cálculo único.
    r = fetch_one(
        "SELECT (SELECT SUM(L.Superficie) FROM dbo.Lotes L JOIN (SELECT DISTINCT P.IdLote FROM dbo.PlanAgricola P "
        "  WHERE P.IdCultivo = ? AND P.IdCampaña = ?) X ON L.IdLote = X.IdLote) AS Superficie, "
        "(SELECT MIN(O.[Fecha Ejecucion]) FROM dbo.Ordenes O JOIN dbo.Ordenes_Lotes OL ON O.IdOrden = OL.IdOrden "
        "  WHERE OL.IdCultivo = ? AND OL.IdCampaña = ? AND O.[Fecha Ejecucion] IS NOT NULL) AS FechaInicio, "
        "(SELECT SUM(DC.Cantidad) FROM dbo.Det_Compras DC JOIN dbo.Rubros R ON DC.IdRubro = R.IdRubro "
        "  WHERE R.Rubro = 'Confeccion Silo' AND DC.IdDestino = ? AND DC.IdCampaña = ? AND ISNULL(DC.[Ajuste financiero], 0) = 0) AS SupPicado",
        (id_cultivo, id_campania, id_cultivo, id_campania, id_destino, id_campania)) or {}
    lineas = _lineas(id_cultivo, id_campania)
    impl_lineas = [l for l in lineas if _es_implantacion(l)]
    r["TotalImplPesos"], r["TotalImplDolares"] = _sumar(impl_lineas)
    r["TotalSiloPesos"], r["TotalSiloDolares"] = _sumar([l for l in lineas if l.get("rubroNombre") == "Confeccion Silo"])
    r["TotalCosechaPesos"], r["TotalCosechaDolares"] = _sumar([l for l in lineas if l.get("idRubro") in _COSECHA_RUBROS])
    sup = _f(r.get("Superficie"))
    base = {"cultivo": cultivo, "campania": campania, "idCultivo": id_cultivo, "idCampania": id_campania}
    if sup <= 0:
        return {**base, "sinSuperficie": True}
    picado = min(max(_f(r.get("SupPicado")), 0.0), sup)
    cosechada = round(_f((fetch_one("SELECT SuperficieCosechada AS s FROM dbo.ResultadoCultivo_Cierre WHERE IdCultivo = ? AND IdCampaña = ?",
                                    (id_cultivo, id_campania)) or {}).get("s")), 1)
    grano = sup - picado
    impl_p, impl_d = _f(r.get("TotalImplPesos")), _f(r.get("TotalImplDolares"))
    silo_p, silo_d = _f(r.get("TotalSiloPesos")), _f(r.get("TotalSiloDolares"))
    cos_p, cos_d = _f(r.get("TotalCosechaPesos")), _f(r.get("TotalCosechaDolares"))
    impl_ha_p, impl_ha_d = impl_p / sup, impl_d / sup
    grano_p = impl_p - impl_ha_p * picado + cos_p
    grano_d = impl_d - impl_ha_d * picado + cos_d
    # = dbo.sp_FrmCostos_ImplantacionAgrupado, sobre el cálculo único.
    filas = [{"IdRubroGrupo": g["idRubro"], "Concepto": g["concepto"], "Pesos": g["pesos"], "Dolares": g["dolares"],
              "CostoHAPesos": round(g["pesos"] / sup, 2), "CostoHADolares": round(g["dolares"] / sup, 2)}
             for g in _agrupar(impl_lineas)]
    return {
        **base,
        "sinSuperficie": False,
        "fechaInicio": _fecha_inicio(id_cultivo, id_campania, r.get("FechaInicio")),
        "superficieAfectada": round(sup, 1),
        "superficieSembrada": max(real, cosechada) if (real := superficie_sembrada_real(id_destino, id_campania)) is not None else round(grano, 1),
        "superficieSembradaTeorica": real is None,
        "superficieSembradaSegunCosecha": real is not None and cosechada > real,
        "superficiePicada": round(picado, 1),
        "costosDirectos": [
            {"idRubro": f["IdRubroGrupo"], "concepto": f["Concepto"], "pesos": _f(f["Pesos"]), "dolares": _f(f["Dolares"]),
             "haPesos": _f(f["CostoHAPesos"]), "haDolares": _f(f["CostoHADolares"])}
            for f in filas
        ],
        "implantacion": {"pesos": round(impl_p), "dolares": round(impl_d), "haPesos": round(impl_ha_p), "haDolares": round(impl_ha_d)},
        "silo": {"pesos": round(impl_ha_p * picado + silo_p), "dolares": round(impl_ha_d * picado + silo_d)},
        "total": {"pesos": round(grano_p), "dolares": round(grano_d),
                  "haPesos": round(grano_p / grano) if grano > 0 else 0, "haDolares": round(grano_d / grano) if grano > 0 else 0},
    }


def detalle_rubro(id_cultivo: int, id_campania: int, id_rubro: int) -> list[dict]:
    """Subformulario "Detalles Costos" de Access (al hacer clic en un concepto), sobre el cálculo único."""
    out = []
    for l in _lineas(id_cultivo, id_campania):
        if _grupo(l)[0] != id_rubro:
            continue
        q = _f(l.get("cantidad"))
        p_, d_ = _f(l.get("montoPesos")), _f(l.get("montoDolares"))
        out.append({"cantidad": q, "producto": l.get("item") or l.get("rubroNombre"),
                    "unitarioPesos": p_ / q if q else None, "unitarioDolares": d_ / q if q else None,
                    "totalPesos": p_, "totalDolares": d_})
    return out


# ------------------------------------------------------------------ FrmResultados

def formulario_resultados(id_cultivo: int, id_campania: int) -> dict:
    id_destino, cultivo = _destino(id_cultivo)
    camp = _campania(id_campania)
    base = {"cultivo": cultivo, "campania": camp, "idCultivo": id_cultivo, "idCampania": id_campania}

    ini_access = (fetch_one(
        "SELECT MIN(O.[Fecha Ejecucion]) AS f FROM dbo.Ordenes O JOIN dbo.Ordenes_Lotes OL ON O.IdOrden = OL.IdOrden "
        "WHERE OL.IdCultivo = ? AND OL.IdCampaña = ? AND O.[Fecha Ejecucion] IS NOT NULL", (id_cultivo, id_campania)) or {}).get("f")
    fecha_inicio = _fecha_inicio(id_cultivo, id_campania, ini_access)
    sup = _f((fetch_one(
        "SELECT SUM(L.Superficie) AS s FROM dbo.Lotes L JOIN (SELECT DISTINCT P.IdLote FROM dbo.PlanAgricola P "
        "WHERE P.IdCultivo = ? AND P.IdCampaña = ?) X ON L.IdLote = X.IdLote", (id_cultivo, id_campania)) or {}).get("s"))
    if fecha_inicio is None:
        return {**base, "aviso": f"No hay órdenes con fecha de ejecución para {cultivo} {camp}."}
    if sup <= 0:
        return {**base, "aviso": f"No hay superficie planificada para {cultivo} {camp}."}

    sup_cosecha = _f((fetch_one("SELECT SuperficieCosechada AS s FROM dbo.ResultadoCultivo_Cierre WHERE IdCultivo = ? AND IdCampaña = ?",
                                (id_cultivo, id_campania)) or {}).get("s"))
    sup_picado = 0.0
    if cultivo in ("Maiz", "Maiz diferido", "Sorgo"):
        sup_picado = _f((fetch_one(
            "SELECT SUM(DC.Cantidad) AS s FROM dbo.Det_Compras DC JOIN dbo.Rubros R ON DC.IdRubro = R.IdRubro "
            "WHERE R.Rubro = 'Confeccion Silo' AND DC.IdDestino = ? AND DC.IdCampaña = ? AND ISNULL(DC.[Ajuste financiero], 0) = 0",
            (id_destino, id_campania)) or {}).get("s"))
    cos = fetch_one("SELECT SUM([Cantidad a Liquidar]) AS c, MAX(Fecha) AS f FROM dbo.[Datos Cosecha] WHERE IdDestino = ? AND IdCampaña = ?",
                    (id_destino, id_campania)) or {}
    cant_cosecha = _f(cos.get("c"))
    fecha_fin = _fecha(cos.get("f"))
    cant_venta = _f((fetch_one(
        "SELECT SUM(VG.[Cantidad vendida]) AS c FROM dbo.Granos G JOIN dbo.[Venta Granos] VG ON G.IdGrano = VG.IdProducto "
        "WHERE G.Grano = ? AND VG.Campaña = ?", (cultivo, camp)) or {}).get("c"))
    v = fetch_one("SELECT * FROM dbo.vw_ResultadosCultivo_Ventas WHERE IdCultivo = ? AND Campaña = ?", (id_cultivo, camp)) or {}
    venta_p, venta_d = _f(v.get("VentaPesos")), _f(v.get("VentaDolares"))
    bonif_p, bonif_d = _f(v.get("BonifPesos")), _f(v.get("BonifDolares"))

    duracion = (fecha_fin - fecha_inicio).days if fecha_fin else 0
    rinde = round(cant_cosecha / sup_cosecha) if sup_cosecha > 0 else 0
    tot_vta_p, tot_vta_d = round(venta_p + bonif_p, 2), round(venta_d + bonif_d, 2)

    lineas = _lineas(id_cultivo, id_campania)
    costos_directos = [{**g, "haPesos": g["pesos"] / sup, "haDolares": g["dolares"] / sup}
                       for g in _agrupar([l for l in lineas if l.get("clasif") == 1])]
    impl_p = sum(c["pesos"] for c in costos_directos)
    impl_d = sum(c["dolares"] for c in costos_directos)
    impl_ha_p = sum(c["haPesos"] for c in costos_directos)
    impl_ha_d = sum(c["haDolares"] for c in costos_directos)

    cos_p, cos_d = _sumar([l for l in lineas if l.get("clasif") == 2])
    cos_ha_p = cos_p / sup_cosecha if sup_cosecha > 0 else 0.0
    cos_ha_d = cos_d / sup_cosecha if sup_cosecha > 0 else 0.0

    deducciones = [{"detalle": d["Detalle"], "pesos": _f(d["Pesos"]), "dolares": _f(d["Dolares"])} for d in fetch_all(
        "SELECT Detalle, Pesos, Dolares FROM dbo.vw_ResultadosCultivo_Deducciones WHERE IdCultivo = ? AND Campaña = ? ORDER BY Detalle",
        (id_cultivo, camp))]
    gastos = [{"concepto": g["concepto"], "pesos": g["pesos"], "dolares": g["dolares"]}
              for g in _agrupar([l for l in lineas if l.get("clasif") == 4])]
    desc_p = sum(x["pesos"] for x in deducciones) + sum(x["pesos"] for x in gastos)
    desc_d = sum(x["dolares"] for x in deducciones) + sum(x["dolares"] for x in gastos)
    s = fetch_one("SELECT SeguroPesos, SeguroDolares FROM dbo.vw_ResultadosCultivo_Seguros WHERE IdDestino = ? AND IdCampaña = ?",
                  (id_destino, id_campania)) or {}
    seg_p, seg_d = _f(s.get("SeguroPesos")), _f(s.get("SeguroDolares"))

    consumo_p = consumo_d = precio_tn = 0.0
    if cant_venta > 0:
        precio_tn = round((tot_vta_d - desc_d) / cant_venta * 1000, 2)
        if cant_cosecha - cant_venta > 0:
            consumo_d = round((cant_cosecha - cant_venta) / 1000 * precio_tn, 2)
            consumo_p = round(consumo_d * (tot_vta_p / tot_vta_d), 2) if tot_vta_d else 0.0

    silo_p = impl_p / sup * sup_picado
    silo_d = impl_d / sup * sup_picado
    total_p = round(impl_p - silo_p + cos_p)
    total_d = round(impl_d - silo_d + cos_d)
    neta_p = tot_vta_p - desc_p + seg_p + consumo_p
    neta_d = tot_vta_d - desc_d + seg_d + consumo_d
    mb_p, mb_d = round(neta_p - total_p, 2), round(neta_d - total_d, 2)
    rent_p = round(mb_p / total_p, 4) if total_p else 0.0
    rent_d = round(mb_d / total_d, 4) if total_d else 0.0
    rinde_indif = round((total_d / sup_cosecha) / precio_tn * 1000) if precio_tn > 0 and sup_cosecha > 0 else 0

    return {
        **base,
        "aviso": None,
        "fechaInicio": fecha_inicio, "fechaFin": fecha_fin, "ocupacionDias": duracion if duracion > 0 else None,
        "superficieAfectada": round(sup, 1), "superficieCosechada": sup_cosecha,
        # No se puede cosechar más de lo sembrado (Sergio 12/11/2026): si la cosecha supera los registros de siembra, manda la cosecha.
        "superficieSembrada": max(real, round(sup_cosecha, 1)) if (real := superficie_sembrada_real(id_destino, id_campania)) is not None else round(sup, 1),
        "superficieSembradaTeorica": real is None,
        "superficieSembradaSegunCosecha": real is not None and sup_cosecha > real, "superficiePicada": sup_picado,
        "cantidadCosechada": round(cant_cosecha), "cantidadVendida": round(cant_venta), "cantidadConsumida": round(cant_cosecha - cant_venta),
        "rinde": rinde, "rindeIndiferencia": rinde_indif, "volumenIndiferencia": round(rinde_indif * sup_cosecha),
        "margenBruto": {"pesos": mb_p, "dolares": mb_d},
        "margenBrutoHa": {"pesos": round(mb_p / sup, 2), "dolares": round(mb_d / sup, 2)},
        "rentabilidad": {"pesos": rent_p, "dolares": rent_d},
        "rentaAnual": {"pesos": round(rent_p * 365 / duracion, 4) if duracion > 0 else 0.0,
                       "dolares": round(rent_d * 365 / duracion, 4) if duracion > 0 else 0.0},
        "precioNetoTn": precio_tn,
        "costosDirectos": costos_directos,
        "implantacion": {"pesos": round(impl_p, 2), "dolares": round(impl_d, 2), "haPesos": round(impl_ha_p, 2), "haDolares": round(impl_ha_d, 2)},
        "silo": {"pesos": round(silo_p, 2), "dolares": round(silo_d, 2)},
        "cosecha": {"pesos": round(cos_p, 2), "dolares": round(cos_d, 2), "haPesos": round(cos_ha_p, 2), "haDolares": round(cos_ha_d, 2)},
        "totalCostos": {"pesos": total_p, "dolares": total_d,
                        "haPesos": round(impl_ha_p + cos_ha_p, 2), "haDolares": round(impl_ha_d + cos_ha_d, 2)},
        "ventaBruta": {"pesos": venta_p, "dolares": venta_d},
        "bonificaciones": {"pesos": bonif_p, "dolares": bonif_d},
        "totalVentas": {"pesos": tot_vta_p, "dolares": tot_vta_d},
        "deducciones": deducciones,
        "gastos": gastos,
        "totalDeducciones": {"pesos": desc_p, "dolares": desc_d},
        "recuperoSeguro": {"pesos": seg_p, "dolares": seg_d},
        "produccionNoComercializada": {"pesos": consumo_p, "dolares": consumo_d},
        "totalVentaNeta": {"pesos": neta_p, "dolares": neta_d},
    }
