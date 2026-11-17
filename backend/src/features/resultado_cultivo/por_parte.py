"""Costo de un cultivo/campaña agrupado en las 9 partes de la estructura (050 US7, T030).

Toma las mismas líneas que el costo del cultivo (sin doble conteo, ver costos.py) y le asigna a cada una su
parte: las fracciones del esquema nuevo traen IdParte; las heredadas se clasifican por su rubro con la tabla
rubro→destino; maquinaria propia y contratistas son Labores; el seguro, Seguro agrícola. Lo que no encaja
queda en "Sin clasificar" para que se vea (nada se esconde).
"""

from __future__ import annotations

from collections import defaultdict

from src.db.connection import fetch_all, fetch_one
from src.features.resultado_cultivo import costos, resultado

PARTE_LABORES, PARTE_SEGURO = 4, 7
SIN_CLASIFICAR = "Sin clasificar"
INSUMOS_ORDENES = "Insumos aplicados (órdenes)"

_VIGENTE = (
    "p.IdCorrida = (SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2 "
    "WHERE p2.IdDetalleCompra = p.IdDetalleCompra AND p2.Origen = p.Origen ORDER BY p2.FechaCalculo DESC)"
)
_DOLARES = "SUM(p.Importe / NULLIF(CASE WHEN c.Moneda = 'Dolares' THEN c.[Tipo de Cambio] END, 0))"


def _partes() -> dict[int, str]:
    return {f["id"]: f["nombre"] for f in fetch_all("SELECT IdParte AS id, Nombre AS nombre FROM dbo.PartesEstructuraCosto ORDER BY Orden")}


def _parte_por_rubro() -> dict[str, int]:
    return {f["rubro"]: f["idParte"] for f in fetch_all(
        "SELECT r.Rubro AS rubro, t.IdParte AS idParte FROM dbo.TamizRubroDestino t JOIN dbo.Rubros r ON r.IdRubro = t.IdRubro "
        "WHERE t.IdParte IS NOT NULL"
    )}


def parte_de_linea(linea: dict, partes: dict[int, str], por_rubro: dict[str, int]) -> str:
    """Pura: nombre de la parte de una línea de costo."""
    if linea.get("idParte"):
        return partes.get(linea["idParte"], SIN_CLASIFICAR)
    if linea.get("origen") == "Seguro":
        return partes.get(PARTE_SEGURO, SIN_CLASIFICAR)
    if linea.get("concepto") in ("Maquinaria propia", "Contratista"):
        return partes.get(PARTE_LABORES, SIN_CLASIFICAR)
    if linea.get("concepto") == "Insumo" and linea.get("origen") == "OrdenTrabajo":
        return INSUMOS_ORDENES
    id_parte = por_rubro.get(linea.get("rubro"))
    return partes.get(id_parte, SIN_CLASIFICAR) if id_parte else SIN_CLASIFICAR


def agrupar(lineas: list[dict], partes: dict[int, str], por_rubro: dict[str, int], superficie: float) -> list[dict]:
    """Pura: totales por parte, en el orden de la estructura, con $/ha y US$/ha."""
    acc: dict[str, dict] = defaultdict(lambda: {"pesos": 0.0, "dolares": 0.0, "documentos": []})
    for l in lineas:
        nombre = parte_de_linea(l, partes, por_rubro)
        acc[nombre]["pesos"] += float(l.get("montoPesos") or 0)
        acc[nombre]["dolares"] += float(l.get("montoDolares") or 0)
        acc[nombre]["documentos"].append({k: l.get(k) for k in ("concepto", "rubro", "montoPesos", "montoDolares",
                                                                  "idCompra", "idDetalleCompra", "idOrdenTrabajo")})
    out = []
    for nombre in [*partes.values(), INSUMOS_ORDENES, SIN_CLASIFICAR]:
        if nombre not in acc:
            continue
        a = acc[nombre]
        out.append({"parte": nombre, "pesos": round(a["pesos"], 2), "dolares": round(a["dolares"], 2),
                    "pesosHa": round(a["pesos"] / superficie, 2) if superficie > 0 else None,
                    "dolaresHa": round(a["dolares"] / superficie, 2) if superficie > 0 else None,
                    "documentos": a["documentos"]})
    return out


def _totales(sql: str, params: tuple = ()) -> dict:
    r = fetch_one(sql, params) or {}
    return {"pesos": round(float(r.get("pesos") or 0), 2), "dolares": round(float(r.get("dolares") or 0), 2)}


def _en_stock_sin_consumir() -> dict:
    """Fracciones 'en stock' de la corrida vigente de los renglones en alcance (todavía no son costo)."""
    if not costos.esquema_050_activo():
        return {"pesos": 0.0, "dolares": 0.0}
    return _totales(
        f"""
        SELECT SUM(p.Importe) AS pesos, {_DOLARES} AS dolares
        FROM dbo.ImputacionPropuestas p
        JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = p.IdDetalleCompra AND tz.Vigente = 1 AND tz.Destino = 'CultivoStock'
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = p.IdDetalleCompra JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        WHERE p.Origen = 'Insumo' AND p.IdCultivo IS NULL AND p.IdOrdenTrabajo IS NULL AND p.IdCentroCosto IS NULL
          AND ISNULL(p.EsGanaderia, 0) = 0 AND {_VIGENTE}
        """
    )


def _estructura_campania(id_campania: int) -> dict:
    """Gasto general del año agrícola de la campaña (julio a junio; renglones en alcance con destino Gasto general)."""
    vacio = {"pesos": 0.0, "dolares": 0.0}
    if not costos.esquema_050_activo():
        return vacio
    nombre = (fetch_one("SELECT [Campaña] AS n FROM dbo.[Campañas] WHERE [IdCampaña] = ?", (id_campania,)) or {}).get("n") or ""
    if not nombre[:4].isdigit():
        return vacio
    anio = int(nombre[:4])
    return _totales(
        f"""
        SELECT SUM(p.Importe) AS pesos, {_DOLARES} AS dolares
        FROM dbo.ImputacionPropuestas p
        JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = p.IdDetalleCompra AND tz.Vigente = 1 AND tz.Destino = 'Estructura'
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = p.IdDetalleCompra JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        WHERE p.Origen = 'Directo' AND p.Estado = 'Aprobada'
          AND c.Fecha >= DATEFROMPARTS(?, 7, 1) AND c.Fecha < DATEFROMPARTS(?, 7, 1) AND {_VIGENTE}
        """,
        (anio, anio + 1),
    )


def costo_por_parte(id_cultivo: int, id_campania: int) -> dict:
    superficie = float(resultado.superficie_sembrada(id_cultivo, id_campania) or 0)
    lineas = costos.costo_total(id_cultivo, id_campania)["lineas"]
    return {
        "superficieHa": superficie,
        "partes": agrupar(lineas, _partes(), _parte_por_rubro(), superficie),
        "estructuraCampania": _estructura_campania(id_campania),
        "enStockSinConsumir": _en_stock_sin_consumir(),
        "paraRevisar": _para_revisar(),
    }


def _para_revisar() -> dict:
    if not costos.esquema_050_activo():
        return {"pesos": 0.0, "documentos": 0}
    from src.features.imputacion import tamiz_repository

    return tamiz_repository.resumen_para_revisar()
