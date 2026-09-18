"""Parameterized SQL queries for the Ventas de Granos module.

Dominio 100% nuevo (007-ventas-hacienda-granos) — cabecera única
`dbo.[Venta Granos]`, sin tabla de líneas de producto separada, con
subformularios de ajustes/deducciones (`Venta Granos_Ajustes`,
`Venta Granos_Deducciones`). Escribe exclusivamente contra `WC` vía
`execute_write_transaction` (ver src/db/connection.py).
"""

from __future__ import annotations

from datetime import date

from src.db.connection import execute_write, execute_write_transaction, fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime

# Whitelist estricta para ORDER BY dinámico — nunca interpolar sort_by directo.
_COLUMNAS_ORDEN = {
    "fecha": "v.Fecha",
    "consignatario": "c.[Razon Social]",
    "numeroDocumento": "v.[Nro Documento]",
}


def search_ventas(
    consignatario: str | None,
    numero_documento: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    campania: str | None,
    page: int,
    page_size: int,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[list[dict], int]:
    """FR-010: sin ningún filtro, no ejecuta la query principal (devuelve vacío)."""
    if not (consignatario or numero_documento or fecha_desde or fecha_hasta or campania):
        return [], 0

    where_clauses: list[str] = []
    params: list = []

    if consignatario:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{consignatario}%")
    if numero_documento:
        where_clauses.append("v.[Nro Documento] LIKE ?")
        params.append(f"%{numero_documento}%")
    if fecha_desde:
        where_clauses.append("v.Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("v.Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))
    if campania:
        where_clauses.append("v.Campaña = ?")
        params.append(campania)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.[Venta Granos] v
        LEFT JOIN dbo.Contactos c ON c.IdContacto = v.IdConsignatario
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    direccion = "DESC" if sort_dir == "desc" else "ASC"
    columna_orden = _COLUMNAS_ORDEN.get(sort_by or "", "v.Fecha")
    order_by_sql = f"{columna_orden} {direccion}, v.IdVenta {direccion}" if sort_by else "v.Fecha DESC, v.IdVenta DESC"

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            v.IdVenta AS idVenta,
            v.Fecha AS fecha,
            c.IdContacto AS idContacto,
            c.[Razon Social] AS razonSocial,
            td.[Tipo Documento] AS tipoDocumento,
            v.[Nro Documento] AS numeroDocumento,
            g.Grano AS grano,
            v.Campaña AS campania
        FROM dbo.[Venta Granos] v
        LEFT JOIN dbo.Contactos c ON c.IdContacto = v.IdConsignatario
        LEFT JOIN dbo.[Tipo Documento] td ON td.IdTipoDocumento = v.IdTipoDocumento
        LEFT JOIN dbo.Granos g ON g.IdGrano = v.IdProducto
        {where_sql}
        ORDER BY {order_by_sql}
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    items = []
    for row in rows:
        items.append(
            {
                "idVenta": row["idVenta"],
                "fecha": row["fecha"],
                "consignatario": {"idContacto": row["idContacto"], "razonSocial": row["razonSocial"]}
                if row.get("idContacto") is not None
                else None,
                "tipoDocumento": row["tipoDocumento"],
                "numeroDocumento": row["numeroDocumento"],
                "grano": row["grano"],
                "campania": row["campania"],
            }
        )
    return items, total


def get_venta_cabecera(id_venta: int) -> dict | None:
    sql = """
        SELECT
            v.IdVenta AS idVenta,
            v.IdConsignatario AS idConsignatario,
            v.IdTipoDocumento AS idTipoDocumento,
            v.[Nro Documento] AS numeroDocumento,
            v.Fecha AS fecha,
            v.[Precio unitario] AS precioUnitario,
            v.[Tipo Cambio] AS tipoCambio,
            v.[Grado Operacion] AS gradoOperacion,
            v.IdProducto AS idProducto,
            v.[Tipo de Grano] AS tipoDeGrano,
            v.Campaña AS campania,
            COALESCE(v.Flete, 0) AS flete,
            v.[Nro Deposito] AS nroDeposito,
            v.[Grado Mercaderia] AS gradoMercaderia,
            COALESCE(v.Factor, 100) AS factor,
            v.[Cont Proteico] AS contProteico,
            COALESCE(v.[Cantidad entregada], 0) AS cantidadEntregada,
            COALESCE(v.[Cantidad vendida], 0) AS cantidadVendida,
            COALESCE(v.AlicuotaIVA, 0) AS alicuotaIVA,
            COALESCE(v.[Retencion IVA], 0) AS retencionIVA,
            COALESCE(v.[Ret IG], 0) AS retIG,
            COALESCE(v.Percepciones, 0) AS percepciones,
            COALESCE(v.[Otra Retenciones], 0) AS otraRetenciones,
            COALESCE(v.[Sellado (0,375%)], 0) AS sellado,
            COALESCE(v.[Derecho de Registro (0,125%)], 0) AS derechoRegistro,
            COALESCE(v.[Honorarios Camara], 0) AS honorariosCamara,
            COALESCE(v.[A cuenta de Calidad], 0) AS aCuentaCalidad,
            COALESCE(v.[IIBB (1%)], 0) AS iibb,
            v.[Documento Original] AS documentoOriginal
        FROM dbo.[Venta Granos] v
        WHERE v.IdVenta = ?
    """
    return fetch_one(sql, (id_venta,))


