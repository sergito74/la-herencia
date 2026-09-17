"""Parameterized, read-only SQL queries for the Compras module.

Column/table names come from data-model.md, confirmed against the real
schema (INFORMATION_SCHEMA) on 2026-09-16. No writes are issued here
(constitution principle II, FR-010).
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


def _row_to_compra(row: dict) -> dict:
    return {
        "idCompra": row["idCompra"],
        "fecha": row["fecha"],
        "proveedor": {
            "idContacto": row["idContacto"],
            "razonSocial": row["razonSocial"],
        }
        if row.get("idContacto") is not None
        else None,
        "tipoDocumento": row["tipoDocumento"],
        "numeroDocumento": row["numeroDocumento"],
    }


def search_compras(
    proveedor: str | None,
    numero_documento: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    id_centro_costo: int | None,
    id_rubro: int | None,
    page: int,
    page_size: int,
    id_contacto: int | None = None,
) -> tuple[list[dict], int]:
    """Search/list compras with optional filters, ordered by fecha desc.

    `id_centro_costo`/`id_rubro` replican los filtros del formulario
    Access real (`Frm Listado Compras`): una compra matchea si ALGUNA de
    sus líneas en `Det_Compras` tiene ese centro de costo/rubro — se usa
    `EXISTS` (no `JOIN`) para no duplicar filas de `Compras`.
    """
    where_clauses: list[str] = []
    params: list = []

    if id_contacto:
        where_clauses.append("cmp.IdContacto = ?")
        params.append(id_contacto)
    if proveedor:
        where_clauses.append("c.[Razon Social] LIKE ?")
        params.append(f"%{proveedor}%")
    if numero_documento:
        where_clauses.append("cmp.[Nro Documento] LIKE ?")
        params.append(f"%{numero_documento}%")
    if fecha_desde:
        where_clauses.append("cmp.Fecha >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append("cmp.Fecha <= ?")
        params.append(as_sql_datetime(fecha_hasta))
    if id_centro_costo:
        where_clauses.append(
            "EXISTS (SELECT 1 FROM dbo.Det_Compras dc "
            "WHERE dc.IdCompra = cmp.IdDeuda AND dc.IdCentroCostos = ?)"
        )
        params.append(id_centro_costo)
    if id_rubro:
        where_clauses.append(
            "EXISTS (SELECT 1 FROM dbo.Det_Compras dc "
            "WHERE dc.IdCompra = cmp.IdDeuda AND dc.IdRubro = ?)"
        )
        params.append(id_rubro)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM dbo.Compras cmp
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        {where_sql}
    """
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            cmp.IdDeuda AS idCompra,
            cmp.Fecha AS fecha,
            c.IdContacto AS idContacto,
            c.[Razon Social] AS razonSocial,
            cmp.[Tipo documento] AS tipoDocumento,
            cmp.[Nro Documento] AS numeroDocumento
        FROM dbo.Compras cmp
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        {where_sql}
        ORDER BY cmp.Fecha DESC, cmp.IdDeuda DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return [_row_to_compra(row) for row in rows], total


def get_compra_cabecera(id_compra: int) -> dict | None:
    sql = """
        SELECT
            cmp.IdDeuda AS idCompra,
            cmp.Fecha AS fecha,
            c.IdContacto AS idContacto,
            c.[Razon Social] AS razonSocial,
            cmp.Tipo AS tipo,
            cmp.[Tipo documento] AS tipoDocumento,
            cmp.[Nro Documento] AS numeroDocumento,
            cmp.Moneda AS moneda,
            cmp.[Tipo de Cambio] AS tipoDeCambio,
            cmp.[Conceptos no gravados] AS conceptosNoGravados,
            cmp.[Ingresos Brutos] AS ingresosBrutos,
            cmp.Guias AS guias,
            cmp.Comision AS comision,
            cmp.Financiacion AS financiacion,
            cmp.[Gastos Varios] AS gastosVarios,
            cmp.[Ley de Sellos] AS leyDeSellos,
            cmp.[Res gral 4169/96] AS resGral4169,
            cmp.[Ajusta Tipo Cambio] AS ajustaTipoCambio,
            cmp.[Documento Original] AS documentoOriginal
        FROM dbo.Compras cmp
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        WHERE cmp.IdDeuda = ?
    """
    row = fetch_one(sql, (id_compra,))
    if row is None:
        return None
    cabecera = _row_to_compra(row)
    for campo in (
        "tipo",
        "moneda",
        "tipoDeCambio",
        "conceptosNoGravados",
        "ingresosBrutos",
        "guias",
        "comision",
        "financiacion",
        "gastosVarios",
        "leyDeSellos",
        "resGral4169",
        "ajustaTipoCambio",
        "documentoOriginal",
    ):
        cabecera[campo] = row.get(campo)
    return cabecera


