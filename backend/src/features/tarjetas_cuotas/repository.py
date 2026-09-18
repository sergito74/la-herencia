"""Parameterized SQL queries for the Tarjetas_Cuotas module.

Cabecera `dbo.[Tarjetas de Credito]` + detalle `dbo.[Cuotas Tarjetas de
Credito]`. Sin columna `IdTarjeta` — no vinculada a una tarjeta del
catálogo (data-model.md, decisión de producto). `Cobrado` es
`nvarchar(1)` ('S'/'N'), no `bit` — mapeado explícitamente. Escribe
exclusivamente contra `WC` vía `execute_write_transaction`.
"""

from __future__ import annotations

from datetime import date

from src.db.connection import execute_write, execute_write_transaction, fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime
from src.features.tarjetas_cuotas.calculo_cuotas import generar_cronograma


def _cobrado_bool(valor) -> bool:
    return valor == "S"


def existe_contacto(id_contacto: int) -> bool:
    return fetch_one("SELECT 1 FROM dbo.Contactos WHERE IdContacto = ?", (id_contacto,)) is not None


def validar_compra(id_contacto: int) -> list[str]:
    errores: list[str] = []
    if not existe_contacto(id_contacto):
        errores.append(f"El contacto {id_contacto} no existe.")
    return errores


