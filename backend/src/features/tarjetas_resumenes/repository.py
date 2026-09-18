"""Parameterized SQL queries for the Tarjetas_Resumenes module.

Cabecera `dbo.Tarjetas_Resumenes` + líneas `dbo.Tarjetas_Resumenes_Lineas`.
Escribe exclusivamente contra `WC` vía `execute_write_transaction` (ver
src/db/connection.py). Fórmulas confirmadas contra datos reales — ver
specs/008-tarjetas/research.md §5 y data-model.md.
"""

from __future__ import annotations

from datetime import date

from src.db.connection import (
    execute_insert_returning_id,
    execute_write,
    execute_write_transaction,
    fetch_all,
    fetch_one,
)
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime

_CARGOS = [
    "impuestoSellos",
    "gastosAdmin",
    "mantCuenta",
    "renovAnual",
    "promocionBNA",
    "creditoContingente",
    "intFinanc",
    "intCompens",
    "iva105",
    "percepIVA105",
    "iva21",
    "percepIVA21",
    "percepIIBB",
    "ajusteResAnterior",
]

_CABECERA_COLUMNAS = [
    "IdTarjeta",
    "ResumenCodigo",
    "FechaCierre",
    "FechaVencimiento",
    "ArchivoOrigen",
    "ImpuestoSellos",
    "GastosAdmin",
    "MantCuenta",
    "RenovAnual",
    "PromocionBNA",
    "CreditoContingente",
    "IntFinanc",
    "IntCompens",
    "IVA105",
    "PercepIVA105",
    "IVA21",
    "PercepIVA21",
    "PercepIIBB",
    "AjusteResAnterior",
]


def _f(value) -> float:
    """pyodbc devuelve `decimal.Decimal` para columnas decimal/money —
    sin este cast, sumarlas con floats literales rompe con TypeError."""
    return float(value) if value is not None else 0.0


def calcular_total(cabecera: dict, lineas: list[dict]) -> float:
    """`Σ(lineas.Importe) + los 14 cargos de cabecera`, cada término con
    su propio signo (data-model.md, research.md §5) — nunca `ABS()`."""
    total = sum(_f(linea.get("importe")) for linea in lineas)
    for campo in _CARGOS:
        total += _f(cabecera.get(campo))
    return total


def existe_tarjeta(id_tarjeta: int) -> bool:
    return fetch_one("SELECT 1 FROM dbo.Tarjetas WHERE IdTarjeta = ?", (id_tarjeta,)) is not None


def validar_resumen(id_tarjeta: int) -> list[str]:
    errores: list[str] = []
    if not existe_tarjeta(id_tarjeta):
        errores.append(f"La tarjeta {id_tarjeta} no existe.")
    return errores


