"""Parameterized, read-only SQL queries for the Tesoreria module.

Each medio keeps its own table/columns (FR-002) — no unified query. Column
names come from data-model.md, confirmed against INFORMATION_SCHEMA on
2026-09-16. No writes are issued here (constitution principle II, FR-010).
"""

from __future__ import annotations

from datetime import date
from typing import NamedTuple

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime


class MedioConfig(NamedTuple):
    table: str
    id_column: str
    id_field: str
    date_column: str
    select_columns: dict[str, str]  # API field -> SQL column/expression
    extra_join: str | None = None  # optional JOIN appended after `table` (013)


MEDIOS_CONFIG: dict[str, MedioConfig] = {
    "bna": MedioConfig(
        table="dbo.[Movimientos BNA]",
        id_column="IdMovimientoBNA",
        id_field="idMovimientoBNA",
        date_column="[Fecha / Hora Mov#]",
        select_columns={
            "idMovimientoBNA": "IdMovimientoBNA",
            "fechaHora": "[Fecha / Hora Mov#]",
            "concepto": "Concepto",
            "importe": "Importe",
            "idContacto": "IdContacto",
            "contacto": "Contacto",
            "idCarga": "_crm_bna.IdCarga",
        },
        extra_join=(
            "LEFT JOIN dbo.CargasResumenBancario_Movimientos _crm_bna "
            "ON _crm_bna.Banco = 'BNA' AND _crm_bna.IdMovimiento = [Movimientos BNA].IdMovimientoBNA"
        ),
    ),
    "galicia": MedioConfig(
        table="dbo.[Movimientos Galicia]",
        # Calificado con la tabla: sin esto, el JOIN a
        # CargasResumenBancario_Movimientos (que también tiene una columna
        # IdMovimiento) vuelve "IdMovimiento" ambiguo en ORDER BY (encontrado
        # corriendo T025 contra `WC` real, 2026-09-22).
        id_column="[Movimientos Galicia].IdMovimiento",
        id_field="idMovimiento",
        date_column="Fecha",
        select_columns={
            "idMovimiento": "[Movimientos Galicia].IdMovimiento",
            "fecha": "Fecha",
            "descripcion": "[Descripción]",
            "debitos": "[Débitos]",
            "creditos": "[Créditos]",
            "saldo": "Saldo",
            "idContacto": "IdContacto",
            "contacto": "Contacto",
            "idCarga": "_crm_gal.IdCarga",
        },
        extra_join=(
            "LEFT JOIN dbo.CargasResumenBancario_Movimientos _crm_gal "
            "ON _crm_gal.Banco = 'Galicia' AND _crm_gal.IdMovimiento = [Movimientos Galicia].IdMovimiento"
        ),
    ),
    "efectivo": MedioConfig(
        table="dbo.[Pagos efectivo]",
        id_column="IdPagoEfectivo",
        id_field="idPagoEfectivo",
        date_column="Fecha",
        select_columns={
            "idPagoEfectivo": "IdPagoEfectivo",
            "idContacto": "IdContacto",
            "fecha": "Fecha",
            "cuenta": "Cuenta",
            "caja": "Caja",
            "numeroDocumento": "[Numero documento]",
            "importeImputado": "[Importe imputado]",
            "idOperacion": "IdOperacion",
        },
    ),
    "valores-propios": MedioConfig(
        table="dbo.[Valores propios]",
        id_column="IdValor",
        id_field="idValor",
        date_column="[Fecha emision]",
        select_columns={
            "idValor": "IdValor",
            "numeroCheque": "[Numero cheque]",
            "fechaEmision": "[Fecha emision]",
            "fechaVencimiento": "[Fecha vencimiento]",
            "importe": "Importe",
            "cobrado": "Cobrado",
            "fechaCobro": "[Fecha Cobro]",
            "numeroCuenta": "[Numero Cuenta]",
            "comentarios": "Comentarios",
        },
    ),
    "valores-recibidos": MedioConfig(
        table="dbo.[Valores Recibidos]",
        id_column="IdValor",
        id_field="idValor",
        date_column="[Fecha Emision]",
        select_columns={
            "idValor": "IdValor",
            "numeroValor": "[Numero Valor]",
            "banco": "Banco",
            "fechaEmision": "[Fecha Emision]",
            "fechaVencimiento": "[Fecha Vencimiento]",
            "fechaCobro": "[Fecha Cobro]",
            "idEmisor": "IdEmisor",
            "idReceptor": "IdReceptor",
            "importe": "Importe",
            "destino": "Destino",
        },
    ),
    "tarjetas": MedioConfig(
        table="dbo.Tarjetas_Resumenes_Lineas",
        id_column="IdLineaConsumo",
        id_field="idLineaConsumo",
        date_column="FechaCompra",
        select_columns={
            "idLineaConsumo": "IdLineaConsumo",
            "idResumen": "IdResumen",
            "fechaCompra": "FechaCompra",
            "detalle": "Detalle",
            "importe": "Importe",
            "idContacto": "IdContacto",
            "numeroDocumento": "NroDocumento",
        },
    ),
}

MEDIOS = tuple(MEDIOS_CONFIG.keys())


def _select_sql(config: MedioConfig) -> str:
    return ", ".join(f"{sql} AS [{field}]" for field, sql in config.select_columns.items())


def get_movimientos(
    medio: str,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    config = MEDIOS_CONFIG[medio]

    where_clauses: list[str] = []
    params: list = []
    if fecha_desde:
        where_clauses.append(f"{config.date_column} >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append(f"{config.date_column} <= ?")
        params.append(as_sql_datetime(fecha_hasta))
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    join_sql = config.extra_join or ""
    count_sql = f"SELECT COUNT(*) AS total FROM {config.table} {join_sql} {where_sql}"
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT {_select_sql(config)}
        FROM {config.table}
        {join_sql}
        {where_sql}
        ORDER BY {config.date_column} DESC, {config.id_column} DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return rows, total


def get_movimiento(medio: str, id_movimiento: int) -> dict | None:
    """Fetch a single movimiento row (all select_columns) by its id."""
    config = MEDIOS_CONFIG[medio]
    sql = f"""
        SELECT {_select_sql(config)}
        FROM {config.table}
        {config.extra_join or ""}
        WHERE {config.id_column} = ?
    """
    return fetch_one(sql, (id_movimiento,))


def listar_cargas(banco: str) -> list[dict]:
    """Historial de cargas confirmadas de un banco (013 US4, FR-009).

    El alias SQL de esta columna NO puede ser "insertados": ese texto
    contiene la subcadena "INSERT", que `_assert_read_only` (connection.py)
    rechaza en cualquier SELECT sin importar dónde aparezca — se alias como
    `cargados` y se renombra a la clave pública `insertados` después de
    leer, ya en Python.
    """
    tabla_banco = "BNA" if banco == "bna" else "Galicia"
    sql = """
        SELECT IdCarga AS idCarga, NombreArchivo AS nombreArchivo,
               FechaHoraCarga AS fechaHoraCarga, CantidadCargados AS cargados,
               CantidadOmitidosDuplicado AS omitidosDuplicado,
               CantidadOmitidosIncompletos AS omitidosIncompletos
        FROM dbo.CargasResumenBancario
        WHERE Banco = ?
        ORDER BY FechaHoraCarga DESC
    """
    rows = fetch_all(sql, (tabla_banco,))
    for row in rows:
        row["insertados"] = row.pop("cargados")
    return rows
