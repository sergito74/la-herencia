"""Resultado ganadero por período (052 FR-002/012/020, US1).

Estructura (estándar CREA/INTA, revisión de especialistas 25/11/2026):
  Ventas brutas por categoría (A contable + B Complemento) − Comercialización = Ventas netas
  − Compras de hacienda ± Diferencia de inventario = INGRESO NETO   (sin stock valuado: "sin variación de inventario")
  + Pastaje cobrado − Directos − Sanidad − Alimentación (forrajes, silo, alimento, pastaje pagado) = MARGEN BRUTO
  − Estructura (sin repartir) = RESULTADO OPERATIVO
Vista "campania" (jul–jun, la de la planilla histórica) = margen de caja, sin variación de inventario.
"""

from __future__ import annotations

from collections import defaultdict

from src.db.connection import fetch_all
from src.features.cotizaciones.dolar_gestion import FUENTE, tc_pesos_cache as tc_pesos
from src.features.ganaderia import categorias, costos, periodos, superficie

GRUPOS = ("Ventas", "Comercializacion", "CompraHacienda", "Inventario", "Pastaje", "Directos", "Sanidad",
          "Alimentacion", "Estructura")
TITULOS = {"Ventas": "Ventas brutas", "Comercializacion": "Gastos de comercialización", "CompraHacienda": "Compras de hacienda",
           "Inventario": "Diferencia de inventario", "Pastaje": "Pastaje cobrado", "Directos": "Costos directos",
           "Sanidad": "Sanidad e inseminación", "Alimentacion": "Alimentación y forrajes", "Estructura": "Estructura"}


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def ventas(desde, hasta, establecimiento: int | None = None) -> list[dict]:
    """Renglones de venta (A y B por renglón) y gastos de comercialización por liquidación, en pesos y US$."""
    filas = fetch_all(
        """
        SELECT v.IdVenta AS idVenta, v.Fecha AS fecha, v.[Nro documento] AS documento, k.[Razon Social] AS contacto,
               v.IdConsignatario AS idContacto, v.IdEstableciemiento AS idEstablecimiento,
               t.[Tipo de Hacienda] AS categoria, g.PesoTipicoKg AS pesoTipico, d.Cantidad AS cantidad,
               d.[Unidad de medida] AS unidad, d.[Peso Total] AS pesoTotal,
               ISNULL(d.Cantidad,0) * ISNULL(d.[Precio unitario (A)],0) AS importeA,
               ISNULL(d.Cantidad,0) * ISNULL(d.[Precio unitario (B)],0) AS importeB
        FROM dbo.[Det_Ventas Hacienda] d
        JOIN dbo.[Venta Hacienda] v ON v.IdVenta = d.IdVenta
        LEFT JOIN dbo.[Tipo Hacienda] t ON t.IdTipoHacienda = d.IdTipoProducto
        LEFT JOIN (SELECT IdTipoHacienda, MIN(PesoTipicoKg) PesoTipicoKg FROM dbo.GanCategoria GROUP BY IdTipoHacienda) g
               ON g.IdTipoHacienda = d.IdTipoProducto
        LEFT JOIN dbo.Contactos k ON k.IdContacto = v.IdConsignatario
        WHERE v.Fecha >= ? AND v.Fecha < DATEADD(day, 1, ?) AND (? IS NULL OR v.IdEstableciemiento = ?)
        """, (desde, hasta, establecimiento, establecimiento))
    cab = fetch_all(
        """
        SELECT v.IdVenta AS idVenta, v.Fecha AS fecha, v.[Nro documento] AS documento, k.[Razon Social] AS contacto,
               ISNULL(v.[Porc Comision],0) AS pc, ISNULL(v.[Vis Municipal],0) + ISNULL(v.Balanza,0) AS municipal,
               ISNULL(v.[Gs Vs No Gravados],0) + ISNULL(v.[Gastos Varios],0) AS varios, ISNULL(v.[Ley de Sellos],0) AS sellos,
               ISNULL(v.Flete,0) AS flete, ISNULL(v.[Ingresos Brutos],0) AS iibb, ISNULL(v.Complemento,0) AS complemento
        FROM dbo.[Venta Hacienda] v LEFT JOIN dbo.Contactos k ON k.IdContacto = v.IdConsignatario
        WHERE v.Fecha >= ? AND v.Fecha < DATEADD(day, 1, ?) AND (? IS NULL OR v.IdEstableciemiento = ?)
        """, (desde, hasta, establecimiento, establecimiento))
    bruto = defaultdict(float)
    for f in filas:
        bruto[f["idVenta"]] += _f(f["importeA"]) + _f(f["importeB"])
        f.update(categorias.cabezas_y_kg(f["cantidad"], f["unidad"], f["pesoTotal"], _f(f["pesoTipico"]) or None))
    gastos = []
    for c in cab:
        comision = bruto[c["idVenta"]] * _f(c["pc"]) / 100
        total = comision + _f(c["municipal"]) + _f(c["varios"]) + _f(c["sellos"]) + _f(c["flete"]) + _f(c["iibb"])
        gastos.append({**c, "comision": comision, "gastos": total})
    return filas, gastos


