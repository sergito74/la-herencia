"""Parameterized, read-only SQL queries for the Arrendamientos module.

UI term is "Arrendamiento"; SQL tables are named `Alquileres` (legacy
naming, kept as-is per constitution principle I — no schema changes).
"""

from __future__ import annotations

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for


def search_arrendamientos(
    contacto: str | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    where_clauses: list[str] = []
    params: list = []

    if contacto:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{contacto}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.Alquileres a
        LEFT JOIN dbo.Contactos c ON c.IdContacto = a.IdContacto
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            a.IdAlquiler AS idAlquiler,
            a.Fecha AS fecha,
            a.[Inicio del periodo] AS inicioPeriodo,
            a.[Fin del periodo] AS finPeriodo,
            c.[Razon Social] AS contacto,
            a.[Importe total del contrato] AS importeTotalContrato,
            a.[Cantidad de cuotas] AS cantidadCuotas
        FROM dbo.Alquileres a
        LEFT JOIN dbo.Contactos c ON c.IdContacto = a.IdContacto
        {where_sql}
        ORDER BY a.Fecha DESC, a.IdAlquiler DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    contratos = []
    for row in rows:
        contrato = dict(row)
        contrato["cobros"] = get_cobros_alquiler(row["idAlquiler"])
        contratos.append(contrato)
    return contratos, total


def get_cobros_alquiler(id_alquiler: int) -> list[dict]:
    sql = """
        SELECT
            IdCobroAlquiler AS idCobroAlquiler,
            [Numero Cuota] AS numeroCuota,
            [Importe Cuota] AS importeCuota,
            Estado AS estado,
            [Fecha vencimiento] AS fechaVencimiento
        FROM dbo.[Detalle Cobro Alquiler]
        WHERE IdAlquiler = ?
        ORDER BY [Numero Cuota] ASC
    """
    return fetch_all(sql, (id_alquiler,))


def get_arrendamiento_referencia(id_alquiler: int) -> dict | None:
    sql = """
        SELECT
            a.IdAlquiler AS idAlquiler,
            c.[Razon Social] AS contacto,
            a.[Importe total del contrato] AS importeTotalContrato
        FROM dbo.Alquileres a
        LEFT JOIN dbo.Contactos c ON c.IdContacto = a.IdContacto
        WHERE a.IdAlquiler = ?
    """
    return fetch_one(sql, (id_alquiler,))