def get_lineas_compra(id_compra: int) -> list[dict]:
    sql = """
        SELECT
            dc.IdDetalleCompra AS idDetalleCompra,
            dc.[Producto/Servicio] AS productoServicio,
            dc.Cantidad AS cantidad,
            dc.[Precio Unitario] AS precioUnitario,
            dc.IVA AS iva,
            dc.IdRubro AS idRubro,
            r.Rubro AS rubro,
            dc.IdCentroCostos AS idCentroCosto,
            cc.[Centro de costos] AS centroCosto,
            dc.IdDestino AS idDestino,
            d.Destino AS destino,
            dc.IdCampaña AS idCampania,
            dc.Campaña AS campania
        FROM dbo.Det_Compras dc
        LEFT JOIN dbo.Rubros r ON r.IdRubro = dc.IdRubro
        LEFT JOIN dbo.[Centro de costos] cc ON cc.IdCentro = dc.IdCentroCostos
        LEFT JOIN dbo.DestinoCompras d ON d.IdDestino = dc.IdDestino
        WHERE dc.IdCompra = ?
        ORDER BY dc.IdDetalleCompra ASC
    """
    rows = fetch_all(sql, (id_compra,))
    lineas = []
    for row in rows:
        tiene_imputacion = any(
            row.get(key) is not None
            for key in ("idRubro", "idCentroCosto", "idDestino", "idCampania")
        )
        imputacion = None
        if tiene_imputacion:
            imputacion = {
                "idRubro": row.get("idRubro"),
                "rubro": row.get("rubro"),
                "idCentroCosto": row.get("idCentroCosto"),
                "centroCosto": row.get("centroCosto"),
                "idDestino": row.get("idDestino"),
                "destino": row.get("destino"),
                "idCampania": row.get("idCampania"),
                "campania": row.get("campania"),
            }
        lineas.append(
            {
                "idDetalleCompra": row["idDetalleCompra"],
                "productoServicio": row.get("productoServicio"),
                "cantidad": row.get("cantidad"),
                "precioUnitario": row.get("precioUnitario"),
                "iva": row.get("iva"),
                "imputacion": imputacion,
            }
        )
    return lineas


def get_trazabilidad_compra(id_compra: int) -> list[dict]:
    """Movimientos de cuenta corriente/tesorería originados por la compra.

    `IdOrigen = idCompra` en `vw_MovimientosCuenta_Base` (FR-008). Si no hay
    filas, el llamador MUST exponer "sin movimientos asociados" (FR-009).
    """
    sql = """
        SELECT
            Origen AS origenTipo,
            IdOrigen AS idOrigen,
            Documento AS documento,
            Fecha AS fecha,
            Deuda AS deuda,
            Credito AS credito
        FROM dbo.vw_MovimientosCuenta_Base
        WHERE IdOrigen = ?
        ORDER BY Fecha ASC
    """
    rows = fetch_all(sql, (id_compra,))
    movimientos = []
    for row in rows:
        deuda = row.get("deuda")
        credito = row.get("credito")
        if deuda:
            importe, tipo_importe = deuda, "Deuda"
        else:
            importe, tipo_importe = credito, "Credito"
        movimientos.append(
            {
                "origenTipo": row.get("origenTipo"),
                "idOrigen": row["idOrigen"],
                "documento": row.get("documento"),
                "fecha": row.get("fecha"),
                "importe": importe,
                "tipoImporte": tipo_importe,
            }
        )
    return movimientos