def search_resumenes(
    id_tarjeta: int | None,
    fecha_cierre_desde: date | None,
    fecha_cierre_hasta: date | None,
    fecha_vencimiento_desde: date | None,
    fecha_vencimiento_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """FR-010: sin ningún filtro, no ejecuta la query principal (devuelve vacío)."""
    if not (
        id_tarjeta
        or fecha_cierre_desde
        or fecha_cierre_hasta
        or fecha_vencimiento_desde
        or fecha_vencimiento_hasta
    ):
        return [], 0

    where_clauses: list[str] = []
    params: list = []
    if id_tarjeta:
        where_clauses.append("r.IdTarjeta = ?")
        params.append(id_tarjeta)
    if fecha_cierre_desde:
        where_clauses.append("r.FechaCierre >= ?")
        params.append(as_sql_datetime(fecha_cierre_desde))
    if fecha_cierre_hasta:
        where_clauses.append("r.FechaCierre <= ?")
        params.append(as_sql_datetime(fecha_cierre_hasta))
    if fecha_vencimiento_desde:
        where_clauses.append("r.FechaVencimiento >= ?")
        params.append(as_sql_datetime(fecha_vencimiento_desde))
    if fecha_vencimiento_hasta:
        where_clauses.append("r.FechaVencimiento <= ?")
        params.append(as_sql_datetime(fecha_vencimiento_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}"

    total_row = fetch_one(
        f"SELECT COUNT(*) AS total FROM dbo.Tarjetas_Resumenes r {where_sql}", tuple(params)
    )
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            r.IdResumen AS idResumen, r.IdTarjeta AS idTarjeta, t.TarjetaNombre AS tarjeta,
            r.ResumenCodigo AS codigo, r.FechaCierre AS fechaCierre, r.FechaVencimiento AS fechaVencimiento
        FROM dbo.Tarjetas_Resumenes r
        LEFT JOIN dbo.Tarjetas t ON t.IdTarjeta = r.IdTarjeta
        {where_sql}
        ORDER BY r.FechaCierre DESC, r.IdResumen DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    items = []
    for row in rows:
        cabecera = get_resumen_detalle(row["idResumen"])
        lineas = get_lineas(row["idResumen"])
        items.append(
            {
                "idResumen": row["idResumen"],
                "idTarjeta": row["idTarjeta"],
                "tarjeta": row["tarjeta"],
                "codigo": row["codigo"],
                "fechaCierre": row["fechaCierre"],
                "fechaVencimiento": row["fechaVencimiento"],
                "totalCalculado": calcular_total(cabecera, lineas) if cabecera else 0.0,
                "soloCabecera": len(lineas) == 0,
            }
        )
    return items, total


def get_resumen_detalle(id_resumen: int) -> dict | None:
    sql = """
        SELECT
            r.IdResumen AS idResumen, r.IdTarjeta AS idTarjeta, t.TarjetaNombre AS tarjeta,
            r.ResumenCodigo AS codigo, r.FechaCierre AS fechaCierre, r.FechaVencimiento AS fechaVencimiento,
            r.ArchivoOrigen AS urlResumenOriginal,
            COALESCE(r.ImpuestoSellos, 0) AS impuestoSellos,
            COALESCE(r.GastosAdmin, 0) AS gastosAdmin,
            COALESCE(r.MantCuenta, 0) AS mantCuenta,
            COALESCE(r.RenovAnual, 0) AS renovAnual,
            COALESCE(r.PromocionBNA, 0) AS promocionBNA,
            COALESCE(r.CreditoContingente, 0) AS creditoContingente,
            COALESCE(r.IntFinanc, 0) AS intFinanc,
            COALESCE(r.IntCompens, 0) AS intCompens,
            COALESCE(r.IVA105, 0) AS iva105,
            COALESCE(r.PercepIVA105, 0) AS percepIVA105,
            COALESCE(r.IVA21, 0) AS iva21,
            COALESCE(r.PercepIVA21, 0) AS percepIVA21,
            COALESCE(r.PercepIIBB, 0) AS percepIIBB,
            COALESCE(r.AjusteResAnterior, 0) AS ajusteResAnterior
        FROM dbo.Tarjetas_Resumenes r
        LEFT JOIN dbo.Tarjetas t ON t.IdTarjeta = r.IdTarjeta
        WHERE r.IdResumen = ?
    """
    return fetch_one(sql, (id_resumen,))


def get_lineas(id_resumen: int) -> list[dict]:
    sql = """
        SELECT
            IdLineaConsumo AS idLineaConsumo, FechaCompra AS fechaCompra, Detalle AS detalle,
            Importe AS importe, FechaVencimientoCompra AS fechaVencimientoCompra,
            IdContacto AS idContacto, NroDocumento AS nroDocumento
        FROM dbo.Tarjetas_Resumenes_Lineas
        WHERE IdResumen = ?
        ORDER BY IdLineaConsumo ASC
    """
    lineas = fetch_all(sql, (id_resumen,))
    for linea in lineas:
        linea["comprasVinculadas"] = get_compras_vinculadas(linea["idLineaConsumo"])
    return lineas


def get_compras_vinculadas(id_linea_consumo: int) -> list[dict]:
    """Facturas/NC/ND reales (`Compras`) que documentan esta línea de
    consumo (punto 4 del feedback del usuario, 2026-09-19) — una línea
    puede tener varias (más de un proveedor, o el pago parcial de una
    compra en cuotas)."""
    sql = """
        SELECT
            v.IdVinculo AS idVinculo, v.IdCompra AS idCompra, v.ImporteImputado AS importeImputado,
            c.[Razon Social] AS proveedor, cmp.[Tipo documento] AS tipoDocumento,
            cmp.[Nro Documento] AS numeroDocumento, cmp.Fecha AS fechaCompra
        FROM dbo.Tarjetas_Resumenes_Lineas_Compras v
        JOIN dbo.Compras cmp ON cmp.IdDeuda = v.IdCompra
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        WHERE v.IdLineaConsumo = ?
        ORDER BY v.IdVinculo ASC
    """
    return fetch_all(sql, (id_linea_consumo,))


def existe_compra(id_compra: int) -> bool:
    return fetch_one("SELECT 1 FROM dbo.Compras WHERE IdDeuda = ?", (id_compra,)) is not None


def auto_vincular_compras(id_resumen: int) -> int:
    """Vincula automáticamente cada línea de consumo sin vínculo todavía
    con la Compra real que coincide exacto en contacto + número de
    documento — sin pedirle nada al usuario (feedback 2026-09-19, punto 4:
    "esto es engorroso, hay que simplificarlo"). El 96% de las líneas
    reales ya traen `IdContacto`/`NroDocumento` cargados desde el resumen
    del banco, y el 86% de esas matchean exacto contra `Compras` — solo
    el resto (proveedor con formato de documento distinto, o la compra
    nunca se cargó en el sistema) necesita intervención manual. Nunca
    vincula si hay más de una Compra candidata (ambigüedad → manual)."""
    creados = 0
    for linea in get_lineas(id_resumen):
        if linea.get("comprasVinculadas"):
            continue
        id_contacto = linea.get("idContacto")
        nro_documento = linea.get("nroDocumento")
        if not id_contacto or not nro_documento:
            continue
        candidatas = fetch_all(
            "SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?",
            (id_contacto, nro_documento),
        )
        if len(candidatas) != 1:
            continue
        vincular_compra(linea["idLineaConsumo"], candidatas[0]["IdDeuda"], linea["importe"])
        creados += 1
    return creados


def vincular_compra(id_linea_consumo: int, id_compra: int, importe_imputado: float) -> int:
    if not existe_compra(id_compra):
        raise ValueError([f"La compra {id_compra} no existe."])
    return execute_insert_returning_id(
        "INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) "
        "OUTPUT INSERTED.IdVinculo VALUES (?, ?, ?)",
        (id_linea_consumo, id_compra, importe_imputado),
    )


def quitar_vinculo_compra(id_vinculo: int) -> None:
    execute_write("DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdVinculo = ?", (id_vinculo,))


def get_pagos(id_resumen: int) -> list[dict]:
    sql = """
        SELECT IdPago AS idPago, Fecha AS fecha, Importe AS importe, Origen AS origen,
               IdMovimientoOrigen AS idMovimientoOrigen
        FROM dbo.Tarjetas_Resumenes_Pagos
        WHERE IdResumen = ?
        ORDER BY Fecha ASC, IdPago ASC
    """
    return fetch_all(sql, (id_resumen,))


def registrar_pago(id_resumen: int, fecha, importe: float, origen: str | None, id_movimiento_origen: int | None) -> int:
    return execute_insert_returning_id(
        "INSERT INTO dbo.Tarjetas_Resumenes_Pagos (IdResumen, Fecha, Importe, Origen, IdMovimientoOrigen) "
        "OUTPUT INSERTED.IdPago VALUES (?, ?, ?, ?, ?)",
        (id_resumen, as_sql_datetime(fecha), importe, origen, id_movimiento_origen),
    )


def eliminar_pago(id_pago: int) -> None:
    execute_write("DELETE FROM dbo.Tarjetas_Resumenes_Pagos WHERE IdPago = ?", (id_pago,))


def hay_resumen_duplicado(id_tarjeta: int, codigo: str, excluir_id_resumen: int | None = None) -> bool:
    """FR-012: advertencia no bloqueante — nunca bloquea el guardado."""
    sql = "SELECT 1 FROM dbo.Tarjetas_Resumenes WHERE IdTarjeta = ? AND ResumenCodigo = ?"
    params: list = [id_tarjeta, codigo]
    if excluir_id_resumen is not None:
        sql += " AND IdResumen <> ?"
        params.append(excluir_id_resumen)
    return fetch_one(sql, tuple(params)) is not None


def _cabecera_params(cabecera: dict) -> tuple:
    return (
        cabecera["idTarjeta"],
        cabecera["codigo"],
        as_sql_datetime(cabecera["fechaCierre"]),
        as_sql_datetime(cabecera["fechaVencimiento"]),
        cabecera.get("urlResumenOriginal"),
        *[cabecera.get(campo) or 0 for campo in _CARGOS],
    )


def _cabecera_insert_statement(cabecera: dict):
    def build(_results: list) -> tuple[str, tuple]:
        columnas_sql = ", ".join(_CABECERA_COLUMNAS)
        placeholders = ", ".join("?" for _ in _CABECERA_COLUMNAS)
        sql = (
            f"INSERT INTO dbo.Tarjetas_Resumenes ({columnas_sql}) "
            f"OUTPUT INSERTED.IdResumen VALUES ({placeholders})"
        )
        return sql, _cabecera_params(cabecera)

    return build


def _cabecera_update_statement(id_resumen: int, cabecera: dict) -> tuple[str, tuple]:
    set_clause = ", ".join(f"{c} = ?" for c in _CABECERA_COLUMNAS)
    sql = f"UPDATE dbo.Tarjetas_Resumenes SET {set_clause} WHERE IdResumen = ?"
    return sql, _cabecera_params(cabecera) + (id_resumen,)


def _linea_insert_statement(linea: dict):
    def build(results: list) -> tuple[str, tuple]:
        id_resumen = results[0]
        sql = (
            "INSERT INTO dbo.Tarjetas_Resumenes_Lineas "
            "(IdResumen, FechaCompra, Detalle, Importe, FechaVencimientoCompra, IdContacto, NroDocumento) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        return sql, (
            id_resumen,
            as_sql_datetime(linea["fechaCompra"]),
            linea["detalle"],
            linea["importe"],
            as_sql_datetime(linea["fechaVencimientoCompra"]) if linea.get("fechaVencimientoCompra") else None,
            linea.get("idContacto"),
            linea.get("nroDocumento"),
        )

    return build


def create_resumen(cabecera: dict, lineas: list[dict]) -> int:
    errores = validar_resumen(cabecera["idTarjeta"])
    if errores:
        raise ValueError(errores)

    statements = [_cabecera_insert_statement(cabecera)]
    for linea in lineas:
        statements.append(_linea_insert_statement(linea))

    results = execute_write_transaction(statements)
    return results[0]


def update_resumen(id_resumen: int, cabecera: dict, lineas: list[dict]) -> None:
    """Reemplazo total de líneas (mismo criterio que el resto de la app).
    Borra primero los vínculos a `Compras` (punto 4 del feedback,
    2026-09-19) — de lo contrario quedarían huérfanos apuntando a un
    `IdLineaConsumo` que ya no existe, perdiendo silenciosamente el
    vínculo cada vez que se edita un resumen."""
    errores = validar_resumen(cabecera["idTarjeta"])
    if errores:
        raise ValueError(errores)

    statements: list = [
        (
            "DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo IN "
            "(SELECT IdLineaConsumo FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdResumen = ?)",
            (id_resumen,),
        ),
        ("DELETE FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdResumen = ?", (id_resumen,)),
        _cabecera_update_statement(id_resumen, cabecera),
    ]
    for linea in lineas:
        statements.append(
            (
                "INSERT INTO dbo.Tarjetas_Resumenes_Lineas "
                "(IdResumen, FechaCompra, Detalle, Importe, FechaVencimientoCompra, IdContacto, NroDocumento) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    id_resumen,
                    as_sql_datetime(linea["fechaCompra"]),
                    linea["detalle"],
                    linea["importe"],
                    as_sql_datetime(linea["fechaVencimientoCompra"]) if linea.get("fechaVencimientoCompra") else None,
                    linea.get("idContacto"),
                    linea.get("nroDocumento"),
                ),
            )
        )
    execute_write_transaction(statements)


def delete_resumen(id_resumen: int) -> None:
    statements = [
        (
            "DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo IN "
            "(SELECT IdLineaConsumo FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdResumen = ?)",
            (id_resumen,),
        ),
        ("DELETE FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdResumen = ?", (id_resumen,)),
        ("DELETE FROM dbo.Tarjetas_Resumenes_Pagos WHERE IdResumen = ?", (id_resumen,)),
        ("DELETE FROM dbo.TarjetaResumenEditLocks WHERE IdResumen = ?", (id_resumen,)),
        ("DELETE FROM dbo.Tarjetas_Resumenes WHERE IdResumen = ?", (id_resumen,)),
    ]
    execute_write_transaction(statements)
