"""Reasignación de contacto en movimientos de cuenta corriente (022).

`ReasignacionesContacto` es insert-only (spec FR-004/FR-013, mismo patrón
que `MovimientosCuentaSocio` en 021): nunca se hace UPDATE/DELETE. La fila
vigente para un `(Origen, IdOrigen)` es siempre la de mayor `IdReasignacion`
— no hace falta una columna de estado mutable. `vw_MovimientosCuenta_Base`
aplica este override vía `OUTER APPLY` (ver
`scripts/aplicar_override_reasignacion_en_vista.py`), por lo que reasignar
nunca escribe en `Movimientos Galicia`/`Movimientos BNA`/`Compras` (FR-014).
"""

from __future__ import annotations

import re

from src.db.connection import execute_write_transaction, fetch_all, fetch_one

ORIGENES_SOPORTADOS = {"Galicia", "Banco Nacion", "Tarjetas", "Conciliación Tesorería"}

# Orígenes con texto libre de descripción — únicos elegibles para la
# detección automática (spec Clarifications 2026-09-25).
_ORIGENES_CON_DESCRIPCION = {
    "Galicia": ("dbo.[Movimientos Galicia]", "IdMovimiento", "Descripción", "Fecha", "Débitos", "Créditos"),
    "Banco Nacion": ("dbo.[Movimientos BNA]", "IdMovimientoBNA", "Concepto", "Fecha / Hora Mov#", "Importe", None),
}

# research.md §5 — términos genéricos bancarios confirmados como ruido por
# el escaneo manual real (35 de 36 candidatos eran esto).
TERMINOS_DE_RUIDO = {
    "BANCO", "GALICIA", "NACION", "ARGENTINA", "BOLIVAR", "BBVA", "CREDICOOP",
    "SOCIEDAD", "ANONIMA", "RESPONSABILIDAD", "LIMITADA", "COMPANIA", "SRL", "SA",
}


def _f(value) -> float:
    return float(value) if value is not None else 0.0


def _origen_no_soportado(origen: str) -> ValueError:
    return ValueError(f"El origen '{origen}' todavía no admite reasignación.")


def _contacto_original(origen: str, id_origen: int) -> int:
    """El contacto tal cual está hoy en la tabla de origen, sin considerar
    ningún override todavía aplicado."""
    if origen == "Galicia":
        fila = fetch_one("SELECT IdContacto FROM dbo.[Movimientos Galicia] WHERE IdMovimiento = ?", (id_origen,))
    elif origen == "Banco Nacion":
        fila = fetch_one("SELECT IdContacto FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA = ?", (id_origen,))
    elif origen == "Tarjetas":
        fila = fetch_one(
            "SELECT c.IdContacto FROM dbo.Tarjetas_Resumenes_Lineas_Compras v "
            "JOIN dbo.Compras c ON c.IdDeuda = v.IdCompra WHERE v.IdVinculo = ?",
            (id_origen,),
        )
    elif origen == "Conciliación Tesorería":
        # 023-conciliacion-tesoreria (FR-008a): un único origen sintético
        # para TODAS las conciliaciones manuales, sin importar de qué medio
        # de Tesorería vinieron — IdOrigen es el IdConciliacion.
        fila = fetch_one(
            "SELECT IdContacto FROM dbo.ConciliacionesTesoreria WHERE IdConciliacion = ?", (id_origen,)
        )
    else:
        raise _origen_no_soportado(origen)
    if fila is None:
        raise ValueError(f"No existe ningún movimiento con origen '{origen}' e IdOrigen {id_origen}.")
    return int(fila["IdContacto"])


def _contacto_efectivo(origen: str, id_origen: int) -> int:
    """El contacto vigente hoy: la última reasignación aplicada, o el
    contacto original si nunca se reasignó (FR-011)."""
    fila = fetch_one(
        "SELECT TOP 1 IdContactoNuevo FROM dbo.ReasignacionesContacto "
        "WHERE Origen = ? AND IdOrigen = ? ORDER BY IdReasignacion DESC",
        (origen, id_origen),
    )
    if fila is not None:
        return int(fila["IdContactoNuevo"])
    return _contacto_original(origen, id_origen)


def reasignar(origen: str, id_origen: int, id_contacto_nuevo: int, usuario: str, motivo: str | None = None) -> dict:
    if origen not in ORIGENES_SOPORTADOS:
        raise _origen_no_soportado(origen)

    contacto_actual = _contacto_efectivo(origen, id_origen)
    if id_contacto_nuevo == contacto_actual:
        raise ValueError("El movimiento ya está asignado a ese contacto.")

    contacto_existe = fetch_one("SELECT 1 AS x FROM dbo.Contactos WHERE IdContacto = ?", (id_contacto_nuevo,))
    if contacto_existe is None:
        raise ValueError(f"El contacto {id_contacto_nuevo} no existe.")

    resultados = execute_write_transaction(
        [
            (
                "INSERT INTO dbo.ReasignacionesContacto "
                "(Origen, IdOrigen, IdContactoAnterior, IdContactoNuevo, Motivo, Usuario) "
                "OUTPUT INSERTED.IdReasignacion "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (origen, id_origen, contacto_actual, id_contacto_nuevo, motivo, usuario),
            ),
        ]
    )
    return _reasignacion_por_id(resultados[0])


