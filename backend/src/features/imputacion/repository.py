"""Acceso a datos del motor de auto-clasificación (017-imputacion-automatica-costos)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone


class CorridaNoVigente(Exception):
    """La corrida que se intenta aprobar ya no es la vigente para su renglón (409)."""

from src.db.connection import execute_write_transaction, fetch_all, fetch_one

_COLUMNAS = (
    "p.IdPropuesta AS idPropuesta, p.IdCorrida AS idCorrida, p.Origen AS origen, "
    "p.IdDetalleCompra AS idDetalleCompra, p.IdOrdenTrabajo AS idOrdenTrabajo, "
    "p.IdLote AS idLote, p.IdCultivo AS idCultivo, p.IdCampania AS idCampania, "
    "p.IdCentroCosto AS idCentroCosto, p.EsGanaderia AS esGanaderia, p.Importe AS importe, "
    "p.Estado AS estado, p.FechaCalculo AS fechaCalculo, p.FechaAprobacion AS fechaAprobacion"
)


def guardar_corrida(origen: str, id_detalle_compra: int, fracciones: list[dict]) -> str:
    """Inserta una corrida nueva (todas sus fracciones) con un `IdCorrida` propio.

    No borra ni toca corridas anteriores de ese renglón — la vigente es
    siempre la de `FechaCalculo` más reciente (`corrida_vigente`). Cada
    fracción es un dict con las claves de `ImputacionPropuestas` (salvo
    `idPropuesta`/`idCorrida`/`fechaCalculo`, que pone esta función); si no
    trae `estado`, se guarda `'Pendiente'`.
    """
    if not fracciones:
        raise ValueError("guardar_corrida requiere al menos una fracción")

    id_corrida = str(uuid.uuid4())
    statements = [
        (
            "INSERT INTO dbo.ImputacionPropuestas "
            "(IdCorrida, Origen, IdDetalleCompra, IdOrdenTrabajo, IdLote, IdCultivo, IdCampania, "
            "IdCentroCosto, EsGanaderia, Importe, Estado, FechaAprobacion) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                id_corrida,
                origen,
                id_detalle_compra,
                f.get("idOrdenTrabajo"),
                f.get("idLote"),
                f.get("idCultivo"),
                f.get("idCampania"),
                f.get("idCentroCosto"),
                f.get("esGanaderia"),
                f["importe"],
                f.get("estado", "Pendiente"),
                f.get("fechaAprobacion"),
            ),
        )
        for f in fracciones
    ]
    execute_write_transaction(statements)
    return id_corrida


def detalle_compra_de_corrida(id_corrida: str) -> int | None:
    fila = fetch_one("SELECT TOP 1 IdDetalleCompra FROM dbo.ImputacionPropuestas WHERE IdCorrida = ?", (id_corrida,))
    return fila["IdDetalleCompra"] if fila else None


def origen_de_corrida(id_corrida: str) -> str | None:
    fila = fetch_one("SELECT TOP 1 Origen FROM dbo.ImputacionPropuestas WHERE IdCorrida = ?", (id_corrida,))
    return fila["Origen"] if fila else None


def info_fraccion(id_propuesta: int) -> dict | None:
    fila = fetch_one(
        "SELECT p.IdDetalleCompra AS idDetalleCompra, dc.IdFormulado AS idProducto, p.EsGanaderia AS esGanaderia "
        "FROM dbo.ImputacionPropuestas p JOIN dbo.Det_Compras dc ON dc.IdDetalleCompra = p.IdDetalleCompra "
        "WHERE p.IdPropuesta = ?",
        (id_propuesta,),
    )
    return fila


def actualizar_referencia(id_producto: int, es_ganaderia: bool, id_cultivo: int | None, id_campania: int | None) -> None:
    """UPSERT en `ImputacionReferencias` (lado de escritura del aprendizaje
    simple, FR-008 — el lado de lectura es `obtener_referencia`)."""
    execute_write_transaction(
        [
            (
                "IF EXISTS (SELECT 1 FROM dbo.ImputacionReferencias WHERE IdProducto = ? AND EsGanaderia = ?) "
                "UPDATE dbo.ImputacionReferencias SET IdCultivo = ?, IdCampania = ?, FechaActualizacion = SYSUTCDATETIME() "
                "WHERE IdProducto = ? AND EsGanaderia = ? "
                "ELSE "
                "INSERT INTO dbo.ImputacionReferencias (IdProducto, EsGanaderia, IdCultivo, IdCampania) VALUES (?, ?, ?, ?)",
                (
                    id_producto, 1 if es_ganaderia else 0,
                    id_cultivo, id_campania, id_producto, 1 if es_ganaderia else 0,
                    id_producto, 1 if es_ganaderia else 0, id_cultivo, id_campania,
                ),
            )
        ]
    )


def aprobar_corrida(id_corrida: str, correcciones: list[dict] | None = None) -> None:
    """Marca toda la corrida como `Aprobada`, aplicando primero las
    correcciones puntuales que traiga (FR-007), y actualiza `ImputacionReferencias`
    para los productos corregidos (FR-008). 409 si la corrida ya no es la
    vigente de su renglón."""
    id_detalle_compra = detalle_compra_de_corrida(id_corrida)
    if id_detalle_compra is None:
        raise ValueError(f"Corrida {id_corrida} no existe")
    if corrida_vigente(id_detalle_compra) != id_corrida:
        raise CorridaNoVigente(f"Corrida {id_corrida} ya no es la vigente para el renglón {id_detalle_compra}")

    statements: list = []
    for c in correcciones or []:
        sets, params = [], []
        for campo, columna in (("idLote", "IdLote"), ("idCultivo", "IdCultivo"), ("idCampania", "IdCampania"), ("importe", "Importe")):
            if c.get(campo) is not None:
                sets.append(f"{columna} = ?")
                params.append(c[campo])
        if sets:
            params.append(c["idPropuesta"])
            statements.append((f"UPDATE dbo.ImputacionPropuestas SET {', '.join(sets)} WHERE IdPropuesta = ?", tuple(params)))

    statements.append(
        (
            "UPDATE dbo.ImputacionPropuestas SET Estado = 'Aprobada', FechaAprobacion = SYSUTCDATETIME() WHERE IdCorrida = ?",
            (id_corrida,),
        )
    )
    execute_write_transaction(statements)

    for c in correcciones or []:
        if c.get("idCultivo") is None and c.get("idCampania") is None:
            continue
        fraccion = info_fraccion(c["idPropuesta"])
        if fraccion is None or fraccion.get("idProducto") is None:
            continue
        actualizar_referencia(fraccion["idProducto"], bool(fraccion.get("esGanaderia")), c.get("idCultivo"), c.get("idCampania"))


def guardar_requiere_intervencion(origen: str, id_detalle_compra: int, motivo: str) -> str:
    """Guarda una corrida de una sola fila `Estado='RequiereIntervencion'`,
    sin fracciones de reparto — el `motivo` (`sinOrdenVinculada`/`repartoNoCierra`)
    queda como `Importe=0` con una convención de columna: se reusa `IdCentroCosto`
    como `NULL` y se documenta el motivo fuera de esta tabla (en la respuesta del
    endpoint, calculado on-demand — no hace falta persistir texto libre)."""
    return guardar_corrida(origen, id_detalle_compra, [{"importe": 0.0, "estado": "RequiereIntervencion"}])


def pendientes_intervencion(page: int = 1, page_size: int = 50) -> list[dict]:
    offset = max(page - 1, 0) * page_size
    return fetch_all(
        f"SELECT {_COLUMNAS} FROM dbo.ImputacionPropuestas p "
        "WHERE p.Estado = 'RequiereIntervencion' AND p.IdCorrida = ("
        "SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2 "
        "WHERE p2.IdDetalleCompra = p.IdDetalleCompra ORDER BY p2.FechaCalculo DESC) "
        "ORDER BY p.FechaCalculo DESC "
        "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        (offset, page_size),
    )


def marcar_stock_sin_consumir_aprobada(fracciones: list[dict]) -> list[dict]:
    """La fracción "en stock sin consumir" (`esStock=True`, sin Orden/Lote/Cultivo/
    Campaña) no requiere aprobación del usuario — se guarda directo `Aprobada`
    (FR-002)."""
    ahora = datetime.now(timezone.utc)
    resultado = []
    for f in fracciones:
        if f.get("esStock"):
            resultado.append({**f, "estado": "Aprobada", "fechaAprobacion": ahora})
        else:
            resultado.append(f)
    return resultado


def corrida_vigente(id_detalle_compra: int) -> str | None:
    fila = fetch_one(
        "SELECT TOP 1 IdCorrida FROM dbo.ImputacionPropuestas "
        "WHERE IdDetalleCompra = ? ORDER BY FechaCalculo DESC",
        (id_detalle_compra,),
    )
    return fila["IdCorrida"] if fila else None


def listar_propuestas(
    estado: str | None = None,
    origen: str | None = None,
    id_detalle_compra: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> list[dict]:
    """Lista las fracciones de la corrida vigente de cada renglón (no las corridas viejas)."""
    where = [
        "p.IdCorrida = ("
        "SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2 "
        "WHERE p2.IdDetalleCompra = p.IdDetalleCompra ORDER BY p2.FechaCalculo DESC)"
    ]
    params: list = []
    if estado:
        where.append("p.Estado = ?")
        params.append(estado)
    if origen:
        where.append("p.Origen = ?")
        params.append(origen)
    if id_detalle_compra is not None:
        where.append("p.IdDetalleCompra = ?")
        params.append(id_detalle_compra)

    offset = max(page - 1, 0) * page_size
    return fetch_all(
        f"SELECT {_COLUMNAS} FROM dbo.ImputacionPropuestas p WHERE {' AND '.join(where)} "
        "ORDER BY p.FechaCalculo DESC, p.IdPropuesta "
        "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        (*params, offset, page_size),
    )


def det_compra_producto(id_detalle_compra: int) -> int | None:
    """`IdFormulado` (producto) del renglón de factura, o `None` si no es un insumo."""
    fila = fetch_one("SELECT IdFormulado FROM dbo.Det_Compras WHERE IdDetalleCompra = ?", (id_detalle_compra,))
    return fila["IdFormulado"] if fila else None


def vinculos_remito_para_compra(id_detalle_compra: int) -> list[dict]:
    """Renglones de remito vinculados a este renglón de factura, con la cantidad
    remitida de cada uno (`tblRemitoCompra`, fuente de verdad del vínculo)."""
    return fetch_all(
        "SELECT IdDetalleRemito AS idDetalleRemito, CantidadRemitida AS cantidadRemitida "
        "FROM dbo.tblRemitoCompra WHERE IdDetalleCompra = ?",
        (id_detalle_compra,),
    )


def nombres_cultivos() -> dict[int, str]:
    filas = fetch_all("SELECT IdCultivo AS id, Cultivo AS nombre FROM dbo.Cultivos")
    return {f["id"]: f["nombre"] for f in filas}


def nombres_campanias() -> dict[int, str]:
    filas = fetch_all("SELECT [IdCampaña] AS id, [Campaña] AS nombre FROM dbo.Campañas")
    return {f["id"]: f["nombre"] for f in filas}


def orden_trabajo_info(id_orden_trabajo: int) -> dict | None:
    return fetch_one(
        "SELECT IdOrdenTrabajo AS idOrdenTrabajo, IdRubro AS idRubro, IdCentroCostos AS idCentroCostos, "
        "COALESCE(FechaEjecucion, FechaPedido) AS fecha "
        "FROM dbo.Ordenes_Trabajo WHERE IdOrdenTrabajo = ?",
        (id_orden_trabajo,),
    )


def distribucion_de_orden_insumo(id_orden_insumo: int) -> list[dict]:
    return fetch_all(
        "SELECT IdLote AS idLote, IdCultivo AS idCultivo, IdCampania AS idCampania, "
        "CantidadAsignada AS cantidadAsignada "
        "FROM dbo.Ordenes_Trabajo_Distrib WHERE IdOrdenInsumo = ? AND Aplicar = 1",
        (id_orden_insumo,),
    )


def distribucion_de_orden(id_orden_trabajo: int) -> list[dict]:
    """Superficie por Lote/Cultivo/Campaña de una Orden completa (todos sus
    renglones de insumo), para prorratear el costo de un contratista/maquinaria
    (mismo criterio que `ordenes.costeo`, spec 011)."""
    return fetch_all(
        "SELECT d.IdLote AS idLote, d.IdCultivo AS idCultivo, d.IdCampania AS idCampania, "
        "SUM(d.Superficie) AS superficie "
        "FROM dbo.Ordenes_Trabajo_Distrib d JOIN dbo.Ordenes_Trabajo_Insumos oi ON oi.IdOrdenInsumo = d.IdOrdenInsumo "
        "WHERE oi.IdOrdenTrabajo = ? AND d.Aplicar = 1 "
        "GROUP BY d.IdLote, d.IdCultivo, d.IdCampania",
        (id_orden_trabajo,),
    )


def total_neto_compra(id_compra: int) -> dict | None:
    return fetch_one(
        "SELECT c.Moneda AS moneda, c.[Tipo de Cambio] AS tipoDeCambio, "
        "(SELECT SUM(d.Cantidad * d.[Precio Unitario]) FROM dbo.Det_Compras d WHERE d.IdCompra = c.IdDeuda) AS neto "
        "FROM dbo.Compras c WHERE c.IdDeuda = ?",
        (id_compra,),
    )


def ordenes_vinculadas_a_compra(id_compra: int) -> list[int]:
    """`IdOrdenTrabajo` de todas las Órdenes vinculadas a esta factura de contratista
    (`OrdenesContratistaFacturas`, N a N)."""
    filas = fetch_all("SELECT IdOrdenTrabajo AS idOrdenTrabajo FROM dbo.OrdenesContratistaFacturas WHERE IdCompra = ?", (id_compra,))
    return [f["idOrdenTrabajo"] for f in filas]


def info_remito_de_capa(id_detalle_remito: int) -> dict | None:
    return fetch_one(
        "SELECT r.IdRemito AS idRemito, r.NroRemito AS nroRemito, r.Fecha AS fecha "
        "FROM dbo.Remitos_Detalles rd JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito "
        "WHERE rd.IdDetalleRemito = ?",
        (id_detalle_remito,),
    )


def info_orden_trabajo(id_orden_trabajo: int) -> dict | None:
    return fetch_one(
        "SELECT IdOrdenTrabajo AS idOrdenTrabajo, FechaEjecucion AS fechaEjecucion, "
        "FechaPedido AS fechaPedido, Estado AS estado "
        "FROM dbo.Ordenes_Trabajo WHERE IdOrdenTrabajo = ?",
        (id_orden_trabajo,),
    )


def detalles_compra_con_corrida_por_producto(id_producto: int) -> list[int]:
    """`IdDetalleCompra` de todos los renglones de este producto que ya
    tienen alguna corrida calculada — usado para saber a quién avisar cuando
    cambia un dato fuente (remito/distribución/orden) de ese producto."""
    filas = fetch_all(
        "SELECT DISTINCT p.IdDetalleCompra AS idDetalleCompra "
        "FROM dbo.ImputacionPropuestas p JOIN dbo.Det_Compras dc ON dc.IdDetalleCompra = p.IdDetalleCompra "
        "WHERE dc.IdFormulado = ?",
        (id_producto,),
    )
    return [f["idDetalleCompra"] for f in filas]


def listar_documentos_con_imputacion(
    id_contacto: int | None = None,
    fecha_desde=None,
    fecha_hasta=None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Documentos comerciales (Compras) que ya tienen al menos una propuesta
    del motor — informe/pantalla para la oficina del contador (pedido del
    usuario, 2026-09-25)."""
    where = ["c.IdDeuda IN (SELECT DISTINCT dc.IdCompra FROM dbo.Det_Compras dc "
             "JOIN dbo.ImputacionPropuestas p ON p.IdDetalleCompra = dc.IdDetalleCompra)"]
    params: list = []
    if id_contacto is not None:
        where.append("c.IdContacto = ?")
        params.append(id_contacto)
    if fecha_desde is not None:
        where.append("c.Fecha >= ?")
        params.append(fecha_desde)
    if fecha_hasta is not None:
        where.append("c.Fecha <= ?")
        params.append(fecha_hasta)
    where_sql = "WHERE " + " AND ".join(where)

    total = fetch_one(f"SELECT COUNT(*) AS total FROM dbo.Compras c {where_sql}", tuple(params))["total"]

    offset = max(page - 1, 0) * page_size
    filas = fetch_all(
        f"""
        SELECT c.IdDeuda AS idCompra, c.Fecha AS fecha, c.IdContacto AS idContacto,
               ct.[Razon Social] AS proveedor, c.[Tipo documento] AS tipoDocumento,
               c.[Nro Documento] AS numeroDocumento, c.Moneda AS moneda, c.[Tipo de Cambio] AS tipoDeCambio
        FROM dbo.Compras c
        LEFT JOIN dbo.Contactos ct ON ct.IdContacto = c.IdContacto
        {where_sql}
        ORDER BY c.Fecha DESC, c.IdDeuda DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """,
        (*params, offset, page_size),
    )
    return filas, total