def get_ajustes(id_venta: int) -> list[dict]:
    return fetch_all(
        "SELECT IdAjuste AS idAjuste, Concepto AS concepto, Importe AS importe, AlicuotaIVA AS alicuotaIVA "
        "FROM dbo.[Venta Granos_Ajustes] WHERE IdVenta = ? ORDER BY IdAjuste ASC",
        (id_venta,),
    )


def get_deducciones(id_venta: int) -> list[dict]:
    sql = """
        SELECT
            d.IdDeduccion AS idDeduccion,
            d.IdConcepto AS idConcepto,
            cd.Concepto AS concepto,
            d.Detalle AS detalle,
            d.Porc AS porc,
            d.[Base Calculo] AS baseCalculo,
            d.Alicuota AS alicuota
        FROM dbo.[Venta Granos_Deducciones] d
        LEFT JOIN dbo.[Venta Granos_ConceptosDeducciones] cd ON cd.IdConcepto = d.IdConcepto
        WHERE d.IdVenta = ?
        ORDER BY d.IdDeduccion ASC
    """
    return fetch_all(sql, (id_venta,))


def calcular_totales(cabecera: dict, ajustes: list[dict], deducciones: list[dict]) -> dict:
    """Fórmulas confirmadas contra el formulario Access real (`Frm Venta
    Granos`, ver data-model.md). Función pura, sin acceso a base."""
    # pyodbc devuelve `decimal.Decimal` para columnas money/decimal de SQL
    # Server — sin este cast, mezclar Decimal con los float literales de
    # esta fórmula (ej. /100, /1000) rompe con TypeError en tiempo de
    # ejecución (no lo cubren los tests porque ahí los mocks ya usan floats).
    def _f(value) -> float:
        return float(value) if value is not None else 0.0

    precio_unitario = _f(cabecera.get("precioUnitario"))
    factor = _f(cabecera.get("factor")) if cabecera.get("factor") is not None else 100.0
    flete = _f(cabecera.get("flete"))
    cantidad_vendida = _f(cabecera.get("cantidadVendida"))

    precio_kg = (precio_unitario * factor / 100 - flete) / 1000
    suma_ajustes = sum(_f(a.get("importe")) for a in ajustes)
    sub_total = (cantidad_vendida * precio_kg) + suma_ajustes

    alicuota_iva = _f(cabecera.get("alicuotaIVA"))
    iva = sub_total * alicuota_iva / 100
    importe_con_iva = sub_total + iva
    total_operacion = importe_con_iva

    total_retenciones = _f(cabecera.get("retIG")) + _f(cabecera.get("retencionIVA"))

    total_deducciones = 0.0
    for d in deducciones:
        base = _f(d.get("baseCalculo"))
        porc = _f(d.get("porc"))
        alicuota = _f(d.get("alicuota"))
        monto_base = base * porc / 100
        iva_deduccion = monto_base * alicuota / 100
        total_deducciones += monto_base + iva_deduccion

    importe_neto_a_percibir = total_operacion - (
        total_retenciones
        + _f(cabecera.get("percepciones"))
        + _f(cabecera.get("otraRetenciones"))
        + total_deducciones
    )

    return {
        "precioKg": precio_kg,
        "subTotal": sub_total,
        "iva": iva,
        "importeConIVA": importe_con_iva,
        "totalOperacion": total_operacion,
        "totalRetenciones": total_retenciones,
        "totalDeducciones": total_deducciones,
        "importeNetoAPercibir": importe_neto_a_percibir,
    }


def existe_contacto_consignatario(id_contacto: int) -> bool:
    """research.md §3: histórico real 100% tipo Multiple; se admite también Comprador/Consignatario."""
    row = fetch_one(
        "SELECT 1 FROM dbo.Contactos WHERE IdContacto = ? AND [Tipo Contacto] IN "
        "('Multiple', 'Comprador', 'Consignatario')",
        (id_contacto,),
    )
    return row is not None


def existe_grano(id_producto: int) -> bool:
    return fetch_one("SELECT 1 FROM dbo.Granos WHERE IdGrano = ?", (id_producto,)) is not None


def existe_tipo_documento(id_tipo_documento: int) -> bool:
    return (
        fetch_one("SELECT 1 FROM dbo.[Tipo Documento] WHERE IdTipoDocumento = ?", (id_tipo_documento,))
        is not None
    )