def get_filtros() -> dict:
    """Catálogos para los filtros de búsqueda y para los combos de línea del alta (006).

    Centro de Costos y Rubro replican los combos del formulario Access real
    `Frm Listado Compras`. Destino/Unidad de Medida/Campaña se agregan en
    006-carga-compras para poblar los combos de `Det_Compras` — ampliación
    aditiva, no rompe a los consumidores existentes de 002-compras.
    """
    centros = fetch_all(
        "SELECT IdCentro AS idCentroCosto, [Centro de costos] AS centroCosto "
        "FROM dbo.[Centro de costos] ORDER BY [Centro de costos]"
    )
    rubros = fetch_all("SELECT IdRubro AS idRubro, Rubro AS rubro FROM dbo.Rubros ORDER BY Rubro")
    destinos = fetch_all(
        "SELECT IdDestino AS idDestino, Destino AS destino "
        "FROM dbo.DestinoCompras ORDER BY Destino"
    )
    unidades_medida = fetch_all(
        "SELECT Unidad AS unidad FROM dbo.UnidadesMedida ORDER BY Unidad"
    )
    campañas = fetch_all(
        "SELECT IdCampaña AS idCampania, Campaña AS campania "
        "FROM dbo.Campañas ORDER BY Campaña"
    )
    return {
        "centrosCosto": centros,
        "rubros": rubros,
        "destinos": destinos,
        "unidadesMedida": unidades_medida,
        "campañas": campañas,
    }


def get_id_centro_costo_por_nombre(nombre: str) -> int | None:
    row = fetch_one(
        "SELECT IdCentro FROM dbo.[Centro de costos] WHERE [Centro de costos] = ?", (nombre,)
    )
    return row["IdCentro"] if row else None


def get_id_destino_por_nombre(nombre: str) -> int | None:
    row = fetch_one("SELECT IdDestino FROM dbo.DestinoCompras WHERE Destino = ?", (nombre,))
    return row["IdDestino"] if row else None


def existe_contacto_valido_para_compra(id_contacto: int) -> bool:
    """FR-001/FR-013: el proveedor de una compra puede ser Proveedor/Multiple/Organismo/Empleado/Banco."""
    row = fetch_one(
        "SELECT 1 FROM dbo.Contactos WHERE IdContacto = ? AND [Tipo Contacto] IN "
        "('Proveedor', 'Multiple', 'Organismo', 'Empleado', 'Banco')",
        (id_contacto,),
    )
    return row is not None


def existe_rubro(id_rubro: int) -> bool:
    return fetch_one("SELECT 1 FROM dbo.Rubros WHERE IdRubro = ?", (id_rubro,)) is not None


def existe_centro_costo(id_centro_costo: int) -> bool:
    return (
        fetch_one("SELECT 1 FROM dbo.[Centro de costos] WHERE IdCentro = ?", (id_centro_costo,))
        is not None
    )


def existe_destino(id_destino: int) -> bool:
    return fetch_one("SELECT 1 FROM dbo.DestinoCompras WHERE IdDestino = ?", (id_destino,)) is not None


# Alta controlada de catálogos: los combos de línea (Rubro/Centro de Costos/
# Destino/Campaña) restringen la carga a estos valores (no texto libre);
# agregar uno nuevo pasa por una confirmación explícita en el frontend antes
# de llamar a estas funciones, para evitar duplicados por error de tipeo.

RUBRO_CLASIFICACION_DEFAULT = "Costos"  # valor más frecuente en el catálogo real (44/73 filas)


def create_rubro(nombre: str) -> dict:
    id_rubro = execute_insert_returning_id(
        "INSERT INTO dbo.Rubros (Rubro, Clasificacion) OUTPUT INSERTED.IdRubro VALUES (?, ?)",
        (nombre, RUBRO_CLASIFICACION_DEFAULT),
    )
    return {"idRubro": id_rubro, "rubro": nombre}