def _usd(pesos, fecha) -> float:
    tc = tc_pesos(fecha)
    return _f(pesos) / tc if tc else 0.0


def _pastaje(desde, hasta, establecimiento: int | None = None) -> list[dict]:
    return fetch_all(
        "SELECT p.Fecha AS fecha, p.Numero AS documento, k.[Razon Social] AS contacto, "
        "CASE WHEN p.Tipo = 'nota_credito' THEN -p.Neto ELSE p.Neto END AS pesos "
        "FROM dbo.PastajeComprobantes p LEFT JOIN dbo.ContratosPastaje cp ON cp.IdContratoPastaje = p.IdContratoPastaje "
        "LEFT JOIN dbo.Contactos k ON k.IdContacto = cp.IdContactoCliente "
        "WHERE p.Estado = 'vigente' AND p.Fecha >= ? AND p.Fecha < DATEADD(day, 1, ?) "
        "AND (? IS NULL OR p.IdEstablecimiento = ?)", (desde, hasta, establecimiento, establecimiento))


def _mapa_rubros() -> dict[int, dict]:
    return {r["idRubro"]: {"grupo": r["grupo"], "rubro": r["rubro"], "orden": r["orden"]} for r in fetch_all(
        "SELECT IdRubro AS idRubro, Grupo AS grupo, RubroPlanilla AS rubro, Orden AS orden FROM dbo.GanRubroMapa "
        "WHERE IdRubro IS NOT NULL")}


def periodo(anio: int, vista: str = "ejercicio", forrajes_cache: list | None = None,
            establecimiento: int | None = None) -> dict:
    """Celdas {(grupo, rubro): {pesos, usd, detalle: [...]}} e indicadores de un período."""
    desde, hasta = periodos.rango(anio, vista)
    celdas: dict = defaultdict(lambda: {"pesos": 0.0, "usd": 0.0, "detalle": []})

    def suma(grupo, rubro, pesos, usd, det):
        c = celdas[(grupo, rubro)]
        c["pesos"] += _f(pesos)
        c["usd"] += _f(usd)
        c["detalle"].append(det)

    renglones, gastos = ventas(desde, hasta, establecimiento)
    kg_vendidos, cab_vendidas = 0.0, 0
    for r in renglones:
        if not r["esHacienda"]:  # renglón en pesos: ajuste de la liquidación, suma a la venta como en la planilla
            suma("Ventas", "Ajustes de liquidación", r["importeA"], _usd(r["importeA"], r["fecha"]), _det(r, r["importeA"]))
            continue
        cat = r["categoria"] or "Sin categoría"
        suma("Ventas", f"{cat} (A)", r["importeA"], _usd(r["importeA"], r["fecha"]), _det(r, r["importeA"]))
        if _f(r["importeB"]):
            suma("Ventas", f"{cat} (B)", r["importeB"], _usd(r["importeB"], r["fecha"]), _det(r, r["importeB"]))
        kg_vendidos += _f(r["kg"])
        cab_vendidas += int(r["cabezas"] or 0)
    for g in gastos:
        if _f(g["complemento"]):
            suma("Ventas", "Complemento (B)", g["complemento"], _usd(g["complemento"], g["fecha"]), _det(g, g["complemento"]))
        if _f(g["gastos"]):
            suma("Comercializacion", "Gastos de la liquidación", g["gastos"], _usd(g["gastos"], g["fecha"]), _det(g, g["gastos"]))
    for p in _pastaje(desde, hasta, establecimiento):
        suma("Pastaje", "Pastaje cobrado (neto)", p["pesos"], _usd(p["pesos"], p["fecha"]), _det(p, p["pesos"]))

    mapa = _mapa_rubros()
    for (grupo, rubro), filas in costos.agrupar_por_rubro(costos.compras(desde, hasta), mapa).items():
        for f in filas:
            suma(grupo, rubro, f["pesos"], f["usd"], _det(f, f["pesos"], enlace=f"/compras/{f['idCompra']}/editar"))
    for fo in (forrajes_cache if forrajes_cache is not None else costos.forrajes(anio, anio, vista)):
        if fo["periodo"] == anio:
            suma("Alimentacion", fo["rubro"], fo["pesos"], fo["usd"],
                 {"fecha": None, "documento": f"{fo['cultivo']} {fo['campania']}", "contacto": fo["detalle"],
                  "importe": round(fo["pesos"], 2), "enlace": "/produccion/resultado-cultivo"})
    pp = costos.personal_permanente(desde, hasta)
    if pp["pct"]:
        suma("Directos", "Personal permanente", pp["ganaderia"][0], pp["ganaderia"][1],
             {"fecha": None, "documento": "Remuneraciones", "contacto": f"{pp['pct']['g']}% del encargado",
              "importe": round(pp["ganaderia"][0], 2), "enlace": "/personal/remuneraciones"})
        suma("Estructura", "Personal permanente (estructura)", pp["estructura"][0], pp["estructura"][1],
             {"fecha": None, "documento": "Remuneraciones", "contacto": f"{pp['pct']['e']}% del encargado",
              "importe": round(pp["estructura"][0], 2), "enlace": "/personal/remuneraciones"})

    sup = superficie.superficie(anio, vista)
    return {"celdas": celdas, "kgVendidos": round(kg_vendidos, 1), "cabezasVendidas": cab_vendidas,
            "haGanaderas": sup["haEfectivas"]}


