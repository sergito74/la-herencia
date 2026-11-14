"""Vínculo automático remito ↔ factura (050 US9, research R-04).

Candidato = mismo proveedor, mismo producto (IdFormulado) y fecha del remito entre 60 días antes y
30 días después de la factura. Se comparan cantidades en la unidad base del producto, sin tolerancias
(P17): solo se vincula si hay UNA combinación exacta de remitos (entregas parciales incluidas) que suma
lo pendiente del renglón. Lo demás va a VinculoRemitoPendiente con los candidatos. Nunca se vincula más
de lo que tiene el renglón de factura ni más de lo que le queda al renglón de remito.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from itertools import combinations

from src.db.connection import execute_write_transaction, fetch_all, fetch_one

_log = logging.getLogger(__name__)

DIAS_ANTES, DIAS_DESPUES = 60, 30
MAX_REMITOS_COMBINADOS = 4
_EPS = 1e-6


def _fecha(v) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    return v


def en_ventana(fecha_factura, fecha_remito) -> bool:
    ff, fr = _fecha(fecha_factura), _fecha(fecha_remito)
    if ff is None or fr is None:
        return False
    return ff - timedelta(days=DIAS_ANTES) <= fr <= ff + timedelta(days=DIAS_DESPUES)


def combinaciones_exactas(pendiente: float, candidatos: list[dict]) -> list[tuple[dict, ...]]:
    """Subconjuntos de candidatos (cada uno con `disponible`, en base) cuya suma es exactamente `pendiente`.
    Pura: la usa la vinculación y los tests."""
    utiles = [c for c in candidatos if c["disponible"] > _EPS]
    out = []
    for n in range(1, min(MAX_REMITOS_COMBINADOS, len(utiles)) + 1):
        for combo in combinations(utiles, n):
            if abs(sum(c["disponible"] for c in combo) - pendiente) <= _EPS * max(1.0, pendiente):
                out.append(combo)
    return out


def decidir(renglon: dict, candidatos: list[dict]) -> dict:
    """`renglon`: {idDetalleCompra, fecha, pendiente (base)}; `candidatos`: renglones de remito del mismo
    proveedor y producto con {idDetalleRemito, fecha, disponible (base), factor}. Devuelve
    {'accion': 'vincular', 'items': [...]} | {'accion': 'revisar', 'motivo', 'candidatos'} | {'accion': 'nada'}."""
    if renglon["pendiente"] <= _EPS:
        return {"accion": "nada"}
    en_v = [c for c in candidatos if en_ventana(renglon["fecha"], c["fecha"])]
    if not en_v:
        return {"accion": "nada"}  # todavía no llegó el remito: queda la capa de la factura
    combos = combinaciones_exactas(renglon["pendiente"], en_v)
    if len(combos) == 1:
        items = [{"idDetalleRemito": c["idDetalleRemito"], "cantidadRemito": c["disponible"] / c["factor"]}
                 for c in combos[0]]
        return {"accion": "vincular", "items": items}
    motivo = "Varias combinaciones de remitos posibles" if combos else "Las cantidades de los remitos no coinciden con la factura"
    return {"accion": "revisar", "motivo": motivo,
            "candidatos": [{"idDetalleRemito": c["idDetalleRemito"], "disponible": c["disponible"]} for c in en_v]}


# ---------------------------------------------------------------- acceso a datos

def _renglones_factura(id_compra: int) -> list[dict]:
    return fetch_all(
        """
        SELECT d.IdDetalleCompra AS idDetalleCompra, d.IdCompra AS idCompra, d.IdFormulado AS idProducto,
               d.Unidad AS unidad, ISNULL(d.Cantidad, 0) AS cantidad, c.Fecha AS fecha, c.IdContacto AS idProveedor,
               ISNULL((SELECT SUM(t.CantidadRemitida) FROM dbo.tblRemitoCompra t WHERE t.IdDetalleCompra = d.IdDetalleCompra), 0) AS vinculada
        FROM dbo.Det_Compras d
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = d.IdDetalleCompra AND tz.Vigente = 1
        WHERE d.IdCompra = ? AND tz.Destino = 'CultivoStock' AND NULLIF(d.IdFormulado, 0) IS NOT NULL
          AND c.[Tipo documento] = 'Factura'
        """,
        (id_compra,),
    )


def _remitos_candidatos(id_proveedor: int, id_producto: int) -> list[dict]:
    return fetch_all(
        """
        SELECT rd.IdDetalleRemito AS idDetalleRemito, r.Fecha AS fecha, rd.[Unidad Medida] AS unidad,
               ISNULL(rd.Cantidad, 0) - ISNULL((SELECT SUM(t.CantidadRemitida) FROM dbo.tblRemitoCompra t
                                               WHERE t.IdDetalleRemito = rd.IdDetalleRemito), 0) AS disponible
        FROM dbo.Remitos_Detalles rd JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito
        LEFT JOIN dbo.Remitos_Extra x ON x.IdRemito = r.IdRemito
        WHERE r.IdProveedor = ? AND rd.IdFormulado = ? AND ISNULL(x.Anulado, 0) = 0
        """,
        (id_proveedor, id_producto),
    )


def _ya_pendiente(id_detalle_compra: int) -> bool:
    return fetch_one("SELECT 1 AS x FROM dbo.VinculoRemitoPendiente WHERE IdDetalleCompra = ? AND Resuelto = 0 AND Tipo = 'remito'",
                     (id_detalle_compra,)) is not None


def vincular_por_compra(id_compra: int) -> dict:
    """Vincula los renglones de insumo de la factura con sus remitos. Devuelve un resumen."""
    from src.features.remitos import repository as remitos_repo
    from src.features.remitos.stock_datos import equivalencias, factor_a_base, unidades_base

    bases, equiv = unidades_base(), equivalencias()
    resumen = {"vinculados": 0, "revisar": 0}
    for r in _renglones_factura(id_compra):
        f_fac, falta_fac = factor_a_base(r["idProducto"], r["unidad"], bases, equiv)
        pendiente = (float(r["cantidad"]) - float(r["vinculada"])) * f_fac
        cands = []
        for c in _remitos_candidatos(r["idProveedor"], r["idProducto"]):
            f_rem, falta_rem = factor_a_base(r["idProducto"], c["unidad"], bases, equiv)
            if falta_rem:
                continue
            cands.append({**c, "factor": f_rem, "disponible": float(c["disponible"]) * f_rem})
        decision = decidir({**r, "pendiente": pendiente}, cands)
        if decision["accion"] == "vincular" and not falta_fac:
            por_remito: dict[int, list] = {}
            for it in decision["items"]:
                id_remito = fetch_one("SELECT IdRemito AS r FROM dbo.Remitos_Detalles WHERE IdDetalleRemito = ?",
                                      (it["idDetalleRemito"],))["r"]
                # CantidadRemitida se guarda en la unidad de la factura, como hace la pantalla de remitos.
                cant = it["cantidadRemito"] * next(c["factor"] for c in cands if c["idDetalleRemito"] == it["idDetalleRemito"]) / f_fac
                por_remito.setdefault(id_remito, []).append(
                    {"idDetalleRemito": it["idDetalleRemito"], "idDetalleCompra": r["idDetalleCompra"], "cantidad": cant})
            for id_remito, items in por_remito.items():
                remitos_repo.vincular_renglones(id_remito, items)
            resumen["vinculados"] += 1
        elif decision["accion"] in ("vincular", "revisar") and not _ya_pendiente(r["idDetalleCompra"]):
            motivo = decision.get("motivo") or "Falta la equivalencia de unidades del producto"
            execute_write_transaction([(
                "INSERT INTO dbo.VinculoRemitoPendiente (IdDetalleCompra, Tipo, CandidatosJson, Motivo) VALUES (?, 'remito', ?, ?)",
                (r["idDetalleCompra"], json.dumps(decision.get("candidatos") or [], default=str), motivo),
            )])
            resumen["revisar"] += 1
    return resumen


def vincular_por_remito(id_remito: int) -> dict:
    """Al guardar un remito: intenta vincular las facturas en alcance del mismo proveedor cercanas en fecha."""
    cab = fetch_one("SELECT IdProveedor AS p, Fecha AS f FROM dbo.Remitos WHERE IdRemito = ?", (id_remito,))
    if cab is None:
        return {"vinculados": 0, "revisar": 0}
    compras = fetch_all(
        """
        SELECT DISTINCT d.IdCompra AS id FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = d.IdDetalleCompra AND tz.Vigente = 1 AND tz.Destino = 'CultivoStock'
        WHERE c.IdContacto = ? AND c.Fecha BETWEEN DATEADD(day, -?, ?) AND DATEADD(day, ?, ?)
        """,
        (cab["p"], DIAS_DESPUES, cab["f"], DIAS_ANTES, cab["f"]),
    )
    total = {"vinculados": 0, "revisar": 0}
    for c in compras:
        res = vincular_por_compra(c["id"])
        total = {k: total[k] + res[k] for k in total}
    return total


def vincular_seguro(funcion, id_: int) -> None:
    """Disparo desde el guardado: un error del vínculo no impide guardar."""
    try:
        funcion(id_)
    except Exception:  # noqa: BLE001
        _log.exception("Vínculo automático 050: falló para %s", id_)