def search_compras(
    id_contacto: int | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """FR-006 (Clarifications 2026-09-18): sin ningún filtro, no ejecuta la
    query principal (devuelve vacío)."""
    if not (id_contacto or fecha_desde or fecha_hasta):
        return [], 0

    where_clauses: list[str] = []
    params: list = []
    if id_contacto:
        where_clauses.append("t.IdContacto = ?")
        params.append(id_contacto)
    if fecha_desde:
        where_clauses.append("t.Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("t.Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}"

    total_row = fetch_one(
        f"SELECT COUNT(*) AS total FROM dbo.[Tarjetas de Credito] t {where_sql}", tuple(params)
    )
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            t.IdPagoTarjeta AS idPagoTarjeta, t.IdContacto AS idContacto, c.[Razon Social] AS contacto,
            t.Fecha AS fecha, t.[Nro Comprobante] AS nroComprobante, t.Cuotas AS cantidadCuotas
        FROM dbo.[Tarjetas de Credito] t
        LEFT JOIN dbo.Contactos c ON c.IdContacto = t.IdContacto
        {where_sql}
        ORDER BY t.Fecha DESC, t.IdPagoTarjeta DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    items = []
    for row in rows:
        cuotas = get_cuotas(row["idPagoTarjeta"])
        cobradas = sum(1 for c in cuotas if c["cobrado"])
        items.append(
            {
                **row,
                "cuotasCobradas": cobradas,
                "cuotasPendientes": len(cuotas) - cobradas,
            }
        )
    return items, total


def get_detalle(id_pago_tarjeta: int) -> dict | None:
    sql = """
        SELECT
            t.IdPagoTarjeta AS idPagoTarjeta, t.IdContacto AS idContacto, c.[Razon Social] AS contacto,
            t.Fecha AS fecha, t.[Nro Comprobante] AS nroComprobante, t.Cuotas AS cantidadCuotas
        FROM dbo.[Tarjetas de Credito] t
        LEFT JOIN dbo.Contactos c ON c.IdContacto = t.IdContacto
        WHERE t.IdPagoTarjeta = ?
    """
    return fetch_one(sql, (id_pago_tarjeta,))


def get_cuotas(id_pago_tarjeta: int) -> list[dict]:
    sql = """
        SELECT
            IdAuto AS idCuota, [Cuota nro] AS numeroCuota, [Fecha Vencimiento] AS fechaVencimiento,
            Importe AS importe, Cobrado AS cobrado
        FROM dbo.[Cuotas Tarjetas de Credito]
        WHERE IdPagoTarjeta = ?
        ORDER BY [Cuota nro] ASC
    """
    rows = fetch_all(sql, (id_pago_tarjeta,))
    return [{**row, "cobrado": _cobrado_bool(row["cobrado"])} for row in rows]


def _siguiente_id_auto_base() -> int:
    """`IdAuto` (PK real de `Cuotas Tarjetas de Credito`) NO es identity
    (confirmado contra `WC`: `COLUMNPROPERTY(...,'IsIdentity')` = 0) — hay
    que generarlo a mano, igual que hacía el formulario Access original."""
    row = fetch_one("SELECT COALESCE(MAX(IdAuto), 0) AS maxid FROM dbo.[Cuotas Tarjetas de Credito]")
    return (row["maxid"] or 0) + 1


def _cuota_insert_statement(id_auto: int, cuota: dict, id_pago_tarjeta: int | None = None):
    """`IdCuotaTarjeta` tiene un índice único real y no admite múltiples
    filas en NULL (confirmado contra `WC`) — se genera con el patrón real
    de los datos históricos, `'CUOT' + IdAuto` (ej. `CUOT183`)."""

    def build(results: list) -> tuple[str, tuple]:
        pago_id = id_pago_tarjeta if id_pago_tarjeta is not None else results[0]
        sql = (
            "INSERT INTO dbo.[Cuotas Tarjetas de Credito] "
            "(IdAuto, IdCuotaTarjeta, IdPagoTarjeta, [Cuota nro], [Fecha Vencimiento], Importe, Cobrado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        return sql, (
            id_auto,
            f"CUOT{id_auto}",
            pago_id,
            cuota["numeroCuota"],
            as_sql_datetime(cuota["fechaVencimiento"]),
            cuota["importe"],
            "S" if cuota["cobrado"] else "N",
        )

    return build


def create_compra(cabecera: dict) -> int:
    errores = validar_compra(cabecera["idContacto"])
    if errores:
        raise ValueError(errores)

    cronograma = generar_cronograma(cabecera["fecha"], cabecera["importeTotal"], cabecera["cantidadCuotas"])

    def cabecera_insert(_results: list) -> tuple[str, tuple]:
        sql = (
            "INSERT INTO dbo.[Tarjetas de Credito] (IdContacto, Fecha, [Nro Comprobante], Cuotas) "
            "OUTPUT INSERTED.IdPagoTarjeta VALUES (?, ?, ?, ?)"
        )
        return sql, (
            cabecera["idContacto"],
            as_sql_datetime(cabecera["fecha"]),
            cabecera["nroComprobante"],
            cabecera["cantidadCuotas"],
        )

    id_auto_base = _siguiente_id_auto_base()
    statements: list = [cabecera_insert]
    for i, cuota in enumerate(cronograma):
        statements.append(_cuota_insert_statement(id_auto_base + i, cuota))

    results = execute_write_transaction(statements)
    return results[0]


def update_compra(id_pago_tarjeta: int, cabecera: dict) -> None:
    """FR-007a (Clarifications 2026-09-18): regenera el cronograma completo
    siempre, sin excepción — cualquier cuota ya cobrada pierde ese estado."""
    errores = validar_compra(cabecera["idContacto"])
    if errores:
        raise ValueError(errores)

    cronograma = generar_cronograma(cabecera["fecha"], cabecera["importeTotal"], cabecera["cantidadCuotas"])

    statements: list = [
        ("DELETE FROM dbo.[Cuotas Tarjetas de Credito] WHERE IdPagoTarjeta = ?", (id_pago_tarjeta,)),
        (
            "UPDATE dbo.[Tarjetas de Credito] SET IdContacto = ?, Fecha = ?, [Nro Comprobante] = ?, Cuotas = ? "
            "WHERE IdPagoTarjeta = ?",
            (
                cabecera["idContacto"],
                as_sql_datetime(cabecera["fecha"]),
                cabecera["nroComprobante"],
                cabecera["cantidadCuotas"],
                id_pago_tarjeta,
            ),
        ),
    ]
    id_auto_base = _siguiente_id_auto_base()
    for i, cuota in enumerate(cronograma):
        statements.append(_cuota_insert_statement(id_auto_base + i, cuota, id_pago_tarjeta=id_pago_tarjeta))

    execute_write_transaction(statements)


def delete_compra(id_pago_tarjeta: int) -> None:
    statements = [
        ("DELETE FROM dbo.[Cuotas Tarjetas de Credito] WHERE IdPagoTarjeta = ?", (id_pago_tarjeta,)),
        ("DELETE FROM dbo.TarjetaCuotasEditLocks WHERE IdPagoTarjeta = ?", (id_pago_tarjeta,)),
        ("DELETE FROM dbo.[Tarjetas de Credito] WHERE IdPagoTarjeta = ?", (id_pago_tarjeta,)),
    ]
    execute_write_transaction(statements)


def marcar_cobrada(id_cuota: int, cobrado: bool) -> None:
    execute_write(
        "UPDATE dbo.[Cuotas Tarjetas de Credito] SET Cobrado = ? WHERE IdAuto = ?",
        ("S" if cobrado else "N", id_cuota),
    )