def existe_concepto_deduccion(id_concepto: int) -> bool:
    return (
        fetch_one(
            "SELECT 1 FROM dbo.[Venta Granos_ConceptosDeducciones] WHERE IdConcepto = ?", (id_concepto,)
        )
        is not None
    )


def validar_venta(id_consignatario: int, id_producto: int, id_tipo_documento: int, deducciones: list[dict]) -> list[str]:
    errores: list[str] = []
    if not existe_contacto_consignatario(id_consignatario):
        errores.append("El consignatario seleccionado no existe o no es de un tipo válido.")
    if not existe_grano(id_producto):
        errores.append(f"El grano {id_producto} no existe.")
    if not existe_tipo_documento(id_tipo_documento):
        errores.append(f"El tipo de documento {id_tipo_documento} no existe.")
    for d in deducciones:
        id_concepto = d.get("idConcepto")
        if id_concepto is not None and not existe_concepto_deduccion(id_concepto):
            errores.append(f"El concepto de deducción {id_concepto} no existe.")
    return errores


def hay_documento_duplicado(id_consignatario: int, numero_documento: str, excluir_id_venta: int | None = None) -> bool:
    """FR-012a: advertencia no bloqueante (decisión Q3) — nunca bloquea el guardado."""
    sql = "SELECT 1 FROM dbo.[Venta Granos] WHERE IdConsignatario = ? AND [Nro Documento] = ?"
    params: list = [id_consignatario, numero_documento]
    if excluir_id_venta is not None:
        sql += " AND IdVenta <> ?"
        params.append(excluir_id_venta)
    return fetch_one(sql, tuple(params)) is not None


# Lista explícita (no un string a partir por coma) porque varios nombres
# de columna reales tienen una coma DENTRO de los corchetes (ej.
# "[Sellado (0,375%)]") — partir por "," rompería esos nombres.
_CABECERA_COLUMNAS = [
    "IdConsignatario", "IdTipoDocumento", "[Nro Documento]", "Fecha", "[Precio unitario]",
    "[Tipo Cambio]", "[Grado Operacion]", "IdProducto", "[Tipo de Grano]", "Campaña", "Flete",
    "[Nro Deposito]", "[Grado Mercaderia]", "Factor", "[Cont Proteico]", "[Cantidad entregada]",
    "[Cantidad vendida]", "AlicuotaIVA", "[Retencion IVA]", "[Ret IG]", "Percepciones",
    "[Otra Retenciones]", "[Sellado (0,375%)]", "[Derecho de Registro (0,125%)]",
    "[Honorarios Camara]", "[A cuenta de Calidad]", "[IIBB (1%)]", "[Documento Original]",
]


def _cabecera_params(cabecera: dict) -> tuple:
    return (
        cabecera["idConsignatario"],
        cabecera["idTipoDocumento"],
        cabecera["numeroDocumento"],
        cabecera["fecha"],
        cabecera["precioUnitario"],
        cabecera.get("tipoCambio"),
        cabecera.get("gradoOperacion"),
        cabecera["idProducto"],
        cabecera.get("tipoDeGrano"),
        cabecera.get("campania"),
        cabecera.get("flete") or 0,
        cabecera.get("nroDeposito"),
        cabecera.get("gradoMercaderia"),
        cabecera.get("factor") if cabecera.get("factor") is not None else 100,
        cabecera.get("contProteico"),
        cabecera["cantidadEntregada"],
        cabecera["cantidadVendida"],
        cabecera.get("alicuotaIVA") or 0,
        cabecera.get("retencionIVA") or 0,
        cabecera.get("retIG") or 0,
        cabecera.get("percepciones") or 0,
        cabecera.get("otraRetenciones") or 0,
        cabecera.get("sellado") or 0,
        cabecera.get("derechoRegistro") or 0,
        cabecera.get("honorariosCamara") or 0,
        cabecera.get("aCuentaCalidad") or 0,
        cabecera.get("iibb") or 0,
        cabecera.get("documentoOriginal"),
    )


def _cabecera_insert_statement(cabecera: dict):
    def build(_results: list) -> tuple[str, tuple]:
        columnas_sql = ", ".join(_CABECERA_COLUMNAS)
        placeholders = ", ".join("?" for _ in _CABECERA_COLUMNAS)
        sql = f"INSERT INTO dbo.[Venta Granos] ({columnas_sql}) OUTPUT INSERTED.IdVenta VALUES ({placeholders})"
        return sql, _cabecera_params(cabecera)

    return build


def _cabecera_update_statement(id_venta: int, cabecera: dict) -> tuple[str, tuple]:
    set_clause = ", ".join(f"{c} = ?" for c in _CABECERA_COLUMNAS)
    sql = f"UPDATE dbo.[Venta Granos] SET {set_clause} WHERE IdVenta = ?"
    return sql, _cabecera_params(cabecera) + (id_venta,)