def lineas_con_imputacion(id_compra: int) -> list[dict]:
    """Renglones de un documento comercial con la clasificación manual y las
    fracciones vigentes del motor (con nombres resueltos para el informe)."""
    lineas = fetch_all(
        "SELECT dc.IdDetalleCompra AS idDetalleCompra, dc.[Producto/Servicio] AS producto, "
        "dc.Cantidad AS cantidad, dc.Unidad AS unidad, dc.[Precio Unitario] AS precioUnitario, "
        "dc.IdCampaña AS idCampaniaManual, ca.Campaña AS campaniaManual, "
        "dc.IdCentroCostos AS idCentroCostoManual, cc.[Centro de costos] AS centroCostoManual, "
        "dc.IdRubro AS idRubroManual, r.Rubro AS rubroManual "
        "FROM dbo.Det_Compras dc "
        "LEFT JOIN dbo.Campañas ca ON ca.IdCampaña = dc.IdCampaña "
        "LEFT JOIN dbo.[Centro de costos] cc ON cc.IdCentro = dc.IdCentroCostos "
        "LEFT JOIN dbo.Rubros r ON r.IdRubro = dc.IdRubro "
        "WHERE dc.IdCompra = ? ORDER BY dc.IdDetalleCompra",
        (id_compra,),
    )
    if not lineas:
        return []

    marcas = ",".join("?" for _ in lineas)
    ids = tuple(l["idDetalleCompra"] for l in lineas)
    fracciones = fetch_all(
        f"""
        SELECT p.IdDetalleCompra AS idDetalleCompra, p.IdPropuesta AS idPropuesta, p.Origen AS origen,
               p.IdLote AS idLote, lo.[Numero Lote] AS lote, p.IdCultivo AS idCultivo, cu.Cultivo AS cultivo,
               p.IdCampania AS idCampania, ca.Campaña AS campania, p.IdCentroCosto AS idCentroCosto,
               cc.[Centro de costos] AS centroCosto, p.EsGanaderia AS esGanaderia, p.Importe AS importe,
               p.Estado AS estado
        FROM dbo.ImputacionPropuestas p
        LEFT JOIN dbo.Lotes lo ON lo.IdLote = p.IdLote
        LEFT JOIN dbo.Cultivos cu ON cu.IdCultivo = p.IdCultivo
        LEFT JOIN dbo.Campañas ca ON ca.IdCampaña = p.IdCampania
        LEFT JOIN dbo.[Centro de costos] cc ON cc.IdCentro = p.IdCentroCosto
        WHERE p.IdDetalleCompra IN ({marcas})
          AND p.IdCorrida = (SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2
                              WHERE p2.IdDetalleCompra = p.IdDetalleCompra ORDER BY p2.FechaCalculo DESC)
        ORDER BY p.IdDetalleCompra, p.IdPropuesta
        """,
        ids,
    )
    por_linea: dict[int, list[dict]] = defaultdict(list)
    for f in fracciones:
        por_linea[f["idDetalleCompra"]].append(f)

    for linea in lineas:
        linea["fracciones"] = por_linea.get(linea["idDetalleCompra"], [])
    return lineas


