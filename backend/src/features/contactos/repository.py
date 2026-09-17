"""Parameterized SQL queries for the Contactos module (master data).

Reads work against either database; writes (`create_contacto`,
`update_contacto`) go exclusively to `WC` via `execute_write` (regla de
oro, ver memory.md).
"""

from __future__ import annotations

from src.db.connection import execute_insert_returning_id, execute_write, fetch_all, fetch_one
from src.db.pagination import offset_for


def search_contactos(
    q: str | None,
    tipo_contacto: str | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    where_clauses: list[str] = []
    params: list = []

    if q:
        where_clauses.append("([Razon Social] LIKE ? OR [CUIT/CUIL] LIKE ?)")
        params.append(f"%{q}%")
        params.append(f"%{q}%")

    if tipo_contacto:
        where_clauses.append("[Tipo Contacto] = ?")
        params.append(tipo_contacto)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"SELECT COUNT(*) AS total FROM dbo.Contactos {where_sql}"
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            IdContacto AS idContacto,
            [Razon Social] AS razonSocial,
            [Tipo Contacto] AS tipoContacto,
            [CUIT/CUIL] AS cuit,
            EsContratistaLabores AS esContratistaLabores
        FROM dbo.Contactos
        {where_sql}
        ORDER BY [Razon Social] ASC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return rows, total


def get_contacto(id_contacto: int) -> dict | None:
    sql = """
        SELECT
            IdContacto AS idContacto,
            [Razon Social] AS razonSocial,
            [Tipo Contacto] AS tipoContacto,
            [CUIT/CUIL] AS cuit,
            EsContratistaLabores AS esContratistaLabores
        FROM dbo.Contactos
        WHERE IdContacto = ?
    """
    return fetch_one(sql, (id_contacto,))


def create_contacto(
    razon_social: str,
    tipo_contacto: str,
    cuit: str | None,
    es_contratista_labores: bool,
) -> int:
    """Inserta un contacto nuevo en `WC` y devuelve el `IdContacto` generado."""
    return execute_insert_returning_id(
        """
        INSERT INTO dbo.Contactos ([Razon Social], [Tipo Contacto], [CUIT/CUIL], EsContratistaLabores)
        OUTPUT INSERTED.IdContacto
        VALUES (?, ?, ?, ?)
        """,
        (razon_social, tipo_contacto, cuit, es_contratista_labores),
    )


def update_contacto(
    id_contacto: int,
    razon_social: str,
    tipo_contacto: str,
    cuit: str | None,
    es_contratista_labores: bool,
) -> bool:
    rows_affected = execute_write(
        """
        UPDATE dbo.Contactos
        SET [Razon Social] = ?, [Tipo Contacto] = ?, [CUIT/CUIL] = ?, EsContratistaLabores = ?
        WHERE IdContacto = ?
        """,
        (razon_social, tipo_contacto, cuit, es_contratista_labores, id_contacto),
    )
    return rows_affected > 0