def create_centro_costo(nombre: str) -> dict:
    id_centro = execute_insert_returning_id(
        "INSERT INTO dbo.[Centro de costos] ([Centro de costos]) OUTPUT INSERTED.IdCentro VALUES (?)",
        (nombre,),
    )
    return {"idCentroCosto": id_centro, "centroCosto": nombre}


def create_destino(nombre: str) -> dict:
    id_destino = execute_insert_returning_id(
        "INSERT INTO dbo.DestinoCompras (Destino) OUTPUT INSERTED.IdDestino VALUES (?)",
        (nombre,),
    )
    return {"idDestino": id_destino, "destino": nombre}


def create_campania(nombre: str) -> dict:
    id_campania = execute_insert_returning_id(
        "INSERT INTO dbo.Campañas (Campaña) OUTPUT INSERTED.IdCampaña VALUES (?)",
        (nombre,),
    )
    return {"idCampania": id_campania, "campania": nombre}


# --- Documentos relacionados (006-carga-compras): el usuario vincula
# manualmente una Nota de Crédito/Débito (u otro documento) a la Factura que
# complementa, para referencia futura — no es un listado automático de todo
# lo comprado a ese proveedor. Tabla nueva `CompraDocumentosRelacionados`,
# infraestructura de esta app, solo en `WC` (no existe en `LaHerencia`).


def get_documentos_relacionados(id_compra: int) -> list[dict]:
    sql = """
        SELECT
            cmp.IdDeuda AS idCompra,
            cmp.Fecha AS fecha,
            cmp.[Tipo documento] AS tipoDocumento,
            cmp.[Nro Documento] AS numeroDocumento
        FROM dbo.CompraDocumentosRelacionados rel
        JOIN dbo.Compras cmp
            ON cmp.IdDeuda = CASE WHEN rel.IdCompra = ? THEN rel.IdCompraRelacionada ELSE rel.IdCompra END
        WHERE rel.IdCompra = ? OR rel.IdCompraRelacionada = ?
        ORDER BY cmp.Fecha DESC
    """
    return fetch_all(sql, (id_compra, id_compra, id_compra))


def agregar_documento_relacionado(id_compra: int, id_compra_relacionada: int) -> None:
    if id_compra == id_compra_relacionada:
        raise ValueError("Una compra no puede relacionarse consigo misma.")
    if fetch_one("SELECT 1 FROM dbo.Compras WHERE IdDeuda = ?", (id_compra_relacionada,)) is None:
        raise ValueError(f"La compra {id_compra_relacionada} no existe.")
    ya_existe = fetch_one(
        "SELECT 1 FROM dbo.CompraDocumentosRelacionados "
        "WHERE (IdCompra = ? AND IdCompraRelacionada = ?) OR (IdCompra = ? AND IdCompraRelacionada = ?)",
        (id_compra, id_compra_relacionada, id_compra_relacionada, id_compra),
    )
    if ya_existe:
        return
    execute_write(
        "INSERT INTO dbo.CompraDocumentosRelacionados (IdCompra, IdCompraRelacionada, CreatedAt) "
        "VALUES (?, ?, GETDATE())",
        (id_compra, id_compra_relacionada),
    )


def quitar_documento_relacionado(id_compra: int, id_compra_relacionada: int) -> None:
    execute_write(
        "DELETE FROM dbo.CompraDocumentosRelacionados "
        "WHERE (IdCompra = ? AND IdCompraRelacionada = ?) OR (IdCompra = ? AND IdCompraRelacionada = ?)",
        (id_compra, id_compra_relacionada, id_compra_relacionada, id_compra),
    )


ACCESORIOS_CON_IVA_105 = ("comision", "guias", "financiacion", "gastosVarios")

DEFAULT_CENTRO_COSTO = "Adm. General"
DEFAULT_DESTINO = "General"
DEFAULT_CAMPANIA = "No Aplica"


