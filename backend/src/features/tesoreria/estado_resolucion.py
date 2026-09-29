"""Estado unificado de un movimiento de Tesorería (024) — ver
specs/024-traspasos-internos-tesoreria/{research,data-model}.md.

`esta_resuelto` es el único punto que conoce los 6 estados posibles de un
movimiento (los 4 de 023 más `traspaso_interno` y `sin_documento`). Consulta el vínculo activo
de `TraspasosInternosTesoreria` con el mismo `SELECT` inlineado de
data-model.md ("Vínculo activo de un movimiento") **en vez de importar**
`traspasos_internos_tesoreria.repository`: ese módulo sí necesita llamar a
esta función (para el gate simétrico de FR-006), y una dependencia circular
entre ambos — aunque funcionara con un import diferido — es un acoplamiento
evitable (remediación I1 de `/speckit-analyze`, 024).
"""

from __future__ import annotations

from src.db.connection import fetch_one
from src.features.conciliacion_tesoreria import repository as conciliacion_repository


def _vinculo_activo(medio: str, id_movimiento: int) -> dict | None:
    fila = fetch_one(
        "SELECT TOP 1 MedioA, IdMovimientoA, MedioB, IdMovimientoB, Accion "
        "FROM dbo.TraspasosInternosTesoreria "
        "WHERE (MedioA = ? AND IdMovimientoA = ?) OR (MedioB = ? AND IdMovimientoB = ?) "
        "ORDER BY IdEvento DESC",
        (medio, id_movimiento, medio, id_movimiento),
    )
    if fila is None or fila["Accion"] != "Vincular":
        return None
    return fila


def esta_resuelto(medio: str, id_movimiento: int) -> str:
    """Devuelve uno de: ya_reconocido | conciliado | parcialmente_conciliado |
    traspaso_interno | sin_documento | sin_conciliar. Las excepciones de 026
    se resuelven dentro de calcular_estado, antes de devolver un parcial."""
    estado = conciliacion_repository.calcular_estado(medio, id_movimiento)
    if estado["estado"] != "sin_conciliar":
        return estado["estado"]
    if _vinculo_activo(medio, id_movimiento) is not None:
        return "traspaso_interno"
    return "sin_conciliar"
