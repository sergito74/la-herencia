"""Traspasos internos de Tesorería (024) — ver
specs/024-traspasos-internos-tesoreria/{research,data-model}.md.

`TraspasosInternosTesoreria` es insert-only (nunca UPDATE/DELETE), mismo
patrón que `ConciliacionesTesoreria` (023) y `ReasignacionesContacto` (022):
cada fila es un evento (`Vincular`/`Deshacer`). El vínculo activo de un
movimiento nunca se guarda aparte — siempre se recalcula a partir de la fila
de mayor `IdEvento` para ese par.

Este módulo nunca escribe en ninguna cuenta corriente ni en
`vw_MovimientosCuenta_Base` (FR-004): vincular dos movimientos como el mismo
traspaso interno no tiene ningún efecto contable, a propósito.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import NamedTuple

from src.db.connection import atomic_reconciliation, execute_write_transaction, fetch_all, fetch_one
from src.features.tesoreria import estado_resolucion

MEDIOS_SOPORTADOS = (
    "bna",
    "galicia",
    "mercado-libre",
    "efectivo",
    "valores-propios",
    "valores-recibidos",
)


class _MedioInfo(NamedTuple):
    tabla: str
    id_col: str
    fecha_col: str
    importe_expr: str
    descripcion_expr: str


_MEDIOS: dict[str, _MedioInfo] = {
    "bna": _MedioInfo("dbo.[Movimientos BNA]", "IdMovimientoBNA", "[Fecha / Hora Mov#]", "Importe", "Concepto"),
    "galicia": _MedioInfo(
        "dbo.[Movimientos Galicia]", "IdMovimiento", "Fecha",
        "(ISNULL([Créditos], 0) - ISNULL([Débitos], 0))", "[Descripción]",
    ),
    "mercado-libre": _MedioInfo("dbo.[Movimientos Mercado Libre]", "IdMovimiento", "Fecha", "Importe", "Descripcion"),
    "efectivo": _MedioInfo("dbo.[Pagos efectivo]", "IdPagoEfectivo", "Fecha", "[Importe imputado]", "Cuenta"),
    "valores-propios": _MedioInfo("dbo.[Valores propios]", "IdValor", "[Fecha emision]", "Importe", "Comentarios"),
    "valores-recibidos": _MedioInfo("dbo.[Valores Recibidos]", "IdValor", "[Fecha Emision]", "Importe", "Destino"),
}

# research.md §3: ventana ±5 días, tolerancia ±$1, verificada contra el caso
# real (ML↔Galicia, mismo día, mismo importe exacto).
VENTANA_DIAS = 5
TOLERANCIA_IMPORTE = 1.0


def _as_date(valor) -> date:
    """Cada tabla de origen guarda su columna de fecha con un tipo SQL
    distinto (`date` vs `datetime`), y pyodbc puede además devolver un valor
    ya en texto (visto contra `WC` real, 2026-09-29, corriendo T021a) — restar
    tipos mixtos revienta con `TypeError`, así que todo se normaliza acá."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, str):
        return datetime.fromisoformat(valor[:10]).date()
    return valor


def _info(medio: str) -> _MedioInfo:
    if medio not in _MEDIOS:
        raise ValueError(f"El medio '{medio}' no admite traspasos internos (Tarjetas no está soportado, FR-002).")
    return _MEDIOS[medio]


def _movimiento_referencia(medio: str, id_movimiento: int) -> dict:
    info = _info(medio)
    fila = fetch_one(
        f"SELECT {info.fecha_col} AS fecha, {info.descripcion_expr} AS descripcion, {info.importe_expr} AS importe "
        f"FROM {info.tabla} WHERE {info.id_col} = ?",
        (id_movimiento,),
    )
    if fila is None:
        raise ValueError(f"No existe ningún movimiento '{medio}' con id {id_movimiento}.")
    return {"medio": medio, "idMovimiento": id_movimiento, **fila}


def vinculo_activo(medio: str, id_movimiento: int) -> dict | None:
    """La fila de mayor `IdEvento` para este movimiento (como A o como B);
    `None` si no existe ninguna o si la más reciente es `Deshacer`
    (data-model.md, "Vínculo activo de un movimiento")."""
    fila = fetch_one(
        "SELECT TOP 1 IdEvento, MedioA, IdMovimientoA, MedioB, IdMovimientoB, Accion, Usuario, Fecha "
        "FROM dbo.TraspasosInternosTesoreria "
        "WHERE (MedioA = ? AND IdMovimientoA = ?) OR (MedioB = ? AND IdMovimientoB = ?) "
        "ORDER BY IdEvento DESC",
        (medio, id_movimiento, medio, id_movimiento),
    )
    if fila is None or fila["Accion"] != "Vincular":
        return None
    return fila


