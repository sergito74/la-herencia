"""Cola de revisión de la migración de Cajas Giamigli (027). 100% de
solo lectura — insertar/marcar casos es tarea de los scripts de
migración, no de este módulo (contracts/api.md)."""

from __future__ import annotations

from src.db.connection import fetch_all


def listar_casos_a_revisar(resuelto: bool | None) -> list[dict]:
    where = ""
    params: tuple = ()
    if resuelto is not None:
        where = "WHERE Resuelto = ?"
        params = (1 if resuelto else 0,)

    sql = f"""
        SELECT
            IdRevision AS idRevision,
            Hoja AS hoja,
            NumeroFila AS numeroFila,
            Motivo AS motivo,
            DatosCrudos AS datosCrudos,
            FechaCarga AS fechaCarga,
            Resuelto AS resuelto
        FROM dbo.MigracionCajasGiamigliRevision
        {where}
        ORDER BY Hoja ASC, NumeroFila ASC
    """
    filas = fetch_all(sql, params)
    return [{**f, "resuelto": bool(f["resuelto"])} for f in filas]