def validar_compra(
    id_contacto: int, moneda: str, tipo_de_cambio: float | None, lineas: list[dict]
) -> list[str]:
    """FR-007/FR-013: errores de validación de aplicación (sin FKs reales en el motor)."""
    errores: list[str] = []

    if not existe_contacto_valido_para_compra(id_contacto):
        errores.append(
            "El contacto seleccionado no existe o no es de un tipo válido para una compra "
            "(Proveedor, Multiple, Organismo, Empleado o Banco)."
        )

    if moneda == "Dolares" and (tipo_de_cambio is None or tipo_de_cambio <= 0):
        errores.append("El tipo de cambio es obligatorio para compras en Dólares.")

    for linea in lineas:
        id_rubro = linea.get("idRubro")
        if id_rubro is not None and not existe_rubro(id_rubro):
            errores.append(f"El rubro {id_rubro} no existe.")
        id_centro_costo = linea.get("idCentroCosto")
        if id_centro_costo is not None and not existe_centro_costo(id_centro_costo):
            errores.append(f"El centro de costos {id_centro_costo} no existe.")
        id_destino = linea.get("idDestino")
        if id_destino is not None and not existe_destino(id_destino):
            errores.append(f"El destino {id_destino} no existe.")

    return errores


def calcular_totales(lineas: list[dict], cabecera: dict) -> dict:
    """Fórmulas confirmadas contra el formulario Access real (`Frm Compras`, ver data-model.md).

    Función pura, sin acceso a base — no confundir con `validar_compra`.
    """
    lineas_calculadas = []
    subtotal_neto = 0.0
    iva_lineas = 0.0
    for linea in lineas:
        subtotal = linea["cantidad"] * linea["precioUnitario"]
        importe_iva = subtotal * linea["iva"] / 100
        subtotal_neto += subtotal
        iva_lineas += importe_iva
        lineas_calculadas.append({**linea, "subtotal": subtotal, "importeIva": importe_iva})

    accesorios = sum(cabecera.get(campo, 0) or 0 for campo in ACCESORIOS_CON_IVA_105)
    iva_cabecera = iva_lineas + 0.105 * accesorios

    importe_total = (
        subtotal_neto
        + iva_cabecera
        + (cabecera.get("ingresosBrutos") or 0)
        + (cabecera.get("conceptosNoGravados") or 0)
        + (cabecera.get("guias") or 0)
        + (cabecera.get("comision") or 0)
        + (cabecera.get("financiacion") or 0)
        + (cabecera.get("gastosVarios") or 0)
        + (cabecera.get("leyDeSellos") or 0)
        + (cabecera.get("resGral4169") or 0)
    )

    pesificado = None
    if cabecera.get("moneda") == "Dolares" and cabecera.get("tipoDeCambio"):
        tc = cabecera["tipoDeCambio"]
        pesificado = {
            "subtotalNeto": subtotal_neto * tc,
            "ivaCabecera": iva_cabecera * tc,
            "importeTotal": importe_total * tc,
        }

    return {
        "lineas": lineas_calculadas,
        "subtotalNeto": subtotal_neto,
        "ivaCabecera": iva_cabecera,
        "importeTotal": importe_total,
        "pesificado": pesificado,
    }


def hay_documento_duplicado(
    id_contacto: int, numero_documento: str, excluir_id_compra: int | None = None
) -> bool:
    sql = (
        "SELECT 1 FROM dbo.Compras "
        "WHERE IdContacto = ? AND [Nro Documento] = ?"
    )
    params: list = [id_contacto, numero_documento]
    if excluir_id_compra is not None:
        sql += " AND IdDeuda <> ?"
        params.append(excluir_id_compra)
    return fetch_one(sql, tuple(params)) is not None


def resolver_defaults_lineas(lineas: list[dict]) -> list[dict]:
    """Versión pública de `_resolver_defaults_linea` para que el router pueda
    construir la respuesta con los mismos valores que `create_compra`/
    `update_compra` efectivamente persisten (FR-011)."""
    return [_resolver_defaults_linea(linea) for linea in lineas]


def _resolver_defaults_linea(linea: dict) -> dict:
    """FR-011: aplica los defaults históricos si la línea llega sin clasificación."""
    resultado = dict(linea)
    if resultado.get("idCentroCosto") is None:
        resultado["idCentroCosto"] = get_id_centro_costo_por_nombre(DEFAULT_CENTRO_COSTO)
    if resultado.get("idDestino") is None:
        resultado["idDestino"] = get_id_destino_por_nombre(DEFAULT_DESTINO)
    if not resultado.get("campaña"):
        resultado["campaña"] = DEFAULT_CAMPANIA
    return resultado


