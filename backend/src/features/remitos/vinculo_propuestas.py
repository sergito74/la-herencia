"""Vínculos remito ↔ factura propuestos para revisar (050, 16/11/2026).

Las propuestas las calcula scripts/vinculo_propuesta_050.py (misma regla que la simulación validada) y quedan en
dbo.VinculoRemitoPendiente con Tipo = 'propuesta050'. Acá se listan agrupadas (factura + producto + remito) y se
graban en tblRemitoCompra solo las que Sergio aprueba, con la misma función que usa la pantalla de remitos.
"""

from __future__ import annotations

import json
from collections import defaultdict

from src.db.connection import execute_write_transaction, fetch_all
from src.features.remitos import repository as remitos_repo

TIPO = "propuesta050"


def _filas(ids: list[int] | None = None) -> list[dict]:
    filtro = ""
    params: tuple = (TIPO,)
    if ids:
        filtro = f" AND v.IdVinculoPend IN ({','.join('?' * len(ids))})"
        params += tuple(ids)
    return fetch_all(
        f"""
        SELECT v.IdVinculoPend AS id, v.IdDetalleRemito AS idDetalleRemito, v.IdDetalleCompra AS idDetalleCompra,
               v.CandidatosJson AS datos, v.Motivo AS motivo, rd.IdRemito AS idRemito, d.IdCompra AS idCompra
        FROM dbo.VinculoRemitoPendiente v
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = v.IdDetalleCompra
        LEFT JOIN dbo.Remitos_Detalles rd ON rd.IdDetalleRemito = v.IdDetalleRemito
        WHERE v.Tipo = ? AND v.Resuelto = 0{filtro}
        """,
        params,
    )


def listar() -> dict:
    grupos: dict[tuple, dict] = {}
    for f in _filas():
        d = json.loads(f["datos"] or "{}")
        k = (f["idCompra"], d.get("producto"), f["idRemito"])
        g = grupos.setdefault(k, {
            "ids": [], "idCompra": f["idCompra"], "idRemito": f["idRemito"], "factura": d.get("factura"),
            "fechaFactura": d.get("fechaFactura"), "proveedor": d.get("proveedor"), "producto": d.get("producto"),
            "remito": d.get("remito"), "fechaRemito": d.get("fechaRemito"), "regla": d.get("regla"),
            "cantidad": 0.0, "renglones": 0, "sinRemito": f["idDetalleRemito"] is None,
        })
        g["ids"].append(f["id"])
        g["cantidad"] += float(d.get("cantidadFactura") or 0)
        g["renglones"] += 1
    items = sorted(grupos.values(), key=lambda g: (g["sinRemito"], g["fechaFactura"] or "", g["factura"] or "", g["producto"] or ""))
    return {"items": items, "conRemito": sum(1 for g in items if not g["sinRemito"]), "sinRemito": sum(1 for g in items if g["sinRemito"])}


def grabar(ids: list[int]) -> dict:
    """Graba en tblRemitoCompra las propuestas elegidas (por remito) y las marca resueltas. Los errores de un remito
    no frenan a los demás: se devuelven para mostrarlos."""
    por_remito: dict[int, list[dict]] = defaultdict(list)
    for f in _filas(ids):
        if f["idRemito"] is None:
            continue
        d = json.loads(f["datos"] or "{}")
        por_remito[f["idRemito"]].append({"id": f["id"], "idDetalleRemito": f["idDetalleRemito"],
                                          "idDetalleCompra": f["idDetalleCompra"], "cantidad": float(d.get("cantidadVincular") or 0)})
    grabados, errores, avisos = 0, [], []
    for id_remito, items in por_remito.items():
        try:
            res = remitos_repo.vincular_renglones(id_remito, [{k: it[k] for k in ("idDetalleRemito", "idDetalleCompra", "cantidad")} for it in items])
        except ValueError as exc:
            errores.append({"idRemito": id_remito, "mensajes": exc.args[0] if exc.args else [str(exc)]})
            continue
        avisos += (res or {}).get("advertencias") or []
        execute_write_transaction([(f"UPDATE dbo.VinculoRemitoPendiente SET Resuelto = 1 WHERE IdVinculoPend IN ({','.join('?' * len(items))})",
                                    tuple(it["id"] for it in items))])
        grabados += len(items)
    return {"grabados": grabados, "errores": errores, "advertencias": avisos}


def descartar(ids: list[int]) -> int:
    if not ids:
        return 0
    return execute_write_transaction([(
        f"UPDATE dbo.VinculoRemitoPendiente SET Resuelto = 1, Motivo = 'Descartado por el usuario' WHERE Tipo = ? AND IdVinculoPend IN ({','.join('?' * len(ids))})",
        (TIPO, *ids))])[0]
