"""Parameterized, read-only SQL queries for the Arrendamientos module.

UI term is "Arrendamiento"; SQL tables are named `Alquileres` (legacy
naming, kept as-is per constitution principle I — no schema changes).
"""

from __future__ import annotations

from src.db.connection import execute_write, fetch_all, fetch_one
from src.db.pagination import offset_for

# Enum real confirmado en el combo del formulario Access
# (`Subformulario Detalle Cobro Alquiler`): solo estos 2 valores.
ESTADOS_CUOTA_VALIDOS = ("Pendiente", "Cobrado")


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
            a.[Cantidad de cuotas] AS cantidadCuotas,
            a.[Tipo de pago] AS tipoDePago,
            a.[Superficie total] AS superficieTotal,
            a.[Retencion Ganancias] AS retencionGanancias
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


def set_estado_cuota(id_cobro_alquiler: int, estado: str) -> bool:
    """Marca una cuota de arrendamiento como Pendiente/Cobrado.

    Primera funcionalidad de escritura real de la app (2026-09-17,
    decisión explícita del usuario) — corre exclusivamente contra `WC`
    (ver `execute_write`/`_assert_target_is_wc` en `src/db/connection.py`;
    nunca contra `LaHerencia`).
    """
    if estado not in ESTADOS_CUOTA_VALIDOS:
        raise ValueError(f"Estado inválido: {estado!r}. Valores válidos: {ESTADOS_CUOTA_VALIDOS}")
    rows_affected = execute_write(
        "UPDATE dbo.[Detalle Cobro Alquiler] SET Estado = ? WHERE IdCobroAlquiler = ?",
        (estado, id_cobro_alquiler),
    )
    return rows_affected > 0


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