def _cabecera_insert_statement(cabecera: dict):
    def build(_results: list) -> tuple[str, tuple]:
        sql = """
            INSERT INTO dbo.Compras (
                Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda,
                [Tipo de Cambio], [Ingresos Brutos], [Conceptos no gravados], Guias,
                Comision, Financiacion, [Gastos Varios], [Ley de Sellos],
                [Res gral 4169/96], [Ajusta Tipo Cambio], [Documento Original]
            )
            OUTPUT INSERTED.IdDeuda
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            cabecera["fecha"],
            cabecera["idContacto"],
            cabecera["tipo"],
            cabecera["tipoDocumento"],
            cabecera["numeroDocumento"],
            cabecera["moneda"],
            cabecera.get("tipoDeCambio"),
            cabecera.get("ingresosBrutos") or 0,
            cabecera.get("conceptosNoGravados") or 0,
            cabecera.get("guias") or 0,
            cabecera.get("comision") or 0,
            cabecera.get("financiacion") or 0,
            cabecera.get("gastosVarios") or 0,
            cabecera.get("leyDeSellos") or 0,
            cabecera.get("resGral4169") or 0,
            cabecera.get("ajustaTipoCambio") or False,
            cabecera.get("documentoOriginal"),
        )
        return sql, params

    return build


def _cabecera_update_statement(id_compra: int, cabecera: dict) -> tuple[str, tuple]:
    sql = """
        UPDATE dbo.Compras SET
            Fecha = ?, IdContacto = ?, Tipo = ?, [Tipo documento] = ?, [Nro Documento] = ?,
            Moneda = ?, [Tipo de Cambio] = ?, [Ingresos Brutos] = ?, [Conceptos no gravados] = ?,
            Guias = ?, Comision = ?, Financiacion = ?, [Gastos Varios] = ?, [Ley de Sellos] = ?,
            [Res gral 4169/96] = ?, [Ajusta Tipo Cambio] = ?, [Documento Original] = ?
        WHERE IdDeuda = ?
    """
    params = (
        cabecera["fecha"],
        cabecera["idContacto"],
        cabecera["tipo"],
        cabecera["tipoDocumento"],
        cabecera["numeroDocumento"],
        cabecera["moneda"],
        cabecera.get("tipoDeCambio"),
        cabecera.get("ingresosBrutos") or 0,
        cabecera.get("conceptosNoGravados") or 0,
        cabecera.get("guias") or 0,
        cabecera.get("comision") or 0,
        cabecera.get("financiacion") or 0,
        cabecera.get("gastosVarios") or 0,
        cabecera.get("leyDeSellos") or 0,
        cabecera.get("resGral4169") or 0,
        cabecera.get("ajustaTipoCambio") or False,
        cabecera.get("documentoOriginal"),
        id_compra,
    )
    return sql, params


def _linea_insert_statement(linea: dict):
    def build(results: list) -> tuple[str, tuple]:
        id_compra = results[0]
        sql = """
            INSERT INTO dbo.Det_Compras (
                IdCompra, [Producto/Servicio], Cantidad, [Precio Unitario], IVA, Unidad,
                IdCentroCostos, IdDestino, IdRubro, Campaña, [Ajuste financiero]
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            id_compra,
            linea["productoServicio"],
            linea["cantidad"],
            linea["precioUnitario"],
            linea["iva"],
            linea.get("unidad"),
            linea.get("idCentroCosto"),
            linea.get("idDestino"),
            linea.get("idRubro"),
            linea.get("campaña"),
            linea.get("ajusteFinanciero") or False,
        )
        return sql, params

    return build


def _vencimiento_insert_statement(vencimiento: dict):
    def build(results: list) -> tuple[str, tuple]:
        id_compra = results[0]
        sql = "INSERT INTO dbo.[Vencimiento Compras] (IdCompra, [Fecha de vencimiento]) VALUES (?, ?)"
        return sql, (id_compra, vencimiento["fechaVencimiento"])

    return build


