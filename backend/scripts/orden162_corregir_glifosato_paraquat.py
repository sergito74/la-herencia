"""Orden 162 (12/11/2026, pedido de Sergio contra la planilla de la orden): el glifosato (Power Plus II) estaba repartido
en lotes que no lo llevan (5 trigo, 3C/6/6A girasol a 2,8 = dosis de paraquat) y faltaba en 3AB maíz diferido; al
paraquat le faltaba el 3C a 2,8. Se corrige la distribución sin tocar lo entregado ni los ajustes del recuento (el neto
= cargado + ajuste se reparte por esta distribución). Superficies: las del sistema.

uso: python -m scripts.orden162_corregir_glifosato_paraquat [--aplicar]
"""
import sys

from src.db.connection import execute_write_transaction, fetch_all
from src.features.ordenes import distribucion

POWER_PLUS, PARAQUAT = 893, 895
LOTE_3AB, LOTE_3C = 35, 7


def plan():
    sqls = []
    for id_insumo, quitar, agregar in (
        (POWER_PLUS, ["5", "3C", "6", "6A"], (LOTE_3AB, 3.2)),
        (PARAQUAT, [], (LOTE_3C, 2.8)),
    ):
        filas = fetch_all(
            "SELECT d.IdDistrib, d.IdLote, l.[Numero Lote] AS lote, d.IdCultivo, d.IdCampania, d.DosisHa AS dosisHa, "
            "d.Superficie AS superficie, d.Aplicar AS aplicar FROM dbo.Ordenes_Trabajo_Distrib d "
            "JOIN dbo.Lotes l ON l.IdLote = d.IdLote WHERE d.IdOrdenInsumo = ?", (id_insumo,))
        total = fetch_all("SELECT CantidadTotal AS t FROM dbo.Ordenes_Trabajo_Insumos WHERE IdOrdenInsumo = ?", (id_insumo,))[0]["t"]
        # Cultivo/campaña/superficie del lote a agregar: los de ese lote en otro insumo de la misma orden.
        ref = fetch_all(
            "SELECT TOP 1 d.IdCultivo, d.IdCampania, d.Superficie FROM dbo.Ordenes_Trabajo_Distrib d "
            "JOIN dbo.Ordenes_Trabajo_Insumos i ON i.IdOrdenInsumo = d.IdOrdenInsumo "
            "WHERE i.IdOrdenTrabajo = 162 AND d.IdLote = ?", (agregar[0],))[0]
        quedan = [f for f in filas if f["lote"] not in quitar]
        nuevo = {"IdDistrib": None, "IdLote": agregar[0], "IdCultivo": ref["IdCultivo"], "IdCampania": ref["IdCampania"],
                 "dosisHa": agregar[1], "superficie": ref["Superficie"], "aplicar": True}
        repartidas = distribucion.repartir_total(total, quedan + [nuevo])
        for f in filas:
            if f["lote"] in quitar:
                sqls.append(("DELETE FROM dbo.Ordenes_Trabajo_Distrib WHERE IdDistrib = ?", (f["IdDistrib"],)))
        for r in repartidas:
            if r["IdDistrib"] is None:
                sqls.append(("INSERT INTO dbo.Ordenes_Trabajo_Distrib (IdOrdenInsumo, IdLote, IdCultivo, IdCampania, DosisHa, "
                             "Superficie, CantidadAsignada, Aplicar) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                             (id_insumo, r["IdLote"], r["IdCultivo"], r["IdCampania"], r["dosisHa"], r["superficie"], r["cantidadAsignada"])))
            else:
                sqls.append(("UPDATE dbo.Ordenes_Trabajo_Distrib SET CantidadAsignada = ? WHERE IdDistrib = ?",
                             (r["cantidadAsignada"], r["IdDistrib"])))
            print(id_insumo, r.get("lote", "NUEVO"), r["dosisHa"], r["superficie"], r["cantidadAsignada"])
        print("total", total, "suma", round(sum(r["cantidadAsignada"] for r in repartidas), 4))
    return sqls


if __name__ == "__main__":
    s = plan()
    if "--aplicar" in sys.argv:
        execute_write_transaction(s)
        print("aplicado", len(s))
