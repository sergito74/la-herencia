"""Parameterized SQL queries for the Tarjetas_Resumenes module.

Cabecera `dbo.Tarjetas_Resumenes` + líneas `dbo.Tarjetas_Resumenes_Lineas`.
Escribe exclusivamente contra `WC` vía `execute_write_transaction` (ver
src/db/connection.py). Fórmulas confirmadas contra datos reales — ver
specs/008-tarjetas/research.md §5 y data-model.md.
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
from src.features.tarjetas_resumenes.conciliacion_documentos import (
    MAX_DOCS_SUGERENCIA,
    calcular_imputacion,
    importe_pesos,
    repartir,
    sugerir,
    tolerancia,
)

_CARGOS = [
    "impuestoSellos",
    "gastosAdmin",
    "mantCuenta",
    "renovAnual",
    "promocionBNA",
    "creditoContingente",
    "intFinanc",
    "intCompens",
    "iva105",
    "percepIVA105",
    "iva21",
    "percepIVA21",
    "percepIIBB",
    "ajusteResAnterior",
]

_CABECERA_COLUMNAS = [
    "IdTarjeta",
    "ResumenCodigo",
    "FechaCierre",
    "FechaVencimiento",
    "ArchivoOrigen",
    "ImpuestoSellos",
    "GastosAdmin",
    "MantCuenta",
    "RenovAnual",
    "PromocionBNA",
    "CreditoContingente",
    "IntFinanc",
    "IntCompens",
    "IVA105",
    "PercepIVA105",
    "IVA21",
    "PercepIVA21",
    "PercepIIBB",
    "AjusteResAnterior",
]


TOLERANCIA_CONCILIACION = 0.10
"""Tolerancia de redondeo para marcar un resumen como conciliado
(feedback del usuario 2026-09-21, análisis del especialista financiero).
`totalCalculado` suma 14 cargos de cabecera + N líneas, cada uno ya
redondeado a 2 decimales en su origen (resumen bancario) — esa
acumulación de redondeos independientes genera una diferencia real y
no evitable contra el pago real del banco. Medido contra los 293
resúmenes reales: 170/188 pagados coinciden exacto, el resto difiere
hasta $0.03 como máximo (no hay ningún caso real entre $0.05 y $0.50).
$0.10 fijo (no proporcional al total — el ruido depende de CUÁNTOS
términos se suman, no de CUÁNTO suman) cubre esos casos reales con
margen y sigue detectando cualquier discrepancia real mayor."""


def _f(value) -> float:
    """pyodbc devuelve `decimal.Decimal` para columnas decimal/money —
    sin este cast, sumarlas con floats literales rompe con TypeError."""
    return float(value) if value is not None else 0.0


def calcular_total(cabecera: dict, lineas: list[dict]) -> float:
    """`Σ(lineas.Importe) + los 14 cargos de cabecera`, cada término con
    su propio signo (data-model.md, research.md §5) — nunca `ABS()`."""
    total = sum(_f(linea.get("importe")) for linea in lineas)
    for campo in _CARGOS:
        total += _f(cabecera.get(campo))
    return total


def existe_tarjeta(id_tarjeta: int) -> bool:
    return fetch_one("SELECT 1 FROM dbo.Tarjetas WHERE IdTarjeta = ?", (id_tarjeta,)) is not None


def validar_resumen(id_tarjeta: int) -> list[str]:
    errores: list[str] = []
    if not existe_tarjeta(id_tarjeta):
        errores.append(f"La tarjeta {id_tarjeta} no existe.")
    return errores


def search_resumenes(
    id_tarjeta: int | None,
    fecha_cierre_desde: date | None,
    fecha_cierre_hasta: date | None,
    fecha_vencimiento_desde: date | None,
    fecha_vencimiento_hasta: date | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """FR-010: sin ningún filtro, no ejecuta la query principal (devuelve vacío)."""
    if not (
        id_tarjeta
        or fecha_cierre_desde
        or fecha_cierre_hasta
        or fecha_vencimiento_desde
        or fecha_vencimiento_hasta
    ):
        return [], 0

    where_clauses: list[str] = []
    params: list = []
    if id_tarjeta:
        where_clauses.append("r.IdTarjeta = ?")
        params.append(id_tarjeta)
    if fecha_cierre_desde:
        where_clauses.append("r.FechaCierre >= ?")
        params.append(as_sql_datetime(fecha_cierre_desde))
    if fecha_cierre_hasta:
        where_clauses.append("r.FechaCierre <= ?")
        params.append(as_sql_datetime(fecha_cierre_hasta))
    if fecha_vencimiento_desde:
        where_clauses.append("r.FechaVencimiento >= ?")
        params.append(as_sql_datetime(fecha_vencimiento_desde))
    if fecha_vencimiento_hasta:
        where_clauses.append("r.FechaVencimiento <= ?")
        params.append(as_sql_datetime(fecha_vencimiento_hasta))

    where_sql = f"WHERE {' AND '.join(where_clauses)}"

    total_row = fetch_one(
        f"SELECT COUNT(*) AS total FROM dbo.Tarjetas_Resumenes r {where_sql}", tuple(params)
    )
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT
            r.IdResumen AS idResumen, r.IdTarjeta AS idTarjeta, t.TarjetaNombre AS tarjeta,
            r.ResumenCodigo AS codigo, r.FechaCierre AS fechaCierre, r.FechaVencimiento AS fechaVencimiento
        FROM dbo.Tarjetas_Resumenes r
        LEFT JOIN dbo.Tarjetas t ON t.IdTarjeta = r.IdTarjeta
        {where_sql}
        ORDER BY r.FechaCierre DESC, r.IdResumen DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    items = []
    for row in rows:
        id_resumen = row["idResumen"]
        # Intenta el auto-vínculo de facturas antes de reportar el estado
        # de conciliación en el listado (feedback 2026-09-20) — el de
        # pagos se corre por separado (GET detalle / alta / edición) para
        # no crear un import circular entre `tarjetas`/`tarjetas_resumenes`.
        auto_vincular_compras(id_resumen)
        cabecera = get_resumen_detalle(id_resumen)
        lineas = get_lineas(id_resumen)
        total_calculado = calcular_total(cabecera, lineas) if cabecera else 0.0
        lineas_vinculadas = sum(1 for l in lineas if l.get("comprasVinculadas"))
        pagado = sum(_f(p.get("importe")) for p in get_pagos(id_resumen))
        diferencia_redondeo = round(total_calculado - pagado, 2)
        items.append(
            {
                "idResumen": id_resumen,
                "idTarjeta": row["idTarjeta"],
                "tarjeta": row["tarjeta"],
                "codigo": row["codigo"],
                "fechaCierre": row["fechaCierre"],
                "fechaVencimiento": row["fechaVencimiento"],
                "urlResumenOriginal": cabecera.get("urlResumenOriginal") if cabecera else None,
                "totalCalculado": total_calculado,
                "soloCabecera": len(lineas) == 0,
                "pagoConciliado": diferencia_redondeo <= TOLERANCIA_CONCILIACION,
                "diferenciaRedondeo": diferencia_redondeo,
                "lineasTotal": len(lineas),
                "lineasVinculadas": lineas_vinculadas,
            }
        )
    return items, total


def get_resumen_detalle(id_resumen: int) -> dict | None:
    sql = """
        SELECT
            r.IdResumen AS idResumen, r.IdTarjeta AS idTarjeta, t.TarjetaNombre AS tarjeta,
            r.ResumenCodigo AS codigo, r.FechaCierre AS fechaCierre, r.FechaVencimiento AS fechaVencimiento,
            r.ArchivoOrigen AS urlResumenOriginal,
            COALESCE(r.ImpuestoSellos, 0) AS impuestoSellos,
            COALESCE(r.GastosAdmin, 0) AS gastosAdmin,
            COALESCE(r.MantCuenta, 0) AS mantCuenta,
            COALESCE(r.RenovAnual, 0) AS renovAnual,
            COALESCE(r.PromocionBNA, 0) AS promocionBNA,
            COALESCE(r.CreditoContingente, 0) AS creditoContingente,
            COALESCE(r.IntFinanc, 0) AS intFinanc,
            COALESCE(r.IntCompens, 0) AS intCompens,
            COALESCE(r.IVA105, 0) AS iva105,
            COALESCE(r.PercepIVA105, 0) AS percepIVA105,
            COALESCE(r.IVA21, 0) AS iva21,
            COALESCE(r.PercepIVA21, 0) AS percepIVA21,
            COALESCE(r.PercepIIBB, 0) AS percepIIBB,
            COALESCE(r.AjusteResAnterior, 0) AS ajusteResAnterior
        FROM dbo.Tarjetas_Resumenes r
        LEFT JOIN dbo.Tarjetas t ON t.IdTarjeta = r.IdTarjeta
        WHERE r.IdResumen = ?
    """
    return fetch_one(sql, (id_resumen,))


def get_lineas(id_resumen: int) -> list[dict]:
    sql = """
        SELECT
            l.IdLineaConsumo AS idLineaConsumo, l.FechaCompra AS fechaCompra, l.Detalle AS detalle,
            l.Importe AS importe, l.FechaVencimientoCompra AS fechaVencimientoCompra,
            l.IdContacto AS idContacto, l.NroDocumento AS nroDocumento,
            e.Estado AS estadoLinea, e.Motivo AS motivoEstado, e.Detalle AS detalleEstado,
            e.ImporteDiferencia AS importeDiferencia
        FROM dbo.Tarjetas_Resumenes_Lineas l
        LEFT JOIN dbo.Tarjetas_Resumenes_Lineas_Estado e ON e.IdLineaConsumo = l.IdLineaConsumo
        WHERE l.IdResumen = ?
        ORDER BY l.IdLineaConsumo ASC
    """
    lineas = fetch_all(sql, (id_resumen,))
    for linea in lineas:
        linea["comprasVinculadas"] = get_compras_vinculadas(linea["idLineaConsumo"])
    return lineas


def get_compras_vinculadas(id_linea_consumo: int) -> list[dict]:
    """Facturas/NC/ND reales (`Compras`) que documentan esta línea de
    consumo (punto 4 del feedback del usuario, 2026-09-19) — una línea
    puede tener varias (más de un proveedor, o el pago parcial de una
    compra en cuotas)."""
    sql = """
        SELECT
            v.IdVinculo AS idVinculo, v.IdCompra AS idCompra, v.ImporteImputado AS importeImputado,
            c.[Razon Social] AS proveedor, cmp.[Tipo documento] AS tipoDocumento,
            cmp.[Nro Documento] AS numeroDocumento, cmp.Fecha AS fechaCompra
        FROM dbo.Tarjetas_Resumenes_Lineas_Compras v
        JOIN dbo.Compras cmp ON cmp.IdDeuda = v.IdCompra
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        WHERE v.IdLineaConsumo = ?
        ORDER BY v.IdVinculo ASC
    """
    return fetch_all(sql, (id_linea_consumo,))


def existe_compra(id_compra: int) -> bool:
    return fetch_one("SELECT 1 FROM dbo.Compras WHERE IdDeuda = ?", (id_compra,)) is not None


def auto_vincular_compras(id_resumen: int) -> int:
    """Vincula automáticamente cada línea de consumo sin vínculo todavía
    con la Compra real que coincide exacto en contacto + número de
    documento — sin pedirle nada al usuario (feedback 2026-09-19, punto 4:
    "esto es engorroso, hay que simplificarlo"). El 96% de las líneas
    reales ya traen `IdContacto`/`NroDocumento` cargados desde el resumen
    del banco, y el 86% de esas matchean exacto contra `Compras` — solo
    el resto (proveedor con formato de documento distinto, o la compra
    nunca se cargó en el sistema) necesita intervención manual. Nunca
    vincula si hay más de una Compra candidata (ambigüedad → manual)."""
    creados = 0
    for linea in get_lineas(id_resumen):
        if linea.get("comprasVinculadas"):
            continue
        id_contacto = linea.get("idContacto")
        nro_documento = linea.get("nroDocumento")
        if not id_contacto or not nro_documento:
            continue
        candidatas = fetch_all(
            "SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?",
            (id_contacto, nro_documento),
        )
        if len(candidatas) != 1:
            continue
        vincular_compra(linea["idLineaConsumo"], candidatas[0]["IdDeuda"], linea["importe"])
        creados += 1
    return creados


_SELECT_DOCUMENTO = """
    SELECT
        w.IdDeuda AS idCompra, w.Fecha AS fecha, w.[Tipo documento] AS tipoDocumento,
        w.[Nro Documento] AS numeroDocumento, w.Moneda AS moneda, w.[Tipo de Cambio] AS tipoDeCambio,
        w.ImporteDocumento AS importeOriginal, c.[Razon Social] AS proveedor,
        cm.[Ajusta Tipo Cambio] AS ajustaTipoCambio, w.IdContacto AS idContacto
    FROM dbo.vw_Compras_ImporteDocumento w
    JOIN dbo.Compras cm ON cm.IdDeuda = w.IdDeuda
    LEFT JOIN dbo.Contactos c ON c.IdContacto = w.IdContacto