def create_compra(cabecera: dict, lineas: list[dict], vencimientos: list[dict]) -> int:
    """Alta transaccional (cabecera+líneas+vencimientos), todo o nada, contra `WC` (FR-002/FR-015).

    Lanza `ValueError` con la lista de errores si `validar_compra` falla —
    el router la traduce a un 400, sin crear ningún registro (FR-002
    Historia 1 Escenario 3).
    """
    errores = validar_compra(
        cabecera["idContacto"], cabecera["moneda"], cabecera.get("tipoDeCambio"), lineas
    )
    if errores:
        raise ValueError(errores)

    lineas_con_defaults = [_resolver_defaults_linea(linea) for linea in lineas]

    statements = [_cabecera_insert_statement(cabecera)]
    for linea in lineas_con_defaults:
        statements.append(_linea_insert_statement(linea))
    for vencimiento in vencimientos:
        statements.append(_vencimiento_insert_statement(vencimiento))

    results = execute_write_transaction(statements)
    return results[0]


def update_compra(id_compra: int, cabecera: dict, lineas: list[dict], vencimientos: list[dict]) -> None:
    """Edición transaccional: reemplazo total de líneas/vencimientos + UPDATE de cabecera (FR-009/FR-010)."""
    errores = validar_compra(
        cabecera["idContacto"], cabecera["moneda"], cabecera.get("tipoDeCambio"), lineas
    )
    if errores:
        raise ValueError(errores)

    lineas_con_defaults = [_resolver_defaults_linea(linea) for linea in lineas]

    statements = [
        ("DELETE FROM dbo.Det_Compras WHERE IdCompra = ?", (id_compra,)),
        ("DELETE FROM dbo.[Vencimiento Compras] WHERE IdCompra = ?", (id_compra,)),
        _cabecera_update_statement(id_compra, cabecera),
    ]
    for linea in lineas_con_defaults:
        statements.append(
            (
                """
                INSERT INTO dbo.Det_Compras (
                    IdCompra, [Producto/Servicio], Cantidad, [Precio Unitario], IVA, Unidad,
                    IdCentroCostos, IdDestino, IdRubro, Campaña, [Ajuste financiero]
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_compra,
                    linea["productoServicio"],
                    linea["cantidad"],
                    linea["precioUnitario"],
                    linea["iva"],
                    linea.get("unidad"),
                    linea.get("idCentroCosto"),
                    linea.get("idDestino"),
                    linea.get("idRubro"),
                    linea.get("campaña"),
                    linea.get("ajusteFinanciero") or False,
                ),
            )
        )
    for vencimiento in vencimientos:
        statements.append(
            (
                "INSERT INTO dbo.[Vencimiento Compras] (IdCompra, [Fecha de vencimiento]) VALUES (?, ?)",
                (id_compra, vencimiento["fechaVencimiento"]),
            )
        )

    execute_write_transaction(statements)


def get_vencimientos_compra(id_compra: int) -> list[dict]:
    rows = fetch_all(
        "SELECT IdVencimiento AS idVencimiento, [Fecha de vencimiento] AS fechaVencimiento "
        "FROM dbo.[Vencimiento Compras] WHERE IdCompra = ? ORDER BY [Fecha de vencimiento] ASC",
        (id_compra,),
    )
    return rows


def get_rubro_sugerido(producto_servicio: str) -> dict | None:
    """FR-012a: rubro más frecuente entre líneas anteriores con el mismo texto exacto."""
    row = fetch_one(
        """
        SELECT TOP 1 dc.IdRubro AS idRubro, r.Rubro AS rubro, COUNT(*) AS frecuencia
        FROM dbo.Det_Compras dc
        JOIN dbo.Rubros r ON r.IdRubro = dc.IdRubro
        WHERE dc.[Producto/Servicio] = ? AND dc.IdRubro IS NOT NULL
        GROUP BY dc.IdRubro, r.Rubro
        ORDER BY COUNT(*) DESC
        """,
        (producto_servicio,),
    )
    return row