def _det(f, importe, enlace=None) -> dict:
    fecha = f.get("fecha")
    return {"fecha": str(fecha)[:10] if fecha else None, "documento": f.get("documento"), "contacto": f.get("contacto"),
            "importe": round(_f(importe), 2),
            "enlace": enlace or (f"/ventas/hacienda/{f['idVenta']}" if f.get("idVenta") else None)}


def _signo(grupo: str) -> int:
    return 1 if grupo in ("Ventas", "Pastaje", "Inventario") else -1


def resultado(desde: int, hasta: int, vista: str = "ejercicio", moneda: str = "USD",
              establecimiento: int | None = None) -> dict:
    anios = list(range(desde, hasta + 1))
    fcache = costos.forrajes(desde, hasta, vista)
    datos = {a: periodo(a, vista, fcache, establecimiento) for a in anios}
    k = "usd" if moneda == "USD" else "pesos"
    filas, vistos = [], set()
    for grupo in GRUPOS:
        rubros = sorted({r for a in anios for (g, r) in datos[a]["celdas"] if g == grupo})
        for r in rubros:
            vistos.add((grupo, r))
            filas.append({"grupo": grupo, "rubro": r, "abreDetalle": True,
                          "valores": {periodos.etiqueta(a): (round(datos[a]["celdas"][(grupo, r)][k], 2)
                                                             if (grupo, r) in datos[a]["celdas"] else None) for a in anios}})
    indicadores, avisos = {}, []
    for a in anios:
        tot = defaultdict(float)
        for (g, _r), c in datos[a]["celdas"].items():
            tot[g] += c[k]
        ventas_netas = tot["Ventas"] - tot["Comercializacion"]
        ingreso_neto = ventas_netas - tot["CompraHacienda"] + tot["Inventario"]
        mb = ingreso_neto + tot["Pastaje"] - tot["Directos"] - tot["Sanidad"] - tot["Alimentacion"]
        ro = mb - tot["Estructura"]
        ha = datos[a]["haGanaderas"]
        directos = tot["Directos"] + tot["Sanidad"] + tot["Alimentacion"]
        et = periodos.etiqueta(a)
        indicadores[et] = {
            "ventasNetas": round(ventas_netas, 2), "ingresoNeto": round(ingreso_neto, 2), "margenBruto": round(mb, 2),
            "estructura": round(tot["Estructura"], 2), "resultadoOperativo": round(ro, 2),
            "costoDirecto": round(directos, 2), "haGanaderas": ha, "mbHa": round(mb / ha, 2) if ha else None,
            "costoDirectoHa": round(directos / ha, 2) if ha else None,
            "kgVendidos": datos[a]["kgVendidos"], "cabezasVendidas": datos[a]["cabezasVendidas"],
            "kgProducidos": None, "costoPorKg": None, "ev": None, "evHa": None, "sinInventario": True}
        avisos.append({"periodo": et, "texto": "Sin stock de hacienda valuado: el resultado no incluye la variación de "
                                               "inventario (margen de caja)."})
    return {"vista": vista, "moneda": moneda, "establecimiento": establecimiento,
            "nota": ("Las ventas y el pastaje son del campo elegido; los costos son de toda la ganadería (las compras no "
                     "distinguen campo).") if establecimiento else None, "conversion": FUENTE if moneda == "USD" else None,
            "periodos": [{"clave": periodos.etiqueta(a), "desde": str(periodos.rango(a, vista)[0]),
                          "hasta": str(periodos.rango(a, vista)[1]), "sinInventario": True} for a in anios],
            "grupos": [{"grupo": g, "titulo": TITULOS[g], "signo": _signo(g)} for g in GRUPOS],
            "filas": filas, "indicadores": indicadores, "avisos": avisos}


def detalle(grupo: str, rubro: str, anio: int, vista: str = "ejercicio", establecimiento: int | None = None) -> list[dict]:
    d = periodo(anio, vista, None, establecimiento)
    return d["celdas"].get((grupo, rubro), {"detalle": []})["detalle"]
