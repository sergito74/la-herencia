"""Parameterized SQL queries for the Contactos module (master data).

Reads work against either database; writes (`create_contacto`,
`update_contacto`) go exclusively to `WC` via `execute_write` (regla de
oro, ver memory.md).
"""

from __future__ import annotations

import re
import unicodedata

from src.db.connection import atomic_reconciliation, execute_insert_returning_id, execute_write, fetch_all, fetch_one
from src.db.pagination import offset_for


def search_contactos(
    q: str | None,
    tipo_contacto: list[str] | None,
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
        placeholders = ", ".join("?" for _ in tipo_contacto)
        where_clauses.append(f"[Tipo Contacto] IN ({placeholders})")
        params.extend(tipo_contacto)

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


def normalizar_nombre(nombre: str) -> str:
    texto = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().upper()
    clave = re.sub(r"[^A-Z0-9]", "", texto)
    return "RUTASSURATLANTICOSA" if clave == "CORRESUR" else clave


def _exigir_identidad_unica(nombre: str, cuit: str | None, excluir: int | None = None) -> None:
    clave = normalizar_nombre(nombre)
    fiscal = re.sub(r"\D", "", cuit or "")
    filas = fetch_all("SELECT TOP (10000) IdContacto AS id, [Razon Social] AS nombre, [CUIT/CUIL] AS cuit FROM dbo.Contactos ORDER BY IdContacto")
    if len(filas) >= 10000:
        raise ValueError("No se pudo verificar si el contacto ya existe. Revisá el padrón antes de continuar.")
    for fila in filas:
        if fila["id"] == excluir:
            continue
        mismo_cuit = fiscal and fiscal == re.sub(r"\D", "", fila["cuit"] or "")
        if mismo_cuit or (clave and clave == normalizar_nombre(fila["nombre"] or "")):
            raise ValueError(f"Ya existe el contacto {fila['nombre']}. Usá ese contacto para evitar duplicarlo.")


@atomic_reconciliation
def create_contacto(
    razon_social: str,
    tipo_contacto: str,
    cuit: str | None,
    es_contratista_labores: bool,
) -> int:
    """Inserta un contacto nuevo en `WC` y devuelve el `IdContacto` generado."""
    if normalizar_nombre(razon_social) == "RUTASSURATLANTICOSA":
        razon_social = "Rutas Sur Atlantico S.A."
    _exigir_identidad_unica(razon_social, cuit)
    return execute_insert_returning_id(
        """
        INSERT INTO dbo.Contactos ([Razon Social], [Tipo Contacto], [CUIT/CUIL], EsContratistaLabores)
        OUTPUT INSERTED.IdContacto
        VALUES (?, ?, ?, ?)
        """,
        (razon_social, tipo_contacto, cuit, es_contratista_labores),
    )


@atomic_reconciliation
def update_contacto(
    id_contacto: int,
    razon_social: str,
    tipo_contacto: str,
    cuit: str | None,
    es_contratista_labores: bool,
) -> bool:
    if normalizar_nombre(razon_social) == "RUTASSURATLANTICOSA":
        razon_social = "Rutas Sur Atlantico S.A."
    _exigir_identidad_unica(razon_social, cuit, id_contacto)
    rows_affected = execute_write(
        """
        UPDATE dbo.Contactos
        SET [Razon Social] = ?, [Tipo Contacto] = ?, [CUIT/CUIL] = ?, EsContratistaLabores = ?
        WHERE IdContacto = ?
        """,
        (razon_social, tipo_contacto, cuit, es_contratista_labores, id_contacto),
    )
    return rows_affected > 0
