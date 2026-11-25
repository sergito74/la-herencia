"""Costos ganaderos (052 FR-003/004/005/021/022, research R1/R2).

Fuentes, sin doble conteo con Agricultura:
1. Compras imputadas a Ganadería por 050 (fracción Directo aprobada vigente, tamiz con destino Ganadería).
2. Compras con centro de costos Ganadería FUERA del alcance de 050 (sin tamiz vigente), salvo las de un destino que es
   cultivo (esas entran por su cultivo). Neto sin IVA, con la parte de la empresa (factor_particular).
3. Forrajes: el costo completo de los cultivos ganaderos (el mismo que el Resultado de cultivos dejó de sumar) más el
   maíz picado para silo, imputados al período de consumo (GanForrajeRegla) o amortizados (pastura, 4 años).
4. Personal permanente (encargado del campo): haberes × % de Ganadería y de Estructura (GanReparto).
US$ siempre con el dólar de gestión único (cotizaciones/dolar_gestion).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from src.db.connection import fetch_all
from src.features.cotizaciones.dolar_gestion import sql_tc_pesos, tc_pesos_cache as tc_pesos
from src.features.ganaderia import periodos

# Importe con signo del renglón (mismo criterio que vw_ResultadosCultivo_CostosBase: NC resta; ND financiera con su signo).
_IMPORTE = """(CASE WHEN ISNULL(d.[Ajuste financiero],0)=1 AND c.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Debito'
                    THEN ISNULL(d.Cantidad,0)*ISNULL(d.[Precio Unitario],0)
               WHEN ISNULL(d.[Ajuste financiero],0)=1 AND c.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Credito'
                    THEN -(ISNULL(d.Cantidad,0)*ISNULL(d.[Precio Unitario],0))
               ELSE ABS(ISNULL(d.Cantidad,0)*ISNULL(d.[Precio Unitario],0)) END
              * CASE WHEN c.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Credito' THEN -1 ELSE 1 END)"""
_PESOS = f"({_IMPORTE} * CASE WHEN c.Moneda='Dolares' THEN ISNULL(c.[Tipo de Cambio],0) ELSE 1 END)"
_USD = (f"CASE WHEN c.Moneda='Dolares' THEN {_IMPORTE} WHEN ISNULL(c.[Ajusta Tipo Cambio],0)=1 THEN 0 "
        f"ELSE {_IMPORTE} / NULLIF({sql_tc_pesos('c.Fecha')},0) END")
_PARTICULAR = "(LOWER(d.[Producto/Servicio]) LIKE '%particular%' AND d.Cantidad * d.[Precio Unitario] < 0)"


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def compras(desde: date, hasta: date) -> list[dict]:
    """Renglones de compra que son costo ganadero, con rubro, en pesos y US$."""
    alcance = fetch_all(
        f"""
        SELECT c.Fecha AS fecha, c.IdDeuda AS idCompra, d.IdDetalleCompra AS idDetalle, d.IdRubro AS idRubro,
               r.Rubro AS rubro, d.[Producto/Servicio] AS item, k.[Razon Social] AS contacto, c.IdContacto AS idContacto,
               c.[Nro Documento] AS documento, p.Importe AS pesos,
               CASE WHEN c.Moneda='Dolares' THEN p.Importe / NULLIF(c.[Tipo de Cambio],0)
                    WHEN ISNULL(c.[Ajusta Tipo Cambio],0)=1 THEN 0
                    ELSE p.Importe / NULLIF({sql_tc_pesos('c.Fecha')},0) END AS usd,
               'Imputación' AS origen
        FROM dbo.ImputacionPropuestas p
        JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = p.IdDetalleCompra AND tz.Vigente = 1 AND tz.Destino = 'Ganaderia'
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = p.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.Rubros r ON r.IdRubro = d.IdRubro
        LEFT JOIN dbo.Contactos k ON k.IdContacto = c.IdContacto
        WHERE p.Origen = 'Directo' AND p.Estado = 'Aprobada' AND p.EsGanaderia = 1
          AND p.IdCorrida = (SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2
                             WHERE p2.IdDetalleCompra = p.IdDetalleCompra AND p2.Origen = p.Origen AND p2.Estado <> 'Reemplazada'
                             ORDER BY p2.FechaCalculo DESC, p2.IdPropuesta DESC)
          AND c.Fecha >= ? AND c.Fecha < DATEADD(day, 1, ?)
        """, (desde, hasta))
    heredado = fetch_all(
        f"""
        SELECT c.Fecha AS fecha, c.IdDeuda AS idCompra, d.IdDetalleCompra AS idDetalle, d.IdRubro AS idRubro,
               r.Rubro AS rubro, d.[Producto/Servicio] AS item, k.[Razon Social] AS contacto, c.IdContacto AS idContacto,
               c.[Nro Documento] AS documento, {_PESOS} AS pesos, {_USD} AS usd, 'Compra' AS origen,
               CASE WHEN EXISTS (SELECT 1 FROM dbo.Det_Compras x WHERE x.IdCompra = c.IdDeuda
                                 AND LOWER(x.[Producto/Servicio]) LIKE '%particular%' AND x.Cantidad * x.[Precio Unitario] < 0)
                    THEN 1 ELSE 0 END AS conParticular
        FROM dbo.Det_Compras d
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.Rubros r ON r.IdRubro = d.IdRubro
        LEFT JOIN dbo.Contactos k ON k.IdContacto = c.IdContacto
        WHERE d.IdCentroCostos = 2 AND NOT {_PARTICULAR}
          AND NOT EXISTS (SELECT 1 FROM dbo.TamizRenglones tz WHERE tz.IdDetalleCompra = d.IdDetalleCompra AND tz.Vigente = 1)
          AND NOT EXISTS (SELECT 1 FROM dbo.Map_CultivoResultado m WHERE m.IdDestino = d.IdDestino AND m.Activo = 1)
          AND c.Fecha >= ? AND c.Fecha < DATEADD(day, 1, ?)
        """, (desde, hasta))
    if any(h["conParticular"] for h in heredado):
        from src.features.imputacion.progresivo import factor_particular

        for h in heredado:
            if h["conParticular"]:
                fac = factor_particular(h["idDetalle"]) or 0.0
                h["pesos"], h["usd"] = _f(h["pesos"]) * fac, _f(h["usd"]) * fac
    for h in heredado:
        h.pop("conParticular", None)
    return alcance + heredado


def _campanias() -> list[dict]:
    return fetch_all("SELECT IdCampaña AS id, Campaña AS nombre FROM dbo.Campañas")


def forrajes(anio_desde: int, anio_hasta: int, vista: str = "ejercicio") -> list[dict]:
    """Costo de forrajes por período de consumo. Pastura: cuota anual (costo / años) desde su campaña.
    Usa el mismo cálculo por cultivo que el Resultado de cultivos (resultado_cultivo.resultado_cultivo)."""
    from src.features.resultado_cultivo.resultado import _cultivos_con_datos, cultivos_ganaderos

    from src.features.resultado_cultivo.resultado import costo_cultivo_para_ganaderia as resultado_cultivo

    reglas = {r["c"]: r for r in fetch_all("SELECT IdCultivo c, Tratamiento t, Anios a, DesfaseEjercicios s FROM dbo.GanForrajeRegla")}
    ganaderos = cultivos_ganaderos()
    con_silo = ganaderos | {1}  # el maíz agrícola puede tener ha picadas para silo
    out = []
    for camp in _campanias():
        a0 = periodos.anio_campania_agricola(camp["nombre"])
        if a0 is None or a0 < anio_desde - 5 or a0 > anio_hasta + 1:
            continue
        for idc in _cultivos_con_datos(camp["id"]):
            if idc not in con_silo:
                continue
            r = _resultado_cultivo_cache(idc, camp["id"], resultado_cultivo)
            silo_p, silo_u = _f(r.get("costoSiloGanaderiaPesos")), _f(r.get("costoSiloGanaderiaDolares"))
            if silo_p or silo_u:  # maíz picado: reserva; sin reserva cargada va entero al período de confección
                out.append({"periodo": a0 + (1 if vista == "ejercicio" else 0), "rubro": "Maíz silo",
                            "cultivo": r["cultivo"], "campania": camp["nombre"], "pesos": silo_p, "usd": silo_u,
                            "detalle": "Picado para silo"})
            if idc not in ganaderos:
                continue
            regla = reglas.get(idc, {"t": "Consumo", "a": 1, "s": 0})
            pesos, usd = _f(r["costoTotalPesos"]), _f(r["costoTotalDolares"])
            if regla["t"] == "Amortiza":
                n = max(int(regla["a"]), 1)
                for k in range(n):
                    out.append({"periodo": a0 + k, "rubro": "Amortización pasturas", "cultivo": r["cultivo"],
                                "campania": camp["nombre"], "pesos": pesos / n, "usd": usd / n,
                                "detalle": f"Cuota {k + 1} de {n}"})
            else:
                out.append({"periodo": a0 + int(regla["s"]), "rubro": r["cultivo"], "cultivo": r["cultivo"],
                            "campania": camp["nombre"], "pesos": pesos, "usd": usd, "detalle": "Costo del cultivo"})
    return [o for o in out if anio_desde <= o["periodo"] <= anio_hasta]


_CACHE_CULTIVO: dict = {}


def _resultado_cultivo_cache(idc: int, idcamp: int, fn) -> dict:
    """El costo por cultivo es caro de calcular (es el del Resultado de cultivos): se guarda 6 horas; el sistema lo
    precalienta al arrancar (precalentar) y el botón "Recalcular" lo vacía (invalidar)."""
    import time

    k = (idc, idcamp)
    v = _CACHE_CULTIVO.get(k)
    if v and time.time() - v[0] < 6 * 3600:
        return v[1]
    r = fn(idc, idcamp)
    _CACHE_CULTIVO[k] = (time.time(), r)
    return r


def invalidar() -> None:
    _CACHE_CULTIVO.clear()


def precalentar(anios: int = 11) -> None:
    """Calcula en segundo plano los forrajes de los últimos `anios` ejercicios."""
    from datetime import date

    hoy = periodos.anio_inicio(date.today())
    forrajes(hoy - anios + 1, hoy, "ejercicio")


def personal_permanente(desde: date, hasta: date) -> dict:
    """Haberes del personal permanente del campo × % del reparto vigente (FR-022)."""
    from src.features.remuneraciones.repository import _CONCEPTOS_HABERES

    rep = fetch_all("SELECT TOP 1 PctGanaderia g, PctEstructura e, PctAgricultura a, IdContacto k FROM dbo.GanReparto "
                    "WHERE Concepto = 'Personal permanente' ORDER BY CASE WHEN Ejercicio IS NULL THEN 1 ELSE 0 END")
    if not rep or rep[0]["k"] is None:
        return {"ganaderia": (0.0, 0.0), "estructura": (0.0, 0.0), "pct": None}
    suma = " + ".join(f"ISNULL(r.{c}, 0)" for c in _CONCEPTOS_HABERES)
    filas = fetch_all(
        f"SELECT r.[Fecha de pago] AS fecha, {suma} AS haberes FROM dbo.Remuneraciones r "
        "WHERE r.IdContacto = ? AND r.[Fecha de pago] >= ? AND r.[Fecha de pago] < DATEADD(day, 1, ?)",
        (rep[0]["k"], desde, hasta))
    pesos = sum(_f(f["haberes"]) for f in filas)
    usd = sum(_f(f["haberes"]) / tc for f in filas if (tc := tc_pesos(f["fecha"])))
    g, e = _f(rep[0]["g"]) / 100, _f(rep[0]["e"]) / 100
    return {"ganaderia": (pesos * g, usd * g), "estructura": (pesos * e, usd * e), "pct": rep[0]}


def agrupar_por_rubro(filas: list[dict], mapa: dict[int, dict]) -> dict:
    """{(grupo, rubroPlanilla): [filas]} según GanRubroMapa; lo que no mapea va a ('Directos', 'Otros: <rubro>')."""
    g = defaultdict(list)
    for f in filas:
        m = mapa.get(f.get("idRubro"))
        clave = (m["grupo"], m["rubro"]) if m else ("Directos", f"Otros: {f.get('rubro') or 'sin rubro'}")
        g[clave].append(f)
    return g
