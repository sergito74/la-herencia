"""Heuristic origin reference: tesoreria movimiento -> compra candidata(s).

Pure, read-only matching by IdContacto + fecha + importe against
dbo.Compras (via vw_MovimientosCuenta_Base for the debt amount actually
posted for that compra). No explicit foreign key links tesoreria to
compras, so this never picks a single candidate by default (FR-005).

`valores-propios` has no contact column at all (confirmed against
INFORMATION_SCHEMA 2026-09-16). La clarification original (2026-09-16)
decía que por eso debía devolver siempre "sin_coincidencia" sin consultar
nada — revisado 2026-09-28 a pedido del usuario: la columna `Comentarios`
en la práctica trae el nombre del proveedor en texto libre (ej. "Madelan",
"Gentos"), así que se resuelve el contacto por coincidencia de texto contra
`Contactos.[Razon Social]` antes de aplicar la misma ventana de
fecha/importe que el resto de los medios. Si el texto no resuelve a
exactamente un contacto (cero o varios), sigue devolviendo
"sin_coincidencia" — nunca elige uno al azar.
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import fetch_all
from src.db.params import as_sql_datetime
from src.features.tesoreria.repository import get_movimiento

SIN_COINCIDENCIA = "sin_coincidencia"
COINCIDENCIA_UNICA = "coincidencia_unica"
AMBIGUA = "ambigua"


def _anchor_bna(row: dict) -> tuple[int | None, date | None, float | None]:
    fecha_hora = row.get("fechaHora")
    fecha = fecha_hora.date() if isinstance(fecha_hora, datetime) else fecha_hora
    importe = row.get("importe")
    return row.get("idContacto"), fecha, abs(float(importe)) if importe is not None else None


def _anchor_galicia(row: dict) -> tuple[int | None, date | None, float | None]:
    importe = row.get("debitos") or row.get("creditos")
    return row.get("idContacto"), row.get("fecha"), importe


def _anchor_mercado_libre(row: dict) -> tuple[int | None, date | None, float | None]:
    importe = row.get("importe")
    return row.get("idContacto"), row.get("fecha"), abs(float(importe)) if importe is not None else None


def _anchor_efectivo(row: dict) -> tuple[int | None, date | None, float | None]:
    return row.get("idContacto"), row.get("fecha"), row.get("importeImputado")


def _anchor_valores_recibidos(row: dict) -> tuple[int | None, date | None, float | None]:
    return row.get("idEmisor"), row.get("fechaEmision"), row.get("importe")


def _anchor_tarjetas(row: dict) -> tuple[int | None, date | None, float | None]:
    return row.get("idContacto"), row.get("fechaCompra"), row.get("importe")


def _resolver_contacto_por_texto(comentario: str | None) -> int | None:
    """Resuelve un IdContacto a partir del texto libre de `Comentarios`
    (valores-propios). Coincidencia por substring en cualquier sentido
    (el comentario suele ser más corto que la razón social completa, ej.
    "Gentos" vs "Gentos S.A."). Se exige un mínimo de 3 caracteres útiles
    para no matchear contra textos triviales, y se descarta si el texto
    resuelve a más de un contacto — nunca elige uno al azar."""
    if not comentario or len(comentario.strip()) < 3:
        return None
    sql = """
        SELECT IdContacto AS idContacto
        FROM dbo.Contactos
        WHERE LEN([Razon Social]) >= 3
            AND (CHARINDEX([Razon Social], ?) > 0 OR CHARINDEX(?, [Razon Social]) > 0)
    """
    texto = comentario.strip()
    filas = fetch_all(sql, (texto, texto))
    if len(filas) != 1:
        return None
    return filas[0]["idContacto"]


def _anchor_valores_propios(row: dict) -> tuple[int | None, date | None, float | None]:
    id_contacto = _resolver_contacto_por_texto(row.get("comentarios"))
    return id_contacto, row.get("fechaEmision"), row.get("importe")


_ANCHOR_BY_MEDIO = {
    "bna": _anchor_bna,
    "galicia": _anchor_galicia,
    "mercado-libre": _anchor_mercado_libre,
    "efectivo": _anchor_efectivo,
    "valores-propios": _anchor_valores_propios,
    "valores-recibidos": _anchor_valores_recibidos,
    "tarjetas": _anchor_tarjetas,
}



# En la práctica bancos/tarjetas acreditan con algunos días de desfasaje
# respecto de la fecha de la compra, y los importes pueden diferir por
# centavos de redondeo — un match exacto de fecha e importe (heurística
# original) devolvía "sin_coincidencia" casi siempre aunque el pago
# correspondiera claramente a una compra real. Se relaja a una ventana de
# fecha y una tolerancia de importe, en línea con el criterio ya usado en
# conciliación de tarjetas (tarjetas_resumenes/conciliacion_documentos.py:
# tolerancia en pesos por redondeo, candidatos por cercanía de fecha). Es
# de solo lectura (FR-005: nunca elige una candidata por default), así que
# ampliar la ventana solo puede sumar candidatas a revisar, nunca escribir
# una imputación equivocada.
VENTANA_DIAS = 5
TOLERANCIA_IMPORTE = 1.0


def _buscar_candidatas(id_contacto: int, fecha: date, importe: float) -> list[dict]:
    sql = """
        SELECT
            cmp.IdDeuda AS idCompra,
            cmp.IdContacto AS idContacto,
            cmp.[Nro Documento] AS numeroDocumento,
            c.[Razon Social] AS proveedor,
            v.Fecha AS fecha,
            v.Deuda AS importe
        FROM dbo.Compras cmp
        JOIN dbo.vw_MovimientosCuenta_Base v
            ON v.IdOrigen = cmp.IdDeuda AND v.Origen = 'Compras'
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        WHERE cmp.IdContacto = ?
            AND ABS(DATEDIFF(day, v.Fecha, ?)) <= ?
            AND ABS(v.Deuda - ?) <= ?
        ORDER BY ABS(DATEDIFF(day, v.Fecha, ?)) ASC
    """
    fecha_sql = as_sql_datetime(fecha)
    return fetch_all(
        sql,
        (id_contacto, fecha_sql, VENTANA_DIAS, importe, TOLERANCIA_IMPORTE, fecha_sql),
    )


def buscar_referencia(medio: str, id_movimiento: int) -> dict:
    row = get_movimiento(medio, id_movimiento)
    if row is None:
        return {"estado": SIN_COINCIDENCIA, "candidatas": []}

    id_contacto, fecha, importe = _ANCHOR_BY_MEDIO[medio](row)
    if id_contacto is None or fecha is None or importe is None:
        return {"estado": SIN_COINCIDENCIA, "candidatas": []}

    # pyodbc cannot bind Decimal parameters reliably (SQLBindParameter);
    # normalize to float before querying.
    candidatas = _buscar_candidatas(id_contacto, fecha, float(importe))

    if not candidatas:
        estado = SIN_COINCIDENCIA
    elif len(candidatas) == 1:
        estado = COINCIDENCIA_UNICA
    else:
        estado = AMBIGUA

    return {"estado": estado, "candidatas": candidatas}
