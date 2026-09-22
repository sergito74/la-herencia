"""Costo de maquinaria propia y de contratista, prorrateados entre los lotes
de la orden por superficie (Historias 3 y 4)."""

from __future__ import annotations

from src.db.connection import fetch_one


def _superficies_por_lote(distribuciones: list[dict]) -> dict[int, float]:
    """Superficie aplicada por lote (suma de renglones si el mismo lote aparece
    en más de un insumo), para prorratear un costo de la orden entre lotes."""
    por_lote: dict[int, float] = {}
    for d in distribuciones:
        if d.get("aplicar", True):
            por_lote[d["idLote"]] = por_lote.get(d["idLote"], 0.0) + float(d["superficie"])
    return por_lote


def prorratear_por_superficie(monto_total: float, distribuciones: list[dict]) -> dict[int, float]:
    """Reparte `monto_total` entre los lotes de `distribuciones` en proporción a
    su superficie (mismo criterio para maquinaria propia y contratista)."""
    por_lote = _superficies_por_lote(distribuciones)
    superficie_total = sum(por_lote.values())
    if superficie_total <= 0:
        return {}
    return {lote: round(monto_total * sup / superficie_total, 2) for lote, sup in por_lote.items()}


def costo_maquinaria(costo_por_hectarea: float, distribuciones: list[dict]) -> dict:
    """Costo de un renglón de maquinaria propia: costoPorHectárea × superficie de
    cada lote de la orden, cargado a mano (sin tarifa persistente, research.md §4)."""
    por_lote = _superficies_por_lote(distribuciones)
    superficie_total = sum(por_lote.values())
    monto_total = round(costo_por_hectarea * superficie_total, 2)
    return {"montoTotal": monto_total, "porLote": {lote: round(costo_por_hectarea * sup, 2) for lote, sup in por_lote.items()}}


def costo_contratista(id_compra: int, distribuciones: list[dict]) -> dict:
    """Costo de la factura de un contratista: su importe neto, dolarizado con el
    TC de esa factura (mismo criterio que Remitos, research.md §5), prorrateado
    entre los lotes de la orden por superficie."""
    compra = fetch_one(
        "SELECT c.Moneda AS moneda, c.[Tipo de Cambio] AS tipoDeCambio, "
        "(SELECT SUM(d.Cantidad * d.[Precio Unitario]) FROM dbo.Det_Compras d WHERE d.IdCompra = c.IdDeuda) AS neto "
        "FROM dbo.Compras c WHERE c.IdDeuda = ?",
        (id_compra,),
    )
    if compra is None:
        raise ValueError([f"La factura {id_compra} no existe."])
    neto = float(compra["neto"] or 0)
    tc = float(compra["tipoDeCambio"] or 0)
    moneda = compra["moneda"] or "Pesos"
    monto_pesos = neto * tc if moneda == "Dolares" and tc else neto
    monto_dolares = (monto_pesos / tc) if tc else None
    return {
        "montoPesos": round(monto_pesos, 2),
        "montoDolares": round(monto_dolares, 2) if monto_dolares is not None else None,
        "porLote": prorratear_por_superficie(monto_pesos, distribuciones),
    }