def estado_vinculo(medio: str, id_movimiento: int) -> dict:
    """Estado para el endpoint GET: contraparte si está vinculado, o
    candidatas sugeridas si no está vinculado ni resuelto por otra vía."""
    _info(medio)  # valida el medio antes de nada
    activo = vinculo_activo(medio, id_movimiento)
    if activo is not None:
        es_a = activo["MedioA"] == medio and activo["IdMovimientoA"] == id_movimiento
        medio_c = activo["MedioB"] if es_a else activo["MedioA"]
        id_c = activo["IdMovimientoB"] if es_a else activo["IdMovimientoA"]
        return {
            "vinculado": True,
            "contraparte": _movimiento_referencia(medio_c, id_c),
            "candidatas": [],
            "idEvento": activo["IdEvento"],
            "usuario": activo["Usuario"],
            "fecha": activo["Fecha"],
        }
    candidatas: list[dict] = []
    if estado_resolucion.esta_resuelto(medio, id_movimiento) == "sin_conciliar":
        candidatas = sugerir_candidatas(medio, id_movimiento)
    return {"vinculado": False, "contraparte": None, "candidatas": candidatas}


def sugerir_candidatas(medio: str, id_movimiento: int) -> list[dict]:
    """Movimientos de los otros medios dentro de ±5 días y ±$1 de importe
    (research.md §3) — sin exigir coincidencia de signo entre medios."""
    origen = _movimiento_referencia(medio, id_movimiento)
    importe_abs = abs(round(float(origen["importe"] or 0), 2))
    fecha = origen["fecha"]

    resultado: list[dict] = []
    for otro_medio, info in _MEDIOS.items():
        if otro_medio == medio:
            continue
        filas = fetch_all(
            f"SELECT {info.id_col} AS idMovimiento, {info.fecha_col} AS fecha, "
            f"{info.descripcion_expr} AS descripcion, {info.importe_expr} AS importe "
            f"FROM {info.tabla} "
            f"WHERE ABS(DATEDIFF(day, {info.fecha_col}, ?)) <= ? "
            f"AND ABS(ABS({info.importe_expr}) - ?) <= ?",
            (fecha, VENTANA_DIAS, importe_abs, TOLERANCIA_IMPORTE),
        )
        for fila in filas:
            resultado.append({"medio": otro_medio, **fila})
    fecha_origen = _as_date(fecha)
    resultado.sort(
        key=lambda c: (
            abs((_as_date(c["fecha"]) - fecha_origen).days),
            abs(abs(float(c["importe"] or 0)) - importe_abs),
        )
    )
    return resultado


@atomic_reconciliation
def vincular(medio_a: str, id_a: int, medio_b: str, id_b: int, usuario: str) -> dict:
    _info(medio_a)
    _info(medio_b)
    if medio_a == medio_b and id_a == id_b:
        raise ValueError("No se puede vincular un movimiento consigo mismo.")
    _movimiento_referencia(medio_a, id_a)
    _movimiento_referencia(medio_b, id_b)

    # Recalculado en el momento de escribir, no con el estado que el cliente
    # vio al abrir la pantalla (FR-012: dos usuarios vinculando a la vez).
    estado_a = estado_resolucion.esta_resuelto(medio_a, id_a)
    if estado_a != "sin_conciliar":
        raise ValueError(f"El movimiento '{medio_a}' {id_a} ya está resuelto ({estado_a}) — no se puede vincular de nuevo.")
    estado_b = estado_resolucion.esta_resuelto(medio_b, id_b)
    if estado_b != "sin_conciliar":
        raise ValueError(
            f"El movimiento '{medio_b}' {id_b} (la contraparte elegida) ya está resuelto ({estado_b}) — "
            "no se puede vincular de nuevo."
        )

    resultados = execute_write_transaction(
        [
            (
                "INSERT INTO dbo.TraspasosInternosTesoreria "
                "(MedioA, IdMovimientoA, MedioB, IdMovimientoB, Accion, Usuario) "
                "OUTPUT INSERTED.IdEvento VALUES (?, ?, ?, ?, 'Vincular', ?)",
                (medio_a, id_a, medio_b, id_b, usuario),
            ),
        ]
    )
    id_evento = resultados[0]
    return {
        "vinculado": True,
        "contraparte": _movimiento_referencia(medio_b, id_b),
        "candidatas": [],
        "idEvento": id_evento,
        "usuario": usuario,
        "fecha": fetch_one("SELECT Fecha AS f FROM dbo.TraspasosInternosTesoreria WHERE IdEvento = ?", (id_evento,))["f"],
    }


@atomic_reconciliation
def deshacer(medio: str, id_movimiento: int, usuario: str) -> dict:
    activo = vinculo_activo(medio, id_movimiento)
    if activo is None:
        raise ValueError(f"El movimiento '{medio}' {id_movimiento} no tiene ningún vínculo de traspaso interno activo para deshacer.")

    execute_write_transaction(
        [
            (
                "INSERT INTO dbo.TraspasosInternosTesoreria "
                "(MedioA, IdMovimientoA, MedioB, IdMovimientoB, Accion, Usuario) "
                "OUTPUT INSERTED.IdEvento VALUES (?, ?, ?, ?, 'Deshacer', ?)",
                (activo["MedioA"], activo["IdMovimientoA"], activo["MedioB"], activo["IdMovimientoB"], usuario),
            ),
        ]
    )
    return {"vinculado": False, "contraparte": None, "candidatas": []}