"""


def _documento_dict(row: dict) -> dict:
    doc = {
        **row,
        "tipoDeCambio": _f(row["tipoDeCambio"]) if row.get("tipoDeCambio") is not None else None,
        "importeOriginal": _f(row["importeOriginal"]),
        "ajustaTipoCambio": bool(row.get("ajustaTipoCambio")),
    }
    doc["importePesos"] = importe_pesos(doc)
    return doc


def get_linea(id_linea_consumo: int) -> dict | None:
    return fetch_one(
        """
        SELECT IdLineaConsumo AS idLineaConsumo, IdResumen AS idResumen, FechaCompra AS fechaCompra,
               Importe AS importe, IdContacto AS idContacto, NroDocumento AS nroDocumento
        FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdLineaConsumo = ?
        """,
        (id_linea_consumo,),
    )


def get_documentos_por_ids(ids_compra: list[int]) -> list[dict]:
    """Documentos pedidos, en el mismo orden que `ids_compra`."""
    if not ids_compra:
        return []
    marcas = ",".join("?" for _ in ids_compra)
    rows = fetch_all(f"{_SELECT_DOCUMENTO} WHERE w.IdDeuda IN ({marcas})", tuple(ids_compra))
    por_id = {r["idCompra"]: _documento_dict(r) for r in rows}
    return [por_id[i] for i in ids_compra if i in por_id]


def get_documentos_candidatos(id_linea_consumo: int, id_contacto: int, fecha_linea, limite: int = 60) -> list[dict]:
    """Documentos (Factura/NC/ND) del proveedor de la línea, los más cercanos en
    fecha primero, sin los ya vinculados a esta misma línea. Incluye en
    `vinculosPrevios` a cuántas otras líneas están vinculados (un documento en
    cuotas se paga con varias líneas)."""
    sql = f"""
        SELECT TOP (?) w.IdDeuda AS idCompra, w.Fecha AS fecha, w.[Tipo documento] AS tipoDocumento,
            w.[Nro Documento] AS numeroDocumento, w.Moneda AS moneda, w.[Tipo de Cambio] AS tipoDeCambio,
            w.ImporteDocumento AS importeOriginal, c.[Razon Social] AS proveedor,
            cm.[Ajusta Tipo Cambio] AS ajustaTipoCambio,
            (SELECT COUNT(*) FROM dbo.Tarjetas_Resumenes_Lineas_Compras v
              WHERE v.IdCompra = w.IdDeuda AND v.IdLineaConsumo <> ?) AS vinculosPrevios
        FROM dbo.vw_Compras_ImporteDocumento w
        JOIN dbo.Compras cm ON cm.IdDeuda = w.IdDeuda
        LEFT JOIN dbo.Contactos c ON c.IdContacto = w.IdContacto
        WHERE w.IdContacto = ? AND ISNULL(w.ImporteDocumento, 0) <> 0
          AND NOT EXISTS (
              SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Compras v2
              WHERE v2.IdCompra = w.IdDeuda AND v2.IdLineaConsumo = ?)
        ORDER BY ABS(DATEDIFF(day, w.Fecha, ?)) ASC, w.IdDeuda DESC
    """
    rows = fetch_all(
        sql, (limite, id_linea_consumo, id_contacto, id_linea_consumo, as_sql_datetime(fecha_linea))
    )
    return [_documento_dict(r) for r in rows]


MOTIVOS_DIFERENCIA = {"AjusteTipoCambioSinNota", "Redondeo", "Otro"}
MOTIVOS_SIN_DOCUMENTO = {"Impuesto", "Interes", "CompraNoCargada", "Otro"}

_SIN_RESOLVER = """
    NOT EXISTS (SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Compras v WHERE v.IdLineaConsumo = l.IdLineaConsumo)
    AND NOT EXISTS (SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Estado e WHERE e.IdLineaConsumo = l.IdLineaConsumo)
