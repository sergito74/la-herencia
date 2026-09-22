"""Formulario de Retiro: documento con numeración secuencial propia (FR-008),
emitido al guardar una orden, con el listado de insumos a preparar."""

from __future__ import annotations

from src.db.connection import fetch_one


def stmt_generar(id_orden_resultado_index: int = 0):
    """Statement de transacción que inserta el Formulario de Retiro de la orden
    recién creada (usa el resultado del insert de cabecera en `execute_write_transaction`)."""

    def build(res: list) -> tuple:
        return (
            "INSERT INTO dbo.Formularios_Retiro (IdOrdenTrabajo) OUTPUT INSERTED.IdFormularioRetiro VALUES (?)",
            (res[id_orden_resultado_index],),
        )

    return build


def obtener(id_orden: int) -> dict | None:
    fila = fetch_one(
        "SELECT IdFormularioRetiro AS idFormularioRetiro, FechaEmision AS fechaEmision FROM dbo.Formularios_Retiro WHERE IdOrdenTrabajo = ?",
        (id_orden,),
    )
    return fila