def costo_aprobado_por_campania(id_campania: int) -> dict:
    """Suma `Importe` de fracciones `Aprobada` de esta campaña, y cuenta cuánto
    sigue `Pendiente`/`RequiereIntervencion` (US5, FR-015)."""
    aprobado = fetch_one(
        "SELECT SUM(Importe) AS total FROM dbo.ImputacionPropuestas "
        "WHERE IdCampania = ? AND Estado = 'Aprobada' AND IdCorrida = ("
        "SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2 "
        "WHERE p2.IdDetalleCompra = dbo.ImputacionPropuestas.IdDetalleCompra ORDER BY p2.FechaCalculo DESC)",
        (id_campania,),
    )
    pendiente = fetch_one(
        "SELECT SUM(Importe) AS total FROM dbo.ImputacionPropuestas "
        "WHERE IdCampania = ? AND Estado IN ('Pendiente', 'RequiereIntervencion') AND IdCorrida = ("
        "SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2 "
        "WHERE p2.IdDetalleCompra = dbo.ImputacionPropuestas.IdDetalleCompra ORDER BY p2.FechaCalculo DESC)",
        (id_campania,),
    )
    return {
        "totalAprobado": float((aprobado or {}).get("total") or 0),
        "totalPendiente": float((pendiente or {}).get("total") or 0),
    }


