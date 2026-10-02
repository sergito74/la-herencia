"""SQL parametrizado del módulo Impuestos.

Column/table names come from data-model.md, confirmed against the real
schema (INFORMATION_SCHEMA) on 2026-09-16. Nació de solo lectura (005
FR-008); desde 033-alta-impuestos (2026-10-02) permite alta, edición y
baja de boletas en `dbo.Impuestos`. Las retenciones siguen de solo lectura.
"""

from __future__ import annotations

from datetime import date

import re

from src.db.connection import execute_insert_returning_id, execute_write_transaction, fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime


def search_impuestos(
    organismo: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    where_clauses: list[str] = []
    params: list = []

    if organismo:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{organismo}%")
    if fecha_desde:
        where_clauses.append("i.Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("i.Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.Impuestos i
        LEFT JOIN dbo.Contactos c ON c.IdContacto = i.IdOrganismo
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            i.IdImpuesto AS idImpuesto,
            i.Fecha AS fecha,
            ti.[Nombre Impuesto] AS tipoImpuesto,
            i.[Periodo liquidado] AS periodoLiquidado,
            i.[Numero de documento] AS numeroDocumento,
            i.Importe AS importe,
            c.IdContacto AS idOrganismo,
            c.[Razon Social] AS organismo
        FROM dbo.Impuestos i
        LEFT JOIN dbo.[Tipo Impuesto] ti ON ti.IdTipoImpuesto = i.IdTipoImpuesto
        LEFT JOIN dbo.Contactos c ON c.IdContacto = i.IdOrganismo
        {where_sql}
        ORDER BY i.Fecha DESC, i.IdImpuesto DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return rows, total


def get_impuesto_referencia(id_impuesto: int) -> dict | None:
    """Referencia mínima de un impuesto para resolver `Origen`/`IdOrigen`."""
    sql = """
        SELECT
            i.IdImpuesto AS idImpuesto,
            ti.[Nombre Impuesto] AS tipoImpuesto,
            i.Importe AS importe
        FROM dbo.Impuestos i
        LEFT JOIN dbo.[Tipo Impuesto] ti ON ti.IdTipoImpuesto = i.IdTipoImpuesto
        WHERE i.IdImpuesto = ?
    """
    return fetch_one(sql, (id_impuesto,))


def search_retenciones(
    contacto: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    where_clauses: list[str] = []
    params: list = []

    if contacto:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{contacto}%")
    if fecha_desde:
        where_clauses.append("r.Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("r.Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.Retenciones r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            r.IdRetencionSQL AS idRetencion,
            r.[Numero Certificado] AS numeroCertificado,
            r.Fecha AS fecha,
            c.IdContacto AS idContacto,
            c.[Razon Social] AS contacto,
            r.Importe AS importe
        FROM dbo.Retenciones r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        {where_sql}
        ORDER BY r.Fecha DESC, r.IdRetencionSQL DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return rows, total


def get_retencion_referencia(id_retencion: int) -> dict | None:
    sql = """
        SELECT IdRetencionSQL AS idRetencion, [Numero Certificado] AS numeroCertificado, Importe AS importe
        FROM dbo.Retenciones
        WHERE IdRetencionSQL = ?
    """
    return fetch_one(sql, (id_retencion,))


# --- 033-alta-impuestos -----------------------------------------------------

# FR-001: organismos de `docs/referencia-impuestos.md`. `codigo` es
# `[Tipo Impuesto].IdOrganismo` (numeración heredada de Access, NO es el
# IdContacto). UATRE no tiene código propio: su único tipo es el 15.
ORGANISMOS = [
    {"idContacto": 119, "nombre": "AFIP / ARCA", "codigo": 1},
    {"idContacto": 12, "nombre": "ARBA", "codigo": 2},
    {"idContacto": 72, "nombre": "Municipalidad de Bolívar", "codigo": 3},
    {"idContacto": 422, "nombre": "Municipalidad de Tapalqué", "codigo": 4},
    {"idContacto": 315, "nombre": "UATRE", "codigo": None},
]
TIPO_APORTE_SINDICAL = 15
# FR-002: Retenciones Ganancias (20) no es un impuesto propio; 24 es la marca
# del backfill 029 para boletas de tipo desconocido.
TIPOS_EXCLUIDOS = {20, 24}


def get_catalogo() -> dict:
    tipos = fetch_all(
        "SELECT IdTipoImpuesto AS idTipoImpuesto, IdOrganismo AS codigo, [Nombre Impuesto] AS nombre "
        "FROM dbo.[Tipo Impuesto] ORDER BY [Nombre Impuesto]"
    )
    organismos = []
    for o in ORGANISMOS:
        if o["codigo"] is None:
            propios = [t for t in tipos if t["idTipoImpuesto"] == TIPO_APORTE_SINDICAL]
        else:
            propios = [t for t in tipos if t["codigo"] == o["codigo"] and t["idTipoImpuesto"] != TIPO_APORTE_SINDICAL]
        organismos.append({
            "idContacto": o["idContacto"],
            "nombre": o["nombre"],
            "tipos": [{"idTipoImpuesto": t["idTipoImpuesto"], "nombre": t["nombre"]}
                      for t in propios if t["idTipoImpuesto"] not in TIPOS_EXCLUIDOS],
        })
    return {"organismos": organismos}


def get_impuesto(id_impuesto: int) -> dict | None:
    return fetch_one(
        """
        SELECT i.IdImpuesto AS idImpuesto, i.Fecha AS fecha, i.IdOrganismo AS idOrganismo,
               c.[Razon Social] AS organismo, i.IdTipoImpuesto AS idTipoImpuesto,
               ti.[Nombre Impuesto] AS tipoImpuesto, i.[Periodo liquidado] AS periodoLiquidado,
               i.[Numero de documento] AS numeroDocumento, i.Importe AS importe,
               i.[Documento Original] AS documentoOriginal
        FROM dbo.Impuestos i
        LEFT JOIN dbo.Contactos c ON c.IdContacto = i.IdOrganismo
        LEFT JOIN dbo.[Tipo Impuesto] ti ON ti.IdTipoImpuesto = i.IdTipoImpuesto
        WHERE i.IdImpuesto = ?
        """,
        (id_impuesto,),
    )


def validar(datos: dict) -> list[str]:
    """FR-002/FR-003. `datos`: idOrganismo, idTipoImpuesto, fecha, importe, ..."""
    errores = []
    organismo = next((o for o in get_catalogo()["organismos"] if o["idContacto"] == datos.get("idOrganismo")), None)
    if organismo is None:
        errores.append("Elegí un organismo válido.")
    elif datos.get("idTipoImpuesto") not in {t["idTipoImpuesto"] for t in organismo["tipos"]}:
        errores.append(f"El tipo de impuesto no corresponde a {organismo['nombre']}.")
    if not datos.get("fecha"):
        errores.append("La fecha es obligatoria.")
    if not datos.get("importe"):
        errores.append("El importe no puede ser 0.")
    return errores


def buscar_duplicado(id_organismo: int, numero: str | None, excluir_id: int | None = None) -> dict | None:
    """FR-004: mismo organismo y mismo número, solo si el número tiene algún
    dígito ("SIN COPIA", "S/D" se repiten a propósito; igual que Compras)."""
    numero = (numero or "").strip()
    if not re.search(r"\d", numero):
        return None
    sql = ("SELECT IdImpuesto AS idImpuesto FROM dbo.Impuestos "
           "WHERE IdOrganismo = ? AND LTRIM(RTRIM([Numero de documento])) = ?")
    params: list = [id_organismo, numero]
    if excluir_id is not None:
        sql += " AND IdImpuesto <> ?"
        params.append(excluir_id)
    return fetch_one(sql, tuple(params))


def _valores(datos: dict) -> tuple:
    def limpio(v):
        v = (v or "").strip() if isinstance(v, str) or v is None else v
        return v or None
    return (as_sql_datetime(datos["fecha"]), datos["idOrganismo"], datos["idTipoImpuesto"],
            limpio(datos.get("periodoLiquidado")), limpio(datos.get("numeroDocumento")),
            round(float(datos["importe"]), 2), limpio(datos.get("documentoOriginal")))


def crear(datos: dict) -> int:
    return execute_insert_returning_id(
        "INSERT INTO dbo.Impuestos (Fecha, IdOrganismo, IdTipoImpuesto, [Periodo liquidado], "
        "[Numero de documento], Importe, [Documento Original]) OUTPUT INSERTED.IdImpuesto "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        _valores(datos),
    )


def actualizar(id_impuesto: int, datos: dict) -> None:
    execute_write_transaction([(
        "UPDATE dbo.Impuestos SET Fecha = ?, IdOrganismo = ?, IdTipoImpuesto = ?, [Periodo liquidado] = ?, "
        "[Numero de documento] = ?, Importe = ?, [Documento Original] = ? WHERE IdImpuesto = ?",
        _valores(datos) + (id_impuesto,),
    )])


def vinculos(id_impuesto: int) -> list[str]:
    """FR-005: dónde está usada la boleta (consumos de tarjeta, conciliación
    de tesorería, backfill 029)."""
    usos = []
    n = fetch_one("SELECT COUNT(*) AS n FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdImpuesto = ?", (id_impuesto,))
    if n and n["n"]:
        usos.append(f"{n['n']} consumo(s) de tarjeta")
    n = fetch_one("SELECT COUNT(*) AS n FROM dbo.ConciliacionesTesoreria "
                  "WHERE TipoOrigenDocumento = 'Impuestos' AND IdOrigenDocumento = ?", (id_impuesto,))
    if n and n["n"]:
        usos.append(f"{n['n']} conciliación(es) de tesorería")
    n = fetch_one("SELECT COUNT(*) AS n FROM dbo.BackfillImpuestosVinculos WHERE IdImpuesto = ?", (id_impuesto,))
    if n and n["n"]:
        usos.append(f"{n['n']} vínculo(s) de pago del backfill")
    return usos


def eliminar(id_impuesto: int) -> None:
    execute_write_transaction([("DELETE FROM dbo.Impuestos WHERE IdImpuesto = ?", (id_impuesto,))])
