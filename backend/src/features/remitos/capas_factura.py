"""Capas de stock desde la factura y flete de insumos (050 US9, research R-03 y R-06b).

- Capa virtual `FC{IdDetalleCompra}`: un renglón de insumo en alcance (tamiz vigente CultivoStock, aprobado,
  con producto) que todavía no tiene remito entra al stock a la fecha de la factura. Cuando se vincula el
  remito, la capa desaparece y el consumo pasa a la capa real (R-03). Prefijo `FC` (no `F`) porque `F{id}`
  ya identifica las salidas por faltante de ajuste.
- Flete de insumos: costo de adquisición. Se reparte por importe entre los renglones de insumo de la misma
  factura; si vino en factura aparte, entre los de la(s) factura(s) relacionada(s), y solo cuando el renglón
  de flete está aprobado (queda "Para revisar" hasta que se confirma la relación).

Fuera de alcance no cambia nada: sin filas vigentes en TamizRenglones ambas funciones devuelven vacío.
"""

from __future__ import annotations

from collections import defaultdict

from src.db.connection import fetch_all

_EPS = 1e-9


def repartir_por_importe(insumos: dict[int, float], monto: float) -> dict[int, float]:
    """Reparte `monto` entre `insumos` ({id: importe}) en proporción al importe, al centavo; el residuo del
    redondeo va al de mayor importe para que la suma sea exacta."""
    total = sum(v for v in insumos.values() if v > 0)
    if total <= _EPS or not insumos:
        return {}
    partes = {i: round(monto * v / total, 2) for i, v in insumos.items() if v > 0}
    residuo = round(monto - sum(partes.values()), 2)
    if residuo:
        mayor = max(partes, key=lambda i: insumos[i])
        partes[mayor] = round(partes[mayor] + residuo, 2)
    return partes


def _a_pesos(importe: float, moneda: str | None, tc: float | None) -> float:
    return importe * (tc or 0.0) if moneda == "Dolares" else importe


def flete_por_renglon() -> dict[int, float]:
    """Flete atribuido (en pesos) a cada renglón de insumo en alcance: {IdDetalleCompra: pesos}."""
    filas = fetch_all(
        """
        SELECT d.IdDetalleCompra AS id, d.IdCompra AS idCompra, ISNULL(d.Cantidad, 0) * ISNULL(d.[Precio Unitario], 0) AS importe,
               c.Moneda AS moneda, c.[Tipo de Cambio] AS tc, tz.Destino AS destino, tz.Estado AS estado,
               CASE WHEN tr.ReglaDepende = 'FleteInsumo' THEN 1 ELSE 0 END AS esFlete,
               NULLIF(d.IdFormulado, 0) AS idProducto
        FROM dbo.TamizRenglones tz
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.TamizRubroDestino tr ON tr.IdRubro = d.IdRubro
        WHERE tz.Vigente = 1 AND tz.Destino = 'CultivoStock' AND tz.Estado = 'Aprobada'
        """
    )
    if not filas:
        return {}
    insumos_por_compra: dict[int, dict[int, float]] = defaultdict(dict)
    fletes: list[dict] = []
    for f in filas:
        pesos = _a_pesos(float(f["importe"] or 0), f["moneda"], float(f["tc"] or 0))
        if f["esFlete"]:
            fletes.append({**f, "pesos": pesos})
        elif f["idProducto"]:
            insumos_por_compra[f["idCompra"]][f["id"]] = pesos
    if not fletes:
        return {}
    relacionadas: dict[int, set[int]] = defaultdict(set)
    for r in fetch_all("SELECT IdCompra AS a, IdCompraRelacionada AS b FROM dbo.CompraDocumentosRelacionados"):
        relacionadas[r["a"]].add(r["b"])
        relacionadas[r["b"]].add(r["a"])
    out: dict[int, float] = defaultdict(float)
    for fl in fletes:
        destino = dict(insumos_por_compra.get(fl["idCompra"], {}))
        if not destino:
            for otra in relacionadas.get(fl["idCompra"], ()):
                destino.update(insumos_por_compra.get(otra, {}))
        for id_, monto in repartir_por_importe(destino, fl["pesos"]).items():
            out[id_] += monto
    return dict(out)


def renglones_sin_remito(id_producto: int | None = None) -> list[dict]:
    """Renglones de insumo en alcance, aprobados para stock y sin ningún vínculo con remito."""
    filtro, params = (" AND d.IdFormulado = ?", (id_producto,)) if id_producto is not None else ("", ())
    return fetch_all(
        f"""
        SELECT d.IdDetalleCompra AS idDetalleCompra, d.IdCompra AS idCompra, d.IdFormulado AS idProducto, d.Unidad AS unidad,
               ISNULL(d.Cantidad, 0) AS cantidad, ISNULL(d.[Precio Unitario], 0) AS precio, c.Moneda AS moneda,
               c.[Tipo de Cambio] AS tc, c.Fecha AS fecha, c.[Nro Documento] AS nroDocumento
        FROM dbo.TamizRenglones tz
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        WHERE tz.Vigente = 1 AND tz.Destino = 'CultivoStock' AND tz.Estado = 'Aprobada'
          AND NULLIF(d.IdFormulado, 0) IS NOT NULL AND ISNULL(d.Cantidad, 0) > 0 AND c.Fecha IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM dbo.tblRemitoCompra t WHERE t.IdDetalleCompra = d.IdDetalleCompra){filtro}
        """,
        params,
    )


def costo_unitario_factura(r: dict, flete_pesos: float) -> float:
    """Costo en pesos por unidad de la factura: precio al TC del comprobante más el flete atribuido."""
    cantidad = float(r["cantidad"] or 0)
    unitario = _a_pesos(float(r["precio"] or 0), r.get("moneda"), float(r.get("tc") or 0))
    return unitario + (flete_pesos / cantidad if cantidad > _EPS else 0.0)