def _ajuste_insert_statement(ajuste: dict):
    def build(results: list) -> tuple[str, tuple]:
        id_venta = results[0]
        sql = "INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta, Concepto, Importe, AlicuotaIVA) VALUES (?, ?, ?, ?)"
        return sql, (id_venta, ajuste["concepto"], ajuste["importe"], ajuste.get("alicuotaIVA") or 0)

    return build


def _deduccion_insert_statement(deduccion: dict):
    def build(results: list) -> tuple[str, tuple]:
        id_venta = results[0]
        sql = (
            "INSERT INTO dbo.[Venta Granos_Deducciones] "
            "(IdVenta, IdConcepto, Detalle, Porc, [Base Calculo], Alicuota) VALUES (?, ?, ?, ?, ?, ?)"
        )
        return sql, (
            id_venta,
            deduccion["idConcepto"],
            deduccion.get("detalle"),
            deduccion["porc"],
            deduccion["baseCalculo"],
            deduccion.get("alicuota") or 0,
        )

    return build


def create_venta(cabecera: dict, ajustes: list[dict], deducciones: list[dict]) -> int:
    errores = validar_venta(cabecera["idConsignatario"], cabecera["idProducto"], cabecera["idTipoDocumento"], deducciones)
    if errores:
        raise ValueError(errores)

    statements = [_cabecera_insert_statement(cabecera)]
    for ajuste in ajustes:
        statements.append(_ajuste_insert_statement(ajuste))
    for deduccion in deducciones:
        statements.append(_deduccion_insert_statement(deduccion))

    results = execute_write_transaction(statements)
    return results[0]


def update_venta(id_venta: int, cabecera: dict, ajustes: list[dict], deducciones: list[dict]) -> None:
    errores = validar_venta(cabecera["idConsignatario"], cabecera["idProducto"], cabecera["idTipoDocumento"], deducciones)
    if errores:
        raise ValueError(errores)

    statements: list = [
        ("DELETE FROM dbo.[Venta Granos_Ajustes] WHERE IdVenta = ?", (id_venta,)),
        ("DELETE FROM dbo.[Venta Granos_Deducciones] WHERE IdVenta = ?", (id_venta,)),
        _cabecera_update_statement(id_venta, cabecera),
    ]
    for ajuste in ajustes:
        statements.append(
            (
                "INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta, Concepto, Importe, AlicuotaIVA) VALUES (?, ?, ?, ?)",
                (id_venta, ajuste["concepto"], ajuste["importe"], ajuste.get("alicuotaIVA") or 0),
            )
        )
    for deduccion in deducciones:
        statements.append(
            (
                "INSERT INTO dbo.[Venta Granos_Deducciones] "
                "(IdVenta, IdConcepto, Detalle, Porc, [Base Calculo], Alicuota) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    id_venta,
                    deduccion["idConcepto"],
                    deduccion.get("detalle"),
                    deduccion["porc"],
                    deduccion["baseCalculo"],
                    deduccion.get("alicuota") or 0,
                ),
            )
        )

    execute_write_transaction(statements)


def delete_venta(id_venta: int) -> None:
    statements = [
        ("DELETE FROM dbo.[Venta Granos_Ajustes] WHERE IdVenta = ?", (id_venta,)),
        ("DELETE FROM dbo.[Venta Granos_Deducciones] WHERE IdVenta = ?", (id_venta,)),
        (
            "DELETE FROM dbo.VentaDocumentosRelacionados "
            "WHERE TipoVenta = 'Granos' AND (IdVenta = ? OR IdVentaRelacionada = ?)",
            (id_venta, id_venta),
        ),
        ("DELETE FROM dbo.VentaGranosEditLocks WHERE IdVenta = ?", (id_venta,)),
        ("DELETE FROM dbo.[Venta Granos] WHERE IdVenta = ?", (id_venta,)),
    ]
    execute_write_transaction(statements)


def get_filtros() -> dict:
    granos = fetch_all("SELECT IdGrano AS idGrano, Grano AS grano FROM dbo.Granos ORDER BY Grano")
    tipos_documento = fetch_all(
        "SELECT IdTipoDocumento AS idTipoDocumento, [Tipo Documento] AS tipoDocumento "
        "FROM dbo.[Tipo Documento] ORDER BY [Tipo Documento]"
    )
    conceptos_deducciones = fetch_all(
        "SELECT IdConcepto AS idConcepto, Concepto AS concepto "
        "FROM dbo.[Venta Granos_ConceptosDeducciones] ORDER BY Concepto"
    )
    return {
        "granos": granos,
        "tiposDocumento": tipos_documento,
        "conceptosDeducciones": conceptos_deducciones,
    }