"""


def get_estado(id_linea_consumo: int) -> dict | None:
    return fetch_one(
        "SELECT IdLineaConsumo AS idLineaConsumo, Estado AS estado, Motivo AS motivo, Detalle AS detalle, "
        "ImporteDiferencia AS importeDiferencia FROM dbo.Tarjetas_Resumenes_Lineas_Estado WHERE IdLineaConsumo = ?",
        (id_linea_consumo,),
    )


def _validar_motivo(estado: str, motivo: str | None, detalle: str | None) -> None:
    validos = MOTIVOS_DIFERENCIA if estado == "DiferenciaAceptada" else MOTIVOS_SIN_DOCUMENTO
    if motivo not in validos:
        raise ValueError([f"Motivo inválido: {motivo!r}. Opciones: {sorted(validos)}."])
    if motivo == "Otro" and not (detalle or "").strip():
        raise ValueError(["Indicá el detalle cuando el motivo es «Otro»."])


def _stmt_estado(id_linea: int, estado: str, motivo: str, detalle: str | None, importe_dif: float | None) -> tuple:
    return (
        "INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Estado (IdLineaConsumo, Estado, Motivo, Detalle, ImporteDiferencia) "
        "VALUES (?, ?, ?, ?, ?)",
        (id_linea, estado, motivo, (detalle or "").strip() or None, importe_dif),
    )


def _stmts_relaciones(docs: list[dict]) -> list[tuple]:
    """Asocia cada nota de ajuste de tipo de cambio con las facturas en dólares
    de la misma conciliación (tabla `CompraDocumentosRelacionados`, ya usada para
    relacionar NC/ND con su factura)."""
    ajustes = [d for d in docs if d.get("ajustaTipoCambio")]
    facturas = [d for d in docs if d.get("moneda") == "Dolares" and not d.get("ajustaTipoCambio")]
    stmts = []
    for a in ajustes:
        for f in facturas:
            stmts.append(
                (
                    "INSERT INTO dbo.CompraDocumentosRelacionados (IdCompra, IdCompraRelacionada, CreatedAt) "
                    "SELECT ?, ?, GETDATE() WHERE NOT EXISTS (SELECT 1 FROM dbo.CompraDocumentosRelacionados "
                    "WHERE (IdCompra = ? AND IdCompraRelacionada = ?) OR (IdCompra = ? AND IdCompraRelacionada = ?))",
                    (f["idCompra"], a["idCompra"], f["idCompra"], a["idCompra"], a["idCompra"], f["idCompra"]),
                )
            )
    return stmts


def _asegurar_pendiente(id_linea: int) -> dict:
    linea = get_linea(id_linea)
    if linea is None:
        raise ValueError([f"La línea {id_linea} no existe."])
    if get_compras_vinculadas(id_linea):
        raise ValueError([f"La línea {id_linea} ya tiene documentos vinculados."])
    if get_estado(id_linea):
        raise ValueError([f"La línea {id_linea} ya está resuelta."])
    return linea


def get_linea_contexto(id_linea_consumo: int) -> dict | None:
    return fetch_one(
        """
        SELECT l.IdLineaConsumo AS idLineaConsumo, l.IdResumen AS idResumen, l.FechaCompra AS fechaCompra,
               l.Detalle AS detalle, l.Importe AS importe, l.IdContacto AS idContacto, l.NroDocumento AS nroDocumento,
               r.ResumenCodigo AS resumenCodigo, r.ArchivoOrigen AS urlResumenOriginal, t.TarjetaNombre AS tarjeta,
               c.[Razon Social] AS proveedor
        FROM dbo.Tarjetas_Resumenes_Lineas l
        JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen
        LEFT JOIN dbo.Tarjetas t ON t.IdTarjeta = r.IdTarjeta
        LEFT JOIN dbo.Contactos c ON c.IdContacto = l.IdContacto
        WHERE l.IdLineaConsumo = ?
        """,
        (id_linea_consumo,),
    )


def get_lineas_hermanas(id_linea_consumo: int, id_contacto: int, limite: int = 20) -> list[dict]:
    """Otras líneas pendientes del mismo proveedor (para conciliarlas juntas)."""
    sql = f"""
        SELECT TOP (?) l.IdLineaConsumo AS idLineaConsumo, l.IdResumen AS idResumen, r.ResumenCodigo AS resumenCodigo,
               l.FechaCompra AS fechaCompra, l.Detalle AS detalle, l.Importe AS importe
        FROM dbo.Tarjetas_Resumenes_Lineas l
        JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen
        WHERE l.IdContacto = ? AND l.IdLineaConsumo <> ? AND {_SIN_RESOLVER}
        ORDER BY r.FechaCierre DESC, l.IdLineaConsumo
    """
    rows = fetch_all(sql, (limite, id_contacto, id_linea_consumo))
    return [{**r, "importe": _f(r["importe"])} for r in rows]


def get_candidatos_linea(id_linea_consumo: int) -> dict | None:
    contexto = get_linea_contexto(id_linea_consumo)
    if contexto is None:
        return None
    importe = _f(contexto["importe"])
    id_contacto = contexto.get("idContacto")
    documentos = (
        get_documentos_candidatos(id_linea_consumo, id_contacto, contexto["fechaCompra"]) if id_contacto else []
    )
    return {
        "idLineaConsumo": id_linea_consumo,
        "importeLinea": importe,
        "fechaLinea": contexto["fechaCompra"],
        "idContacto": id_contacto,
        "linea": {**contexto, "importe": importe},
        "estado": get_estado(id_linea_consumo),
        "hermanas": get_lineas_hermanas(id_linea_consumo, id_contacto) if id_contacto else [],
        "documentos": documentos,
        "sugerencias": sugerir(importe, documentos[:MAX_DOCS_SUGERENCIA]),
    }


def buscar_documentos(texto: str, limite: int = 40) -> list[dict]:
    """Documentos por proveedor (razón social) o número de documento, para sumar
    a una conciliación documentos de otros proveedores."""
    patron = f"%{texto.strip()}%"
    sql = f"""
        SELECT TOP (?) w.IdDeuda AS idCompra, w.Fecha AS fecha, w.[Tipo documento] AS tipoDocumento,
            w.[Nro Documento] AS numeroDocumento, w.Moneda AS moneda, w.[Tipo de Cambio] AS tipoDeCambio,
            w.ImporteDocumento AS importeOriginal, c.[Razon Social] AS proveedor,
            cm.[Ajusta Tipo Cambio] AS ajustaTipoCambio,
            (SELECT COUNT(*) FROM dbo.Tarjetas_Resumenes_Lineas_Compras v WHERE v.IdCompra = w.IdDeuda) AS vinculosPrevios
        FROM dbo.vw_Compras_ImporteDocumento w
        JOIN dbo.Compras cm ON cm.IdDeuda = w.IdDeuda
        LEFT JOIN dbo.Contactos c ON c.IdContacto = w.IdContacto
        WHERE ISNULL(w.ImporteDocumento, 0) <> 0
          AND (c.[Razon Social] LIKE ? OR w.[Nro Documento] LIKE ?)
        ORDER BY w.Fecha DESC, w.IdDeuda DESC
    """
    return [_documento_dict(r) for r in fetch_all(sql, (limite, patron, patron))]


def get_documentos_de_contactos(ids_contacto: list[int]) -> dict[int, list[dict]]:
    if not ids_contacto:
        return {}
    marcas = ",".join("?" for _ in ids_contacto)
    rows = fetch_all(
        f"{_SELECT_DOCUMENTO} WHERE w.IdContacto IN ({marcas}) AND ISNULL(w.ImporteDocumento, 0) <> 0",
        tuple(ids_contacto),
    )
    por_contacto: dict[int, list[dict]] = {}
    for r in rows:
        por_contacto.setdefault(r["idContacto"], []).append(_documento_dict(r))
    return por_contacto


def _cercania(doc: dict, fecha_linea) -> int:
    f, l = doc.get("fecha"), fecha_linea
    try:
        return abs((f - l).days)
    except TypeError:
        return 10**6


def _resumen_doc(d: dict) -> dict:
    return {k: d.get(k) for k in ("idCompra", "tipoDocumento", "numeroDocumento", "moneda", "importeOriginal", "importePesos", "proveedor")}


def get_pendientes(
    id_tarjeta: int | None = None,
    proveedor: str | None = None,
    fecha_cierre_desde=None,
    fecha_cierre_hasta=None,
) -> list[dict]:
    """Líneas de consumo sin conciliar (sin documentos vinculados ni estado),
    cada una con la mejor sugerencia exacta si existe. Las que tienen sugerencia
    van primero; dentro de cada grupo, los resúmenes más recientes primero."""
    where = [_SIN_RESOLVER]
    params: list = []
    if id_tarjeta is not None:
        where.append("r.IdTarjeta = ?")
        params.append(id_tarjeta)
    if proveedor:
        where.append("c.[Razon Social] LIKE ?")
        params.append(f"%{proveedor.strip()}%")
    if fecha_cierre_desde is not None:
        where.append("r.FechaCierre >= ?")
        params.append(as_sql_datetime(fecha_cierre_desde))
    if fecha_cierre_hasta is not None:
        where.append("r.FechaCierre <= ?")
        params.append(as_sql_datetime(fecha_cierre_hasta))
    rows = fetch_all(
        f"""
        SELECT l.IdLineaConsumo AS idLineaConsumo, l.IdResumen AS idResumen, r.ResumenCodigo AS resumenCodigo,
               r.IdTarjeta AS idTarjeta, t.TarjetaNombre AS tarjeta, r.FechaCierre AS fechaCierre,
               l.FechaCompra AS fechaCompra, l.Detalle AS detalle, l.Importe AS importe, l.IdContacto AS idContacto,
               c.[Razon Social] AS proveedor, l.NroDocumento AS nroDocumento, r.ArchivoOrigen AS urlResumenOriginal
        FROM dbo.Tarjetas_Resumenes_Lineas l
        JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen
        LEFT JOIN dbo.Tarjetas t ON t.IdTarjeta = r.IdTarjeta
        LEFT JOIN dbo.Contactos c ON c.IdContacto = l.IdContacto
        WHERE {' AND '.join(where)}
        ORDER BY r.FechaCierre DESC, l.IdLineaConsumo ASC
        """,
        tuple(params),
    )
    docs_por_contacto = get_documentos_de_contactos(sorted({r["idContacto"] for r in rows if r.get("idContacto")}))
    items = []
    for r in rows:
        importe = _f(r["importe"])
        docs = sorted(docs_por_contacto.get(r.get("idContacto"), []), key=lambda d: _cercania(d, r["fechaCompra"]))
        sugerencias = sugerir(importe, docs[:MAX_DOCS_SUGERENCIA])
        por_id = {d["idCompra"]: d for d in docs}
        mejor = None
        if sugerencias:
            s = sugerencias[0]
            mejor = {
                "idsCompra": s["idsCompra"],
                "estado": s["estado"],
                "unica": len(sugerencias) == 1,
                "documentos": [_resumen_doc(por_id[i]) for i in s["idsCompra"]],
            }
        items.append({**r, "importe": importe, "cantidadDocumentos": len(docs), "sugerencia": mejor})
    items.sort(key=lambda x: 0 if x["sugerencia"] else 1)
    return items


def get_exactas_propuestas() -> list[dict]:
    """Líneas cuya sugerencia exacta es segura de aplicar en bloque: única, sin
    documentos en dólares y sin que ningún documento se repita en otra propuesta."""
    candidatas = [
        p
        for p in get_pendientes()
        if p["sugerencia"]
        and p["sugerencia"]["unica"]
        and all(d["moneda"] != "Dolares" for d in p["sugerencia"]["documentos"])
    ]
    uso: dict[int, int] = {}
    for p in candidatas:
        for i in p["sugerencia"]["idsCompra"]:
            uso[i] = uso.get(i, 0) + 1
    return [p for p in candidatas if all(uso[i] == 1 for i in p["sugerencia"]["idsCompra"])]


def aceptar_exactas(ids_lineas: list[int]) -> dict:
    propuestas = {p["idLineaConsumo"]: p for p in get_exactas_propuestas()}
    aplicadas, omitidas = 0, []
    for id_linea in ids_lineas:
        p = propuestas.get(id_linea)
        if p is None:
            omitidas.append(id_linea)
            continue
        try:
            vincular_compras_lote(id_linea, p["sugerencia"]["idsCompra"])
            aplicadas += 1
        except ValueError:
            omitidas.append(id_linea)
    return {"aplicadas": aplicadas, "omitidas": omitidas}


def calcular_conciliacion(id_linea_consumo: int, ids_compra: list[int]) -> dict:
    """Cómo se repartiría la línea entre los documentos elegidos (ver
    `conciliacion_documentos`). `ValueError` si algo no existe o se repite."""
    if len(set(ids_compra)) != len(ids_compra):
        raise ValueError(["Hay documentos repetidos en la selección."])
    linea = get_linea(id_linea_consumo)
    if linea is None:
        raise ValueError([f"La línea {id_linea_consumo} no existe."])
    docs = get_documentos_por_ids(ids_compra)
    faltantes = set(ids_compra) - {d["idCompra"] for d in docs}
    if faltantes:
        raise ValueError([f"No existen las compras: {sorted(faltantes)}."])
    calculo = calcular_imputacion(_f(linea["importe"]), docs)
    return {"documentos": docs, **calculo}


def vincular_compras_lote(id_linea_consumo: int, ids_compra: list[int], aceptar_diferencia: dict | None = None) -> list[dict]:
    """Vincula varios documentos a una línea en una sola transacción (todo o
    nada). Si la suma no cierra con la línea hace falta `aceptar_diferencia`
    (`motivo`, `detalle`), que además queda registrada como estado de la línea.
    Un único documento en pesos que no coincide es un pago parcial (cuota) y no
    requiere motivo."""
    if not ids_compra:
        raise ValueError(["Elegí al menos un documento."])
    _asegurar_pendiente(id_linea_consumo)
    calculo = calcular_conciliacion(id_linea_consumo, ids_compra)
    statements: list = [
        (
            "INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) VALUES (?, ?, ?)",
            (id_linea_consumo, i["idCompra"], i["importeImputado"]),
        )
        for i in calculo["imputados"]
    ]
    if calculo["estado"] == "parcial" and not calculo["pagoParcial"]:
        if not aceptar_diferencia:
            raise ValueError(
                [f"La suma de los documentos no cierra con la línea (diferencia {calculo['diferencia']:,.2f}). "
                 "Aceptá la diferencia con un motivo o cambiá la selección."]
            )
        _validar_motivo("DiferenciaAceptada", aceptar_diferencia.get("motivo"), aceptar_diferencia.get("detalle"))
        statements.append(
            _stmt_estado(id_linea_consumo, "DiferenciaAceptada", aceptar_diferencia["motivo"], aceptar_diferencia.get("detalle"), calculo["diferencia"])
        )
    statements.extend(_stmts_relaciones(calculo["documentos"]))
    execute_write_transaction(statements)
    return get_compras_vinculadas(id_linea_consumo)


def marcar_sin_documento(id_linea_consumo: int, motivo: str, detalle: str | None) -> None:
    _validar_motivo("SinDocumento", motivo, detalle)
    _asegurar_pendiente(id_linea_consumo)
    execute_write_transaction([_stmt_estado(id_linea_consumo, "SinDocumento", motivo, detalle, None)])


def quitar_estado(id_linea_consumo: int) -> None:
    execute_write("DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Estado WHERE IdLineaConsumo = ?", (id_linea_consumo,))


def proponer_reparto(ids_lineas: list[int], ids_compra: list[int]) -> dict:
    """Propuesta de reparto de varias líneas entre varios documentos (editable
    por el usuario antes de guardar)."""
    if len(set(ids_lineas)) != len(ids_lineas) or len(set(ids_compra)) != len(ids_compra):
        raise ValueError(["Hay líneas o documentos repetidos en la selección."])
    lineas = []
    for i in ids_lineas:
        l = _asegurar_pendiente(i)
        lineas.append({"idLinea": i, "importe": _f(l["importe"]), "fechaCompra": l["fechaCompra"]})
    docs = get_documentos_por_ids(ids_compra)
    faltantes = set(ids_compra) - {d["idCompra"] for d in docs}
    if faltantes:
        raise ValueError([f"No existen las compras: {sorted(faltantes)}."])
    lineas.sort(key=lambda l: (l["fechaCompra"], l["idLinea"]))
    propuesta = repartir(lineas, docs)
    return {"lineas": lineas, "documentos": docs, **propuesta}


def conciliar_reparto(reparto: list[dict], aceptar_diferencia: dict | None = None) -> dict:
    """Guarda, en una transacción, el reparto de varias líneas entre varios
    documentos. Cada línea debe cerrar con lo asignado (±tolerancia); las que no,
    requieren `aceptar_diferencia` (mismo motivo para todas)."""
    por_linea: dict[int, list[dict]] = {}
    for r in reparto:
        por_linea.setdefault(r["idLinea"], []).append(r)
    docs = {d["idCompra"]: d for d in get_documentos_por_ids(sorted({r["idCompra"] for r in reparto}))}
    faltantes = {r["idCompra"] for r in reparto} - set(docs)
    if faltantes:
        raise ValueError([f"No existen las compras: {sorted(faltantes)}."])

    statements: list = []
    no_cierran: list[tuple[int, float]] = []
    for id_linea, items in por_linea.items():
        linea = _asegurar_pendiente(id_linea)
        docs_linea = [docs[i["idCompra"]] for i in items]
        asignado = round(sum(i["importe"] for i in items), 2)
        diferencia = round(_f(linea["importe"]) - asignado, 2)
        for i in items:
            statements.append(
                (
                    "INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) VALUES (?, ?, ?)",
                    (id_linea, i["idCompra"], i["importe"]),
                )
            )
        statements.extend(_stmts_relaciones(docs_linea))
        if abs(diferencia) > tolerancia(docs_linea):
            no_cierran.append((id_linea, diferencia))

    if no_cierran:
        if not aceptar_diferencia:
            detalle = "; ".join(f"línea {i}: {d:,.2f}" for i, d in no_cierran)
            raise ValueError([f"Hay líneas que no cierran ({detalle}). Aceptá la diferencia con un motivo o ajustá el reparto."])
        _validar_motivo("DiferenciaAceptada", aceptar_diferencia.get("motivo"), aceptar_diferencia.get("detalle"))
        for id_linea, diferencia in no_cierran:
            statements.append(
                _stmt_estado(id_linea, "DiferenciaAceptada", aceptar_diferencia["motivo"], aceptar_diferencia.get("detalle"), diferencia)
            )
    execute_write_transaction(statements)
    return {"lineas": len(por_linea), "vinculos": len(reparto)}


def vincular_compra(id_linea_consumo: int, id_compra: int, importe_imputado: float) -> int:
    if not existe_compra(id_compra):
        raise ValueError([f"La compra {id_compra} no existe."])
    return execute_insert_returning_id(
        "INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) "
        "OUTPUT INSERTED.IdVinculo VALUES (?, ?, ?)",
        (id_linea_consumo, id_compra, importe_imputado),
    )


def quitar_vinculo_compra(id_vinculo: int) -> None:
    execute_write("DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdVinculo = ?", (id_vinculo,))


def get_pagos(id_resumen: int) -> list[dict]:
    sql = """
        SELECT IdPago AS idPago, Fecha AS fecha, Importe AS importe, Origen AS origen,
               IdMovimientoOrigen AS idMovimientoOrigen
        FROM dbo.Tarjetas_Resumenes_Pagos
        WHERE IdResumen = ?
        ORDER BY Fecha ASC, IdPago ASC
    """
    return fetch_all(sql, (id_resumen,))


def registrar_pago(id_resumen: int, fecha, importe: float, origen: str | None, id_movimiento_origen: int | None) -> int:
    return execute_insert_returning_id(
        "INSERT INTO dbo.Tarjetas_Resumenes_Pagos (IdResumen, Fecha, Importe, Origen, IdMovimientoOrigen) "
        "OUTPUT INSERTED.IdPago VALUES (?, ?, ?, ?, ?)",
        (id_resumen, as_sql_datetime(fecha), importe, origen, id_movimiento_origen),
    )


def eliminar_pago(id_pago: int) -> None:
    execute_write("DELETE FROM dbo.Tarjetas_Resumenes_Pagos WHERE IdPago = ?", (id_pago,))


def hay_resumen_duplicado(id_tarjeta: int, codigo: str, excluir_id_resumen: int | None = None) -> bool:
    """FR-012: advertencia no bloqueante — nunca bloquea el guardado."""
    sql = "SELECT 1 FROM dbo.Tarjetas_Resumenes WHERE IdTarjeta = ? AND ResumenCodigo = ?"
    params: list = [id_tarjeta, codigo]
    if excluir_id_resumen is not None:
        sql += " AND IdResumen <> ?"
        params.append(excluir_id_resumen)
    return fetch_one(sql, tuple(params)) is not None


def _cabecera_params(cabecera: dict) -> tuple:
    return (
        cabecera["idTarjeta"],
        cabecera["codigo"],
        as_sql_datetime(cabecera["fechaCierre"]),
        as_sql_datetime(cabecera["fechaVencimiento"]),
        cabecera.get("urlResumenOriginal"),
        *[cabecera.get(campo) or 0 for campo in _CARGOS],
    )


def _cabecera_insert_statement(cabecera: dict):
    def build(_results: list) -> tuple[str, tuple]:
        columnas_sql = ", ".join(_CABECERA_COLUMNAS)
        placeholders = ", ".join("?" for _ in _CABECERA_COLUMNAS)
        sql = (
            f"INSERT INTO dbo.Tarjetas_Resumenes ({columnas_sql}) "
            f"OUTPUT INSERTED.IdResumen VALUES ({placeholders})"
        )
        return sql, _cabecera_params(cabecera)

    return build


def _cabecera_update_statement(id_resumen: int, cabecera: dict) -> tuple[str, tuple]:
    set_clause = ", ".join(f"{c} = ?" for c in _CABECERA_COLUMNAS)
    sql = f"UPDATE dbo.Tarjetas_Resumenes SET {set_clause} WHERE IdResumen = ?"
    return sql, _cabecera_params(cabecera) + (id_resumen,)


def _linea_insert_statement(linea: dict):
    def build(results: list) -> tuple[str, tuple]:
        id_resumen = results[0]
        sql = (
            "INSERT INTO dbo.Tarjetas_Resumenes_Lineas "
            "(IdResumen, FechaCompra, Detalle, Importe, FechaVencimientoCompra, IdContacto, NroDocumento) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        return sql, (
            id_resumen,
            as_sql_datetime(linea["fechaCompra"]),
            linea["detalle"],
            linea["importe"],
            as_sql_datetime(linea["fechaVencimientoCompra"]) if linea.get("fechaVencimientoCompra") else None,
            linea.get("idContacto"),
            linea.get("nroDocumento"),
        )

    return build


def create_resumen(cabecera: dict, lineas: list[dict]) -> int:
    errores = validar_resumen(cabecera["idTarjeta"])
    if errores:
        raise ValueError(errores)

    statements = [_cabecera_insert_statement(cabecera)]
    for linea in lineas:
        statements.append(_linea_insert_statement(linea))

    results = execute_write_transaction(statements)
    return results[0]


def update_resumen(id_resumen: int, cabecera: dict, lineas: list[dict]) -> None:
    """Reemplazo total de líneas (mismo criterio que el resto de la app).
    Borra primero los vínculos a `Compras` (punto 4 del feedback,
    2026-09-19) — de lo contrario quedarían huérfanos apuntando a un
    `IdLineaConsumo` que ya no existe, perdiendo silenciosamente el
    vínculo cada vez que se edita un resumen."""
    errores = validar_resumen(cabecera["idTarjeta"])
    if errores:
        raise ValueError(errores)

    statements: list = [
        (
            "DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo IN "
            "(SELECT IdLineaConsumo FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdResumen = ?)",
            (id_resumen,),
        ),
        (
            "DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Estado WHERE IdLineaConsumo IN "
            "(SELECT IdLineaConsumo FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdResumen = ?)",
            (id_resumen,),
        ),
        ("DELETE FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdResumen = ?", (id_resumen,)),
        _cabecera_update_statement(id_resumen, cabecera),
    ]
    for linea in lineas:
        statements.append(
            (
                "INSERT INTO dbo.Tarjetas_Resumenes_Lineas "
                "(IdResumen, FechaCompra, Detalle, Importe, FechaVencimientoCompra, IdContacto, NroDocumento) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    id_resumen,
                    as_sql_datetime(linea["fechaCompra"]),
                    linea["detalle"],
                    linea["importe"],
                    as_sql_datetime(linea["fechaVencimientoCompra"]) if linea.get("fechaVencimientoCompra") else None,
                    linea.get("idContacto"),
                    linea.get("nroDocumento"),
                ),
            )
        )
    execute_write_transaction(statements)


def delete_resumen(id_resumen: int) -> None:
    statements = [
        (
            "DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo IN "
            "(SELECT IdLineaConsumo FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdResumen = ?)",
            (id_resumen,),
        ),
        (
            "DELETE FROM dbo.Tarjetas_Resumenes_Lineas_Estado WHERE IdLineaConsumo IN "
            "(SELECT IdLineaConsumo FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdResumen = ?)",
            (id_resumen,),
        ),
        ("DELETE FROM dbo.Tarjetas_Resumenes_Lineas WHERE IdResumen = ?", (id_resumen,)),
        ("DELETE FROM dbo.Tarjetas_Resumenes_Pagos WHERE IdResumen = ?", (id_resumen,)),
        ("DELETE FROM dbo.TarjetaResumenEditLocks WHERE IdResumen = ?", (id_resumen,)),
        ("DELETE FROM dbo.Tarjetas_Resumenes WHERE IdResumen = ?", (id_resumen,)),
    ]
    execute_write_transaction(statements)
