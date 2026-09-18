"""Parameterized SQL queries for the Ventas de Hacienda module.

`Retenciones Ventas Hacienda` has no reliable key back to a `Venta
Hacienda` (confirmed against real data — see research.md), so it is
queried independently, never joined to a venta.

Desde 007-ventas-hacienda-granos se agregan alta/edición/eliminación,
que escriben exclusivamente contra `WC` vía `execute_write_transaction`
(ver src/db/connection.py) — nunca contra `LaHerencia`.
"""

from __future__ import annotations

from datetime import date

from src.db.connection import execute_write, execute_write_transaction, fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime


def search_ventas_hacienda(
    consignatario: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    where_clauses: list[str] = []
    params: list = []

    if consignatario:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{consignatario}%")
    if fecha_desde:
        where_clauses.append("v.Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("v.Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.[Venta Hacienda] v
        LEFT JOIN dbo.Contactos c ON c.IdContacto = v.IdConsignatario
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            v.IdVenta AS idVenta,
            v.Fecha AS fecha,
            c.IdContacto AS idConsignatario,
            c.[Razon Social] AS consignatario,
            v.[Nro documento] AS numeroDocumento
        FROM dbo.[Venta Hacienda] v
        LEFT JOIN dbo.Contactos c ON c.IdContacto = v.IdConsignatario
        {where_sql}
        ORDER BY v.Fecha DESC, v.IdVenta DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    ventas = []
    for row in rows:
        venta = dict(row)
        venta["lineas"] = get_lineas_venta(row["idVenta"])
        ventas.append(venta)
    return ventas, total


def get_lineas_venta(id_venta: int) -> list[dict]:
    sql = """
        SELECT
            d.IdDetalleVenta AS idDetalleVenta,
            c.IdContacto AS idComprador,
            c.[Razon Social] AS comprador,
            d.IdTipoProducto AS idTipoProducto,
            th.[Tipo de Hacienda] AS tipoHacienda,
            d.Cantidad AS cantidad,
            d.[Unidad de medida] AS unidadMedida,
            d.[Peso Total] AS pesoTotal,
            d.[Precio unitario (A)] AS precioUnitarioA,
            COALESCE(d.[Precio unitario (B)], 0) AS precioUnitarioB,
            d.Cantidad * (ISNULL(d.[Precio unitario (A)], 0) + ISNULL(d.[Precio unitario (B)], 0)) AS importe
        FROM dbo.[Det_Ventas Hacienda] d
        LEFT JOIN dbo.Contactos c ON c.IdContacto = d.IdComprador
        LEFT JOIN dbo.[Tipo Hacienda] th ON th.IdTipoHacienda = d.IdTipoProducto
        WHERE d.IdVenta = ?
        ORDER BY d.IdDetalleVenta ASC
    """
    # Datos históricos reales incluyen filas de detalle completamente vacías
    # (todas las columnas NULL salvo el ID) — artefactos de carga en Access,
    # no líneas de producto reales. Se descartan al leer en vez de forzarlas
    # a encajar en el contrato (que exige comprador/categoría/cantidad).
    return [row for row in fetch_all(sql, (id_venta,)) if row.get("cantidad") is not None]


def get_venta_hacienda_referencia(id_venta: int) -> dict | None:
    sql = """
        SELECT
            v.IdVenta AS idVenta,
            c.[Razon Social] AS consignatario,
            v.[Nro documento] AS numeroDocumento
        FROM dbo.[Venta Hacienda] v
        LEFT JOIN dbo.Contactos c ON c.IdContacto = v.IdConsignatario
        WHERE v.IdVenta = ?
    """
    return fetch_one(sql, (id_venta,))


def search_retenciones_venta_hacienda(
    contacto: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """Listado independiente — MUST NOT join a `Venta Hacienda` (sin clave confiable)."""
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
        FROM dbo.[Retenciones Ventas Hacienda] r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            r.Id AS idRetencion,
            r.Fecha AS fecha,
            c.IdContacto AS idContacto,
            c.[Razon Social] AS contacto,
            r.Documento AS documento,
            r.[Nro Documento] AS numeroDocumento,
            r.Importe AS importe
        FROM dbo.[Retenciones Ventas Hacienda] r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
        {where_sql}
        ORDER BY r.Fecha DESC, r.Id DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return rows, total


def get_retencion_venta_hacienda_referencia(id_retencion: int) -> dict | None:
    sql = """
        SELECT Id AS idRetencion, Documento AS documento, [Nro Documento] AS numeroDocumento, Importe AS importe
        FROM dbo.[Retenciones Ventas Hacienda]
        WHERE Id = ?
    """
    return fetch_one(sql, (id_retencion,))


# --- Alta/edición/eliminación (007-ventas-hacienda-granos) ---


def get_venta_cabecera(id_venta: int) -> dict | None:
    sql = """
        SELECT
            v.IdVenta AS idVenta,
            v.IdConsignatario AS idConsignatario,
            v.IdEstableciemiento AS idEstablecimiento,
            v.IdTipoDocumento AS idTipoDocumento,
            v.[Nro documento] AS numeroDocumento,
            v.Fecha AS fecha,
            COALESCE(v.[Porc Comision], 0) AS porcComision,
            COALESCE(v.[Vis Municipal], 0) AS visMunicipal,
            COALESCE(v.Balanza, 0) AS balanza,
            COALESCE(v.[Gs Vs No Gravados], 0) AS gsVsNoGravados,
            COALESCE(v.AlicuotaIVA, 0) AS alicuotaIVA,
            COALESCE(v.[Retencion Ganancias], 0) AS retencionGanancias,
            COALESCE(v.[Retencion IVA], 0) AS retencionIVA,
            COALESCE(v.[Ingresos Brutos], 0) AS ingresosBrutos,
            COALESCE(v.[Ley de Sellos], 0) AS leyDeSellos,
            COALESCE(v.Flete, 0) AS flete,
            COALESCE(v.[Gastos Varios], 0) AS gastosVarios,
            COALESCE(v.Complemento, 0) AS complemento,
            v.[Documento Original] AS documentoOriginal,
            c.[Razon Social] AS consignatario
        FROM dbo.[Venta Hacienda] v
        LEFT JOIN dbo.Contactos c ON c.IdContacto = v.IdConsignatario
        WHERE v.IdVenta = ?
    """
    return fetch_one(sql, (id_venta,))


def existe_contacto_valido_consignatario(id_contacto: int) -> bool:
    """research.md §2: histórico real usa Comprador/Consignatario/Multiple."""
    row = fetch_one(
        "SELECT 1 FROM dbo.Contactos WHERE IdContacto = ? AND [Tipo Contacto] IN "
        "('Comprador', 'Consignatario', 'Multiple')",
        (id_contacto,),
    )
    return row is not None


def existe_contacto_valido_comprador(id_contacto: int) -> bool:
    """research.md §2: histórico real usa Comprador/Multiple."""
    row = fetch_one(
        "SELECT 1 FROM dbo.Contactos WHERE IdContacto = ? AND [Tipo Contacto] IN "
        "('Comprador', 'Multiple')",
        (id_contacto,),
    )
    return row is not None


def existe_establecimiento(id_establecimiento: int) -> bool:
    return fetch_one("SELECT 1 FROM dbo.Establecimientos WHERE Id = ?", (id_establecimiento,)) is not None


def existe_tipo_documento(id_tipo_documento: int) -> bool:
    return (
        fetch_one("SELECT 1 FROM dbo.[Tipo Documento] WHERE IdTipoDocumento = ?", (id_tipo_documento,))
        is not None
    )


def existe_tipo_hacienda(id_tipo_producto: int) -> bool:
    return (
        fetch_one("SELECT 1 FROM dbo.[Tipo Hacienda] WHERE IdTipoHacienda = ?", (id_tipo_producto,))
        is not None
    )


def validar_venta(id_consignatario: int, id_establecimiento: int, id_tipo_documento: int, lineas: list[dict]) -> list[str]:
    """FR-001/FR-002/FR-009: errores de validación de aplicación (sin FKs reales en el motor,
    salvo Det_Ventas Hacienda.IdVenta -> Venta Hacienda.IdVenta, research.md §1)."""
    errores: list[str] = []

    if not existe_contacto_valido_consignatario(id_consignatario):
        errores.append(
            "El consignatario seleccionado no existe o no es de un tipo válido "
            "(Comprador, Consignatario o Multiple)."
        )
    if not existe_establecimiento(id_establecimiento):
        errores.append(f"El establecimiento {id_establecimiento} no existe.")
    if not existe_tipo_documento(id_tipo_documento):
        errores.append(f"El tipo de documento {id_tipo_documento} no existe.")

    for linea in lineas:
        id_comprador = linea.get("idComprador")
        if id_comprador is not None and not existe_contacto_valido_comprador(id_comprador):
            errores.append(
                f"El comprador {id_comprador} no existe o no es de un tipo válido "
                "(Comprador o Multiple)."
            )
        id_tipo_producto = linea.get("idTipoProducto")
        if id_tipo_producto is not None and not existe_tipo_hacienda(id_tipo_producto):
            errores.append(f"La categoría de hacienda {id_tipo_producto} no existe.")

    return errores


def calcular_totales(lineas: list[dict], cabecera: dict) -> dict:
    """Fórmulas confirmadas contra el formulario Access real (`Frm Venta
    Hacienda`, ver data-model.md). Función pura, sin acceso a base."""
    # pyodbc devuelve `decimal.Decimal` para columnas money/decimal de SQL
    # Server pero `float` para columnas real/float (ej. `cantidad`) —
    # mezclar ambos tipos rompe con TypeError en tiempo de ejecución (no
    # lo cubren los tests porque ahí los mocks ya usan floats).
    def _f(value) -> float:
        return float(value) if value is not None else 0.0

    lineas_calculadas = []
    sub_total = 0.0
    subtotal_b = 0.0
    for linea in lineas:
        precio_a = _f(linea.get("precioUnitarioA"))
        precio_b = _f(linea.get("precioUnitarioB"))
        cantidad = _f(linea["cantidad"])
        importe_linea = cantidad * (precio_a + precio_b)
        sub_total += cantidad * precio_a
        subtotal_b += cantidad * precio_b
        lineas_calculadas.append({**linea, "importe": importe_linea})

    porc_comision = _f(cabecera.get("porcComision"))
    comision = (sub_total + subtotal_b) * porc_comision / 100

    vis_municipal = _f(cabecera.get("visMunicipal"))
    balanza = _f(cabecera.get("balanza"))
    gs_vs_no_gravados = _f(cabecera.get("gsVsNoGravados"))
    alicuota_iva = _f(cabecera.get("alicuotaIVA"))
    iva = (sub_total - vis_municipal - balanza - comision - gs_vs_no_gravados) * alicuota_iva / 100

    importe = (
        sub_total
        - vis_municipal
        - balanza
        - comision
        - gs_vs_no_gravados
        + iva
        - _f(cabecera.get("leyDeSellos"))
        - _f(cabecera.get("retencionGanancias"))
        - _f(cabecera.get("ingresosBrutos"))
        - _f(cabecera.get("gastosVarios"))
    )
    importe_total = importe + subtotal_b

    return {
        "lineas": lineas_calculadas,
        "subTotal": sub_total,
        "subtotalB": subtotal_b,
        "comision": comision,
        "iva": iva,
        "importe": importe,
        "importeTotal": importe_total,
    }


def hay_documento_duplicado(id_consignatario: int, numero_documento: str, excluir_id_venta: int | None = None) -> bool:
    """FR-009a: advertencia no bloqueante (decisión Q3) — nunca bloquea el guardado."""
    sql = "SELECT 1 FROM dbo.[Venta Hacienda] WHERE IdConsignatario = ? AND [Nro documento] = ?"
    params: list = [id_consignatario, numero_documento]
    if excluir_id_venta is not None:
        sql += " AND IdVenta <> ?"
        params.append(excluir_id_venta)
    return fetch_one(sql, tuple(params)) is not None


def _cabecera_insert_statement(cabecera: dict):
    def build(_results: list) -> tuple[str, tuple]:
        sql = """
            INSERT INTO dbo.[Venta Hacienda] (
                IdConsignatario, IdEstableciemiento, IdTipoDocumento, [Nro documento], Fecha,
                [Porc Comision], [Vis Municipal], Balanza, [Gs Vs No Gravados], AlicuotaIVA,
                [Retencion Ganancias], [Retencion IVA], [Ingresos Brutos], [Ley de Sellos],
                Flete, [Gastos Varios], Complemento, [Documento Original]
            )
            OUTPUT INSERTED.IdVenta
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            cabecera["idConsignatario"],
            cabecera["idEstablecimiento"],
            cabecera["idTipoDocumento"],
            cabecera["numeroDocumento"],
            cabecera["fecha"],
            cabecera.get("porcComision") or 0,
            cabecera.get("visMunicipal") or 0,
            cabecera.get("balanza") or 0,
            cabecera.get("gsVsNoGravados") or 0,
            cabecera.get("alicuotaIVA") or 0,
            cabecera.get("retencionGanancias") or 0,
            cabecera.get("retencionIVA") or 0,
            cabecera.get("ingresosBrutos") or 0,
            cabecera.get("leyDeSellos") or 0,
            cabecera.get("flete") or 0,
            cabecera.get("gastosVarios") or 0,
            cabecera.get("complemento") or 0,
            cabecera.get("documentoOriginal"),
        )
        return sql, params

    return build


def _cabecera_update_statement(id_venta: int, cabecera: dict) -> tuple[str, tuple]:
    sql = """
        UPDATE dbo.[Venta Hacienda] SET
            IdConsignatario = ?, IdEstableciemiento = ?, IdTipoDocumento = ?, [Nro documento] = ?,
            Fecha = ?, [Porc Comision] = ?, [Vis Municipal] = ?, Balanza = ?, [Gs Vs No Gravados] = ?,
            AlicuotaIVA = ?, [Retencion Ganancias] = ?, [Retencion IVA] = ?, [Ingresos Brutos] = ?,
            [Ley de Sellos] = ?, Flete = ?, [Gastos Varios] = ?, Complemento = ?, [Documento Original] = ?
        WHERE IdVenta = ?
    """
    params = (
        cabecera["idConsignatario"],
        cabecera["idEstablecimiento"],
        cabecera["idTipoDocumento"],
        cabecera["numeroDocumento"],
        cabecera["fecha"],
        cabecera.get("porcComision") or 0,
        cabecera.get("visMunicipal") or 0,
        cabecera.get("balanza") or 0,
        cabecera.get("gsVsNoGravados") or 0,
        cabecera.get("alicuotaIVA") or 0,
        cabecera.get("retencionGanancias") or 0,
        cabecera.get("retencionIVA") or 0,
        cabecera.get("ingresosBrutos") or 0,
        cabecera.get("leyDeSellos") or 0,
        cabecera.get("flete") or 0,
        cabecera.get("gastosVarios") or 0,
        cabecera.get("complemento") or 0,
        cabecera.get("documentoOriginal"),
        id_venta,
    )
    return sql, params


def _linea_insert_statement(linea: dict):
    def build(results: list) -> tuple[str, tuple]:
        id_venta = results[0]
        sql = """
            INSERT INTO dbo.[Det_Ventas Hacienda] (
                IdVenta, IdComprador, IdTipoProducto, Cantidad, [Unidad de medida], [Peso Total],
                [Precio unitario (A)], [Precio unitario (B)]
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            id_venta,
            linea["idComprador"],
            linea["idTipoProducto"],
            linea["cantidad"],
            linea.get("unidadMedida"),
            linea.get("pesoTotal"),
            linea["precioUnitarioA"],
            linea.get("precioUnitarioB") or 0,
        )
        return sql, params

    return build


def _vencimiento_insert_statement(vencimiento: dict):
    def build(results: list) -> tuple[str, tuple]:
        id_venta = results[0]
        sql = "INSERT INTO dbo.[Vencimientos Ventas] (IdVenta, Fecha, Importe) VALUES (?, ?, ?)"
        return sql, (id_venta, vencimiento["fecha"], vencimiento["importe"])

    return build


def create_venta(cabecera: dict, lineas: list[dict], vencimientos: list[dict]) -> int:
    """Alta transaccional (cabecera+líneas+vencimientos), todo o nada, contra `WC` (FR-001)."""
    errores = validar_venta(cabecera["idConsignatario"], cabecera["idEstablecimiento"], cabecera["idTipoDocumento"], lineas)
    if errores:
        raise ValueError(errores)

    statements = [_cabecera_insert_statement(cabecera)]
    for linea in lineas:
        statements.append(_linea_insert_statement(linea))
    for vencimiento in vencimientos:
        statements.append(_vencimiento_insert_statement(vencimiento))

    results = execute_write_transaction(statements)
    return results[0]


def update_venta(id_venta: int, cabecera: dict, lineas: list[dict], vencimientos: list[dict]) -> None:
    """Edición transaccional: reemplazo total de líneas/vencimientos + UPDATE de cabecera (FR-005)."""
    errores = validar_venta(cabecera["idConsignatario"], cabecera["idEstablecimiento"], cabecera["idTipoDocumento"], lineas)
    if errores:
        raise ValueError(errores)

    statements: list = [
        ("DELETE FROM dbo.[Det_Ventas Hacienda] WHERE IdVenta = ?", (id_venta,)),
        ("DELETE FROM dbo.[Vencimientos Ventas] WHERE IdVenta = ?", (id_venta,)),
        _cabecera_update_statement(id_venta, cabecera),
    ]
    for linea in lineas:
        statements.append(
            (
                """
                INSERT INTO dbo.[Det_Ventas Hacienda] (
                    IdVenta, IdComprador, IdTipoProducto, Cantidad, [Unidad de medida], [Peso Total],
                    [Precio unitario (A)], [Precio unitario (B)]
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_venta,
                    linea["idComprador"],
                    linea["idTipoProducto"],
                    linea["cantidad"],
                    linea.get("unidadMedida"),
                    linea.get("pesoTotal"),
                    linea["precioUnitarioA"],
                    linea.get("precioUnitarioB") or 0,
                ),
            )
        )
    for vencimiento in vencimientos:
        statements.append(
            (
                "INSERT INTO dbo.[Vencimientos Ventas] (IdVenta, Fecha, Importe) VALUES (?, ?, ?)",
                (id_venta, vencimiento["fecha"], vencimiento["importe"]),
            )
        )

    execute_write_transaction(statements)


def delete_venta(id_venta: int) -> None:
    """Elimina una venta de hacienda cargada por error: cabecera + todo lo
    que depende de ella, todo o nada en una sola transacción contra `WC` (FR-006a)."""
    statements = [
        ("DELETE FROM dbo.[Det_Ventas Hacienda] WHERE IdVenta = ?", (id_venta,)),
        ("DELETE FROM dbo.[Vencimientos Ventas] WHERE IdVenta = ?", (id_venta,)),
        (
            "DELETE FROM dbo.VentaDocumentosRelacionados "
            "WHERE TipoVenta = 'Hacienda' AND (IdVenta = ? OR IdVentaRelacionada = ?)",
            (id_venta, id_venta),
        ),
        ("DELETE FROM dbo.VentaHaciendaEditLocks WHERE IdVenta = ?", (id_venta,)),
        ("DELETE FROM dbo.[Venta Hacienda] WHERE IdVenta = ?", (id_venta,)),
    ]
    execute_write_transaction(statements)


def get_vencimientos_venta(id_venta: int) -> list[dict]:
    return fetch_all(
        "SELECT IdVencimientoVenta AS idVencimientoVenta, Fecha AS fecha, COALESCE(Importe, 0) AS importe "
        "FROM dbo.[Vencimientos Ventas] WHERE IdVenta = ? ORDER BY Fecha ASC",
        (id_venta,),
    )


def get_filtros() -> dict:
    establecimientos = fetch_all("SELECT Id AS idEstablecimiento, Establecimiento AS establecimiento FROM dbo.Establecimientos ORDER BY Establecimiento")
    tipos_documento = fetch_all("SELECT IdTipoDocumento AS idTipoDocumento, [Tipo Documento] AS tipoDocumento FROM dbo.[Tipo Documento] ORDER BY [Tipo Documento]")
    tipos_hacienda = fetch_all("SELECT IdTipoHacienda AS idTipoHacienda, [Tipo de Hacienda] AS tipoHacienda FROM dbo.[Tipo Hacienda] ORDER BY [Tipo de Hacienda]")
    return {
        "establecimientos": establecimientos,
        "tiposDocumento": tipos_documento,
        "tiposHacienda": tipos_hacienda,
    }


# --- Documentos relacionados (FR-007) ---


def get_documentos_relacionados(id_venta: int) -> list[dict]:
    sql = """
        SELECT
            v.IdVenta AS idVenta,
            v.Fecha AS fecha,
            td.[Tipo Documento] AS tipoDocumento,
            v.[Nro documento] AS numeroDocumento
        FROM dbo.VentaDocumentosRelacionados rel
        JOIN dbo.[Venta Hacienda] v
            ON v.IdVenta = CASE WHEN rel.IdVenta = ? THEN rel.IdVentaRelacionada ELSE rel.IdVenta END
        LEFT JOIN dbo.[Tipo Documento] td ON td.IdTipoDocumento = v.IdTipoDocumento
        WHERE rel.TipoVenta = 'Hacienda' AND (rel.IdVenta = ? OR rel.IdVentaRelacionada = ?)
        ORDER BY v.Fecha DESC
    """
    return fetch_all(sql, (id_venta, id_venta, id_venta))


def agregar_documento_relacionado(id_venta: int, id_venta_relacionada: int) -> None:
    if id_venta == id_venta_relacionada:
        raise ValueError("Una venta no puede relacionarse consigo misma.")
    if fetch_one("SELECT 1 FROM dbo.[Venta Hacienda] WHERE IdVenta = ?", (id_venta_relacionada,)) is None:
        raise ValueError(f"La venta {id_venta_relacionada} no existe.")
    ya_existe = fetch_one(
        "SELECT 1 FROM dbo.VentaDocumentosRelacionados WHERE TipoVenta = 'Hacienda' AND "
        "((IdVenta = ? AND IdVentaRelacionada = ?) OR (IdVenta = ? AND IdVentaRelacionada = ?))",
        (id_venta, id_venta_relacionada, id_venta_relacionada, id_venta),
    )
    if ya_existe:
        return
    execute_write(
        "INSERT INTO dbo.VentaDocumentosRelacionados (IdVenta, IdVentaRelacionada, TipoVenta, CreatedAt) "
        "VALUES (?, ?, 'Hacienda', GETDATE())",
        (id_venta, id_venta_relacionada),
    )


def quitar_documento_relacionado(id_venta: int, id_venta_relacionada: int) -> None:
    execute_write(
        "DELETE FROM dbo.VentaDocumentosRelacionados WHERE TipoVenta = 'Hacienda' AND "
        "((IdVenta = ? AND IdVentaRelacionada = ?) OR (IdVenta = ? AND IdVentaRelacionada = ?))",
        (id_venta, id_venta_relacionada, id_venta_relacionada, id_venta),
    )
