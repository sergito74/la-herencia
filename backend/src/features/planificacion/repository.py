"""Planificación Agrícola: qué lote se destina a qué Cultivo/Campaña, tal como lo
definen los asesores agronómicos. Vive en la tabla heredada `PlanAgricola` (se
lee y también se escribe: este módulo es su primera interfaz de administración,
antes se cargaba directo en Access). Un mismo lote puede tener más de un
Cultivo en la misma Campaña (double crop, p. ej. trigo/soja de segunda) — no
hay restricción de unicidad por (Lote, Campaña), solo por (Lote, Cultivo,
Campaña).

Consumida también por Órdenes de Trabajo (011) para sugerir los lotes de un
Cultivo/Campaña al planificar una orden.
"""

from __future__ import annotations

from src.db.connection import execute_write, execute_write_transaction, fetch_all, fetch_one


def listar(id_campania: int | None = None) -> list[dict]:
    where, params = "1 = 1", ()
    if id_campania is not None:
        where, params = "p.IdCampaña = ?", (id_campania,)
    return fetch_all(
        f"""
        SELECT p.IdPlanAgricola AS idPlanAgricola, p.IdLote AS idLote, l.[Numero Lote] AS numeroLote, l.Superficie AS superficie,
               p.IdCultivo AS idCultivo, c.Cultivo AS cultivo, p.IdCampaña AS idCampania, ca.Campaña AS campania
        FROM dbo.PlanAgricola p
        LEFT JOIN dbo.Lotes l ON l.IdLote = p.IdLote
        LEFT JOIN dbo.Cultivos c ON c.IdCultivo = p.IdCultivo
        LEFT JOIN dbo.Campañas ca ON ca.IdCampaña = p.IdCampaña
        WHERE {where} AND l.[Numero Lote] <> 'PRUE'
        ORDER BY ca.Campaña DESC, c.Cultivo, l.[Numero Lote]
        """,
        params,
    )


def crear(datos: dict) -> int:
    existe = fetch_one(
        "SELECT 1 AS x FROM dbo.PlanAgricola WHERE IdLote = ? AND IdCultivo = ? AND IdCampaña = ?",
        (datos["idLote"], datos["idCultivo"], datos["idCampania"]),
    )
    if existe:
        raise ValueError(["Ese lote ya tiene asignado ese Cultivo en esa Campaña."])
    # `IdLoteCña` es una columna heredada de Access (NOT NULL, con índice único):
    # una etiqueta de texto libre lote+temporada+campaña ("3BVER2627") que la
    # planilla vieja armaba a mano. Esta pantalla no reproduce esa convención
    # (no hay un mapeo confiable Cultivo→temporada); genera un valor propio,
    # único por construcción (mismo criterio de unicidad que ya valida arriba),
    # que ningún código de esta app vuelve a leer.
    id_lote_cania = f"{datos['idLote']}-{datos['idCultivo']}-{datos['idCampania']}"
    resultados = execute_write_transaction(
        [
            (
                "INSERT INTO dbo.PlanAgricola (IdLote, IdCultivo, IdCampaña, IdLoteCña) OUTPUT INSERTED.IdPlanAgricola VALUES (?, ?, ?, ?)",
                (datos["idLote"], datos["idCultivo"], datos["idCampania"], id_lote_cania),
            )
        ]
    )
    return resultados[0]


def eliminar(id_plan_agricola: int) -> None:
    if not fetch_one("SELECT 1 AS x FROM dbo.PlanAgricola WHERE IdPlanAgricola = ?", (id_plan_agricola,)):
        raise ValueError([f"El registro {id_plan_agricola} no existe."])
    execute_write("DELETE FROM dbo.PlanAgricola WHERE IdPlanAgricola = ?", (id_plan_agricola,))