def candidatos_insumo_sin_corrida(limite: int = 2000) -> list[int]:
    """`IdDetalleCompra` de renglones de insumo ya vinculados a un remito
    (`tblRemitoCompra`, dentro de alcance) que todavía no tienen ninguna
    corrida del motor — candidatos para el cálculo masivo."""
    filas = fetch_all(
        f"SELECT DISTINCT TOP {int(limite)} t.IdDetalleCompra AS idDetalleCompra "
        "FROM dbo.tblRemitoCompra t "
        "WHERE NOT EXISTS (SELECT 1 FROM dbo.ImputacionPropuestas p WHERE p.IdDetalleCompra = t.IdDetalleCompra)",
    )
    return [f["idDetalleCompra"] for f in filas]


def candidatos_contratista_sin_corrida(limite: int = 2000) -> list[int]:
    """`IdCompra` de facturas de contratista/maquinaria ya vinculadas a
    alguna Orden (`OrdenesContratistaFacturas`) que todavía no tienen
    ninguna corrida del motor."""
    filas = fetch_all(
        f"SELECT DISTINCT TOP {int(limite)} f.IdCompra AS idCompra "
        "FROM dbo.OrdenesContratistaFacturas f "
        "WHERE NOT EXISTS (SELECT 1 FROM dbo.ImputacionPropuestas p WHERE p.IdDetalleCompra = f.IdCompra AND p.Origen = 'Contratista')",
    )
    return [f["idCompra"] for f in filas]


def obtener_referencia(id_producto: int, es_ganaderia: bool) -> dict | None:
    """Última clasificación aprobada/corregida por el usuario para este producto/destino
    (lado de lectura del aprendizaje simple, FR-008 — el lado de escritura es
    `actualizar_referencia`)."""
    return fetch_one(
        "SELECT IdProducto AS idProducto, EsGanaderia AS esGanaderia, IdCultivo AS idCultivo, "
        "IdCampania AS idCampania, FechaActualizacion AS fechaActualizacion "
        "FROM dbo.ImputacionReferencias WHERE IdProducto = ? AND EsGanaderia = ?",
        (id_producto, 1 if es_ganaderia else 0),
    )