def _reasignacion_por_id(id_reasignacion: int) -> dict:
    fila = fetch_one(
        """
        SELECT r.IdReasignacion AS idReasignacion, r.Origen AS origen, r.IdOrigen AS idOrigen,
               r.IdContactoAnterior AS idContactoAnterior, r.IdContactoNuevo AS idContactoNuevo,
               ca.[Razon Social] AS contactoAnterior, cn.[Razon Social] AS contactoNuevo,
               r.Motivo AS motivo, r.Usuario AS usuario, r.Fecha AS fecha
        FROM dbo.ReasignacionesContacto r
        JOIN dbo.Contactos ca ON ca.IdContacto = r.IdContactoAnterior
        JOIN dbo.Contactos cn ON cn.IdContacto = r.IdContactoNuevo
        WHERE r.IdReasignacion = ?
        """,
        (id_reasignacion,),
    )
    assert fila is not None
    return fila


def listar_historial(origen: str | None = None, id_origen: int | None = None) -> list[dict]:
    where = ["1 = 1"]
    params: list = []
    if origen is not None:
        where.append("r.Origen = ?")
        params.append(origen)
    if id_origen is not None:
        where.append("r.IdOrigen = ?")
        params.append(id_origen)

    return fetch_all(
        f"""
        SELECT r.IdReasignacion AS idReasignacion, r.Origen AS origen, r.IdOrigen AS idOrigen,
               r.IdContactoAnterior AS idContactoAnterior, r.IdContactoNuevo AS idContactoNuevo,
               ca.[Razon Social] AS contactoAnterior, cn.[Razon Social] AS contactoNuevo,
               r.Motivo AS motivo, r.Usuario AS usuario, r.Fecha AS fecha
        FROM dbo.ReasignacionesContacto r
        JOIN dbo.Contactos ca ON ca.IdContacto = r.IdContactoAnterior
        JOIN dbo.Contactos cn ON cn.IdContacto = r.IdContactoNuevo
        WHERE {' AND '.join(where)}
        ORDER BY r.Fecha DESC, r.IdReasignacion DESC
        """,
        tuple(params),
    )


# --- Detección de candidatos (US2) ---------------------------------------

_PALABRA_RE = re.compile(r"[A-ZÁÉÍÓÚÑ0-9]+", re.IGNORECASE)


def _palabras_significativas(texto: str) -> set[str]:
    palabras = {p.upper() for p in _PALABRA_RE.findall(texto or "")}
    return {p for p in palabras if len(p) > 3 and p not in TERMINOS_DE_RUIDO}


def _ya_descartado(origen: str, id_origen: int, id_contacto_sugerido: int) -> bool:
    fila = fetch_one(
        "SELECT 1 AS x FROM dbo.CandidatosDescartados "
        "WHERE Origen = ? AND IdOrigen = ? AND IdContactoSugerido = ?",
        (origen, id_origen, id_contacto_sugerido),
    )
    return fila is not None


def detectar_candidatos() -> list[dict]:
    """Solo lectura (FR-009) — nunca escribe. Compara, para cada
    movimiento bancario con contacto asignado, las palabras del nombre de
    otros contactos contra el texto de su descripción (research.md §5)."""
    contactos = fetch_all("SELECT IdContacto, [Razon Social] AS razon FROM dbo.Contactos")
    contacto_palabras = [
        (c["IdContacto"], c["razon"], _palabras_significativas(c["razon"])) for c in contactos
    ]
    contacto_palabras = [(idc, razon, p) for idc, razon, p in contacto_palabras if p]
    contactos_por_id = {c["IdContacto"]: c["razon"] for c in contactos}

    candidatos: list[dict] = []
    for origen, (tabla, columna_id, columna_desc, columna_fecha, columna_importe1, columna_importe2) in _ORIGENES_CON_DESCRIPCION.items():
        columnas_importe = ", ".join(f"[{c}]" for c in (columna_importe1, columna_importe2) if c)
        filas = fetch_all(
            f"""
            SELECT [{columna_id}] AS idOrigen, [{columna_fecha}] AS fecha, [{columna_desc}] AS descripcion,
                   IdContacto AS idContactoActual, {columnas_importe}
            FROM {tabla}
            WHERE IdContacto IS NOT NULL
            """
        )
        for fila in filas:
            desc_palabras = _palabras_significativas(fila["descripcion"] or "")
            if not desc_palabras:
                continue
            id_origen = fila["idOrigen"]
            contacto_actual = _contacto_efectivo(origen, id_origen)
            if columna_importe2:
                importe = _f(fila.get(columna_importe1)) or _f(fila.get(columna_importe2))
            else:
                importe = _f(fila.get(columna_importe1))
            for idc, razon, palabras in contacto_palabras:
                if idc == contacto_actual:
                    continue
                if not (palabras <= desc_palabras):
                    continue
                if _ya_descartado(origen, id_origen, idc):
                    continue
                candidatos.append(
                    {
                        "origen": origen,
                        "idOrigen": id_origen,
                        "fecha": fila["fecha"],
                        "descripcion": fila["descripcion"],
                        "importe": importe,
                        "idContactoActual": contacto_actual,
                        "contactoActual": contactos_por_id.get(contacto_actual),
                        "idContactoSugerido": idc,
                        "contactoSugerido": razon,
                    }
                )
    return candidatos


def descartar_candidato(origen: str, id_origen: int, id_contacto_sugerido: int, usuario: str) -> None:
    """Idempotente (FR-010): descartar dos veces el mismo candidato no
    falla ni duplica."""
    if _ya_descartado(origen, id_origen, id_contacto_sugerido):
        return
    execute_write_transaction(
        [
            (
                "INSERT INTO dbo.CandidatosDescartados (Origen, IdOrigen, IdContactoSugerido, Usuario) "
                "VALUES (?, ?, ?, ?)",
                (origen, id_origen, id_contacto_sugerido, usuario),
            ),
        ]
    )
