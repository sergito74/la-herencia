"""Órdenes de Trabajo: catálogos, alta, listado, detalle, edición, ejecución y anulación.

Escribe exclusivamente contra `WC`. Las tablas heredadas (`Ordenes`,
`Ordenes_Detalles`, `Ordenes_Detalles_Distrib`, `Ordenes_Lotes`, `Lotes`,
`Cultivos`, `Campañas`, `Tipo Labores`, `Contactos`) se leen pero no se alteran;
lo nuevo vive en `Ordenes_Trabajo` y sus tablas asociadas. El consumo de stock
reutiliza el costeo FIFO de 010-remitos (`stock_fifo`, `stock_datos`), que ya
lee `Ordenes_Trabajo_Insumos` como fuente de salidas (ver stock_datos.py).
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.db.params import as_sql_datetime
from src.features.ordenes import costeo, distribucion, formulario_retiro
from src.features.remitos.stock_datos import calcular_stock

TOLERANCIA = 0.005
ESTADOS = ("Planificada", "Ejecutada", "Anulada")


class RequiereConfirmacion(Exception):
    """La operación necesita que el usuario la confirme explícitamente (409)."""

    def __init__(self, mensajes: list[str]):
        super().__init__(mensajes)
        self.mensajes = mensajes


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def _d(v):
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    return v.date() if isinstance(v, datetime) else v


def _existencia(id_producto: int) -> float:
    return calcular_stock(id_producto).get(id_producto, {}).get("existencia", 0.0)


# ------------------------------------------------------------------ catálogos

def listar_lotes() -> list[dict]:
    return fetch_all("SELECT IdLote AS idLote, [Numero Lote] AS numeroLote, Superficie AS superficie FROM dbo.Lotes WHERE [Numero Lote] <> 'PRUE' ORDER BY [Numero Lote]")


def listar_cultivos() -> list[dict]:
    return fetch_all("SELECT IdCultivo AS idCultivo, Cultivo AS nombre FROM dbo.Cultivos ORDER BY Cultivo")


def listar_campanias() -> list[dict]:
    return fetch_all("SELECT IdCampaña AS idCampania, Campaña AS nombre FROM dbo.Campañas ORDER BY Campaña DESC")


def listar_tipos_labor() -> list[dict]:
    return fetch_all("SELECT IdLabor AS idTipoLabor, Labor AS nombre FROM dbo.[Tipo Labores] ORDER BY Labor")


def listar_contratistas() -> list[dict]:
    return fetch_all(
        "SELECT IdContacto AS idContratistaContacto, [Razon Social] AS nombre FROM dbo.Contactos WHERE EsContratistaLabores = 1 ORDER BY [Razon Social]"
    )


# ------------------------------------------------------------------ validación de renglones

def _sin_lotes_que_no_requieren_el_insumo(renglones: list[dict]) -> list[dict]:
    """Dosis/ha = 0 en un lote significa que ese Cultivo/Campaña/Lote no
    necesita este insumo — no es un error de carga (pedido del usuario,
    orden 153: un contratista mal cargado no debería obligar a inventar una
    dosis en lotes donde no se aplicó nada). Se descarta antes de validar y
    de guardar, así no quedan renglones ni distribuciones vacías en las
    tablas. Un renglón de insumo que termina sin ningún lote (no se usó en
    ningún lote de la orden) se descarta entero."""
    filtrados = []
    for r in renglones:
        distribuciones = [d for d in r["distribuciones"] if float(d["dosisHa"]) > 0]
        if distribuciones:
            filtrados.append({**r, "distribuciones": distribuciones})
    return filtrados


def _validar_renglones(renglones: list[dict]) -> dict[int, float]:
    """Valida cada renglón (dosis/superficie > 0, al menos una distribución
    aplicada) y devuelve el consumo total por producto, en la unidad cargada.
    Asume que `renglones` ya pasó por `_sin_lotes_que_no_requieren_el_insumo`."""
    if not renglones:
        raise ValueError(["La orden necesita al menos un renglón de insumo con al menos un lote que lo requiera."])
    consumo_por_producto: dict[int, float] = {}
    for i, r in enumerate(renglones, start=1):
        if not r.get("distribuciones"):
            raise ValueError([f"Renglón {i}: agregá al menos un lote."])
        if not any(d.get("aplicar", True) for d in r["distribuciones"]):
            raise ValueError([f"Renglón {i}: al menos un lote debe estar marcado para aplicar."])
        for j, d in enumerate(r["distribuciones"], start=1):
            if d["superficie"] <= 0:
                raise ValueError([f"Renglón {i}, lote {j}: la superficie debe ser mayor a cero."])
        total = distribucion.calcular_cantidad_total(r["distribuciones"])
        distribucion.validar_cierre(total, r["distribuciones"])
        consumo_por_producto[r["idProducto"]] = consumo_por_producto.get(r["idProducto"], 0.0) + total
    return consumo_por_producto


# ------------------------------------------------------------------ alta

def crear_orden(datos: dict, confirmar: bool = False) -> dict:
    datos = {**datos, "renglones": _sin_lotes_que_no_requieren_el_insumo(datos["renglones"])}
    sin_cultivo = datos.get("idRubro") is not None or datos.get("idCentroCostos") is not None
    consumo = _validar_renglones(datos["renglones"])

    negativos = []
    for pid, total in consumo.items():
        existencia = _existencia(pid)
        if existencia - total < -TOLERANCIA:
            negativos.append(f"Producto {pid}: hay {existencia:g} y la orden retira {total:g}: el stock quedaría negativo.")
    if negativos and not confirmar:
        raise RequiereConfirmacion(negativos)

    def cab(_r: list) -> tuple:
        return (
            "INSERT INTO dbo.Ordenes_Trabajo (FechaPedido, IdTipoLabor, IdContratistaContacto, Estado, IdRubro, IdCentroCostos, Observaciones) "
            "OUTPUT INSERTED.IdOrdenTrabajo VALUES (?, ?, ?, 'Planificada', ?, ?, ?)",
            (
                as_sql_datetime(datos["fecha"]),
                datos["idTipoLabor"],
                datos.get("idContratistaContacto"),
                datos.get("idRubro") if sin_cultivo else None,
                datos.get("idCentroCostos") if sin_cultivo else None,
                datos.get("observaciones") or None,
            ),
        )

    statements: list = [cab]
    for r in datos["renglones"]:
        total = distribucion.calcular_cantidad_total(r["distribuciones"])

        def linea(res: list, r=r, total=total) -> tuple:
            return (
                "INSERT INTO dbo.Ordenes_Trabajo_Insumos (IdOrdenTrabajo, IdProducto, CantidadTotal, Unidad) "
                "OUTPUT INSERTED.IdOrdenInsumo VALUES (?, ?, ?, ?)",
                (res[0], r["idProducto"], total, r["unidad"]),
            )

        idx_insumo = len(statements)
        statements.append(linea)
        for d in r["distribuciones"]:
            cantidad_asignada = round(float(d["dosisHa"]) * float(d["superficie"]), 4)

            def dist(res: list, d=d, cantidad_asignada=cantidad_asignada, idx_insumo=idx_insumo) -> tuple:
                return (
                    "INSERT INTO dbo.Ordenes_Trabajo_Distrib (IdOrdenInsumo, IdLote, IdCultivo, IdCampania, DosisHa, Superficie, CantidadAsignada, Aplicar) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (res[idx_insumo], d["idLote"], d["idCultivo"], d["idCampania"], d["dosisHa"], d["superficie"], cantidad_asignada, 1 if d.get("aplicar", True) else 0),
                )

            statements.append(dist)

    statements.append(formulario_retiro.stmt_generar(0))
    resultados = execute_write_transaction(statements)
    return {"idOrden": resultados[0], "idFormularioRetiro": resultados[-1]}


# ------------------------------------------------------------------ listado y detalle

def listar_ordenes(
    idContratista: int | None = None,
    idLote: int | None = None,
    idCultivo: int | None = None,
    idCampania: int | None = None,
    fechaDesde=None,
    fechaHasta=None,
    estado: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    where, params = ["1 = 1"], []
    if idContratista is not None:
        where.append("o.IdContratistaContacto = ?")
        params.append(idContratista)
    if fechaDesde is not None:
        where.append("o.FechaPedido >= ?")
        params.append(as_sql_datetime(fechaDesde))
    if fechaHasta is not None:
        where.append("o.FechaPedido <= ?")
        params.append(as_sql_datetime(fechaHasta))
    if estado:
        where.append("o.Estado = ?")
        params.append(estado)
    if idLote is not None or idCultivo is not None or idCampania is not None:
        sub = ["1 = 1"]
        if idLote is not None:
            sub.append("d.IdLote = ?")
            params.append(idLote)
        if idCultivo is not None:
            sub.append("d.IdCultivo = ?")
            params.append(idCultivo)
        if idCampania is not None:
            sub.append("d.IdCampania = ?")
            params.append(idCampania)
        where.append(
            f"EXISTS (SELECT 1 FROM dbo.Ordenes_Trabajo_Distrib d JOIN dbo.Ordenes_Trabajo_Insumos i ON i.IdOrdenInsumo = d.IdOrdenInsumo "
            f"WHERE i.IdOrdenTrabajo = o.IdOrdenTrabajo AND {' AND '.join(sub)})"
        )
    filas = fetch_all(
        f"""
        SELECT o.IdOrdenTrabajo AS idOrden, o.FechaPedido AS fechaPedido, o.FechaEjecucion AS fechaEjecucion,
               o.IdTipoLabor AS idTipoLabor, tl.Labor AS tipoLabor, o.IdContratistaContacto AS idContratistaContacto,
               c.[Razon Social] AS contratista, o.Estado AS estado, o.IdRubro AS idRubro, o.IdCentroCostos AS idCentroCostos
        FROM dbo.Ordenes_Trabajo o
        LEFT JOIN dbo.[Tipo Labores] tl ON tl.IdLabor = o.IdTipoLabor
        LEFT JOIN dbo.Contactos c ON c.IdContacto = o.IdContratistaContacto
        WHERE {' AND '.join(where)}
        ORDER BY o.FechaPedido DESC, o.IdOrdenTrabajo DESC
        """,
        tuple(params),
    )
    items = [{**f, "fechaPedido": _d(f["fechaPedido"]), "fechaEjecucion": _d(f["fechaEjecucion"])} for f in filas]
    inicio = (page - 1) * page_size
    return {"items": items[inicio : inicio + page_size], "total": len(items), "page": page, "pageSize": page_size}


def obtener_orden(id_orden: int) -> dict | None:
    cab = fetch_one(
        """
        SELECT o.IdOrdenTrabajo AS idOrden, o.FechaPedido AS fechaPedido, o.FechaEjecucion AS fechaEjecucion,
               o.IdTipoLabor AS idTipoLabor, tl.Labor AS tipoLabor, o.IdContratistaContacto AS idContratistaContacto,
               c.[Razon Social] AS contratista, o.Estado AS estado, o.MotivoAnulacion AS motivoAnulacion,
               o.IdRubro AS idRubro, o.IdCentroCostos AS idCentroCostos, o.Observaciones AS observaciones
        FROM dbo.Ordenes_Trabajo o
        LEFT JOIN dbo.[Tipo Labores] tl ON tl.IdLabor = o.IdTipoLabor
        LEFT JOIN dbo.Contactos c ON c.IdContacto = o.IdContratistaContacto
        WHERE o.IdOrdenTrabajo = ?
        """,
        (id_orden,),
    )
    if cab is None:
        return None
    insumos = fetch_all(
        "SELECT oi.IdOrdenInsumo AS idOrdenInsumo, oi.IdProducto AS idProducto, p.Producto AS producto, oi.CantidadTotal AS cantidadTotal, oi.Unidad AS unidad "
        "FROM dbo.Ordenes_Trabajo_Insumos oi LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = oi.IdProducto WHERE oi.IdOrdenTrabajo = ? ORDER BY oi.IdOrdenInsumo",
        (id_orden,),
    )
    for r in insumos:
        r["cantidadTotal"] = _f(r["cantidadTotal"])
        r["distribuciones"] = fetch_all(
            "SELECT d.IdDistrib AS idDistrib, d.IdLote AS idLote, l.[Numero Lote] AS lote, d.IdCultivo AS idCultivo, cu.Cultivo AS cultivo, "
            "d.IdCampania AS idCampania, ca.Campaña AS campania, d.DosisHa AS dosisHa, d.Superficie AS superficie, d.CantidadAsignada AS cantidadAsignada, d.Aplicar AS aplicar "
            "FROM dbo.Ordenes_Trabajo_Distrib d "
            "LEFT JOIN dbo.Lotes l ON l.IdLote = d.IdLote LEFT JOIN dbo.Cultivos cu ON cu.IdCultivo = d.IdCultivo LEFT JOIN dbo.Campañas ca ON ca.IdCampaña = d.IdCampania "
            "WHERE d.IdOrdenInsumo = ? ORDER BY d.IdDistrib",
            (r["idOrdenInsumo"],),
        )
        for d in r["distribuciones"]:
            d["dosisHa"] = _f(d["dosisHa"])
            d["superficie"] = _f(d["superficie"])
            d["cantidadAsignada"] = _f(d["cantidadAsignada"])
            d["aplicar"] = bool(d["aplicar"])
        r["devoluciones"] = fetch_all(
            "SELECT IdDevolucion AS idDevolucion, Fecha AS fecha, Cantidad AS cantidad, Observaciones AS observaciones "
            "FROM dbo.Ordenes_Trabajo_Devoluciones WHERE IdOrdenInsumo = ? ORDER BY IdDevolucion",
            (r["idOrdenInsumo"],),
        )
        for dv in r["devoluciones"]:
            dv["fecha"] = _d(dv["fecha"])
            dv["cantidad"] = _f(dv["cantidad"])
    maquinaria = fetch_all(
        "SELECT IdOrdenMaquinaria AS idOrdenMaquinaria, Descripcion AS descripcion, CostoPorHectarea AS costoPorHectarea, TipoCambioBna AS tipoCambioBna "
        "FROM dbo.Ordenes_Trabajo_Maquinaria WHERE IdOrdenTrabajo = ?",
        (id_orden,),
    )
    factura = fetch_one(
        "SELECT f.IdCompra AS idCompra, c.[Tipo documento] AS tipoDocumento, c.[Nro Documento] AS numeroDocumento, c.Moneda AS moneda, c.[Tipo de Cambio] AS tipoDeCambio "
        "FROM dbo.Ordenes_Trabajo_Contratista_Factura f JOIN dbo.Compras c ON c.IdDeuda = f.IdCompra WHERE f.IdOrdenTrabajo = ?",
        (id_orden,),
    )
    return {
        **cab,
        "fechaPedido": _d(cab["fechaPedido"]),
        "fechaEjecucion": _d(cab["fechaEjecucion"]),
        "insumos": insumos,
        "maquinaria": maquinaria,
        "facturaContratista": factura,
        "formularioRetiro": formulario_retiro.obtener(id_orden),
        "tieneDevoluciones": any(r["devoluciones"] for r in insumos),
        "editable": cab["estado"] == "Planificada" and not any(r["devoluciones"] for r in insumos) and factura is None,
    }


# ------------------------------------------------------------------ edición

def editar_orden(id_orden: int, datos: dict, confirmar: bool = False) -> None:
    actual = obtener_orden(id_orden)
    if actual is None:
        raise ValueError([f"La orden {id_orden} no existe."])
    if not actual["editable"]:
        raise ValueError(["La orden no se puede editar: ya tiene devoluciones, factura de contratista vinculada, o no está Planificada. Anulala con un motivo para corregirla."])

    datos = {**datos, "renglones": _sin_lotes_que_no_requieren_el_insumo(datos["renglones"])}
    sin_cultivo = datos.get("idRubro") is not None or datos.get("idCentroCostos") is not None
    consumo = _validar_renglones(datos["renglones"])
    negativos = []
    for pid, total in consumo.items():
        existencia_actual_orden = sum(
            r["cantidadTotal"] for r in actual["insumos"] if r["idProducto"] == pid
        )
        existencia = _existencia(pid) + existencia_actual_orden
        if existencia - total < -TOLERANCIA:
            negativos.append(f"Producto {pid}: hay {existencia:g} (liberando lo que ya usaba esta orden) y la orden retira {total:g}.")
    if negativos and not confirmar:
        raise RequiereConfirmacion(negativos)

    ids_insumos = [r["idOrdenInsumo"] for r in actual["insumos"]]
    stmts: list = []
    for idi in ids_insumos:
        stmts.append(("DELETE FROM dbo.Ordenes_Trabajo_Distrib WHERE IdOrdenInsumo = ?", (idi,)))
    if ids_insumos:
        marcas = ",".join("?" for _ in ids_insumos)
        stmts.append((f"DELETE FROM dbo.Ordenes_Trabajo_Insumos WHERE IdOrdenInsumo IN ({marcas})", tuple(ids_insumos)))
    stmts.append((
        "UPDATE dbo.Ordenes_Trabajo SET FechaPedido = ?, IdTipoLabor = ?, IdContratistaContacto = ?, IdRubro = ?, IdCentroCostos = ?, Observaciones = ? WHERE IdOrdenTrabajo = ?",
        (
            as_sql_datetime(datos["fecha"]), datos["idTipoLabor"], datos.get("idContratistaContacto"),
            datos.get("idRubro") if sin_cultivo else None, datos.get("idCentroCostos") if sin_cultivo else None,
            datos.get("observaciones") or None, id_orden,
        ),
    ))
    for r in datos["renglones"]:
        total = distribucion.calcular_cantidad_total(r["distribuciones"])

        def linea(res: list, r=r, total=total) -> tuple:
            return (
                "INSERT INTO dbo.Ordenes_Trabajo_Insumos (IdOrdenTrabajo, IdProducto, CantidadTotal, Unidad) OUTPUT INSERTED.IdOrdenInsumo VALUES (?, ?, ?, ?)",
                (id_orden, r["idProducto"], total, r["unidad"]),
            )

        idx_insumo = len(stmts)
        stmts.append(linea)
        for d in r["distribuciones"]:
            cantidad_asignada = round(float(d["dosisHa"]) * float(d["superficie"]), 4)

            def dist(res: list, d=d, cantidad_asignada=cantidad_asignada, idx_insumo=idx_insumo) -> tuple:
                return (
                    "INSERT INTO dbo.Ordenes_Trabajo_Distrib (IdOrdenInsumo, IdLote, IdCultivo, IdCampania, DosisHa, Superficie, CantidadAsignada, Aplicar) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (res[idx_insumo], d["idLote"], d["idCultivo"], d["idCampania"], d["dosisHa"], d["superficie"], cantidad_asignada, 1 if d.get("aplicar", True) else 0),
                )

            stmts.append(dist)
    execute_write_transaction(stmts)


# ------------------------------------------------------------------ transiciones de estado

def ejecutar_orden(id_orden: int, fecha_ejecucion) -> None:
    actual = obtener_orden(id_orden)
    if actual is None:
        raise ValueError([f"La orden {id_orden} no existe."])
    if actual["estado"] != "Planificada":
        raise ValueError([f"Solo se puede ejecutar una orden Planificada (está {actual['estado']})."])
    execute_write_transaction([
        ("UPDATE dbo.Ordenes_Trabajo SET Estado = 'Ejecutada', FechaEjecucion = ? WHERE IdOrdenTrabajo = ?", (as_sql_datetime(fecha_ejecucion), id_orden)),
    ])


def anular_orden(id_orden: int, motivo: str) -> None:
    if not (motivo or "").strip():
        raise ValueError(["Indicá el motivo de la anulación."])
    actual = obtener_orden(id_orden)
    if actual is None:
        raise ValueError([f"La orden {id_orden} no existe."])
    if actual["estado"] == "Anulada":
        raise ValueError(["La orden ya está anulada."])
    # Anular pone Estado='Anulada': calcular_stock excluye las órdenes anuladas de
    # sus salidas (WHERE ot.Estado <> 'Anulada' en stock_datos.py), así que las
    # capas FIFO que había consumido quedan libres de inmediato — se recalcula
    # desde los datos, no hace falta revertir nada campo por campo. Pero una
    # devolución ya registrada reingresó stock como un `Stock_Ajustes` aparte
    # (registrar_devolucion), que NO está atado al estado de la orden: si no se
    # anula también ese ajuste, anular la orden devolvería el total consumido
    # Y dejaría vigente lo ya devuelto, duplicando el reingreso (hallazgo de
    # `/speckit-implement` T066, verificado con un caso real).
    execute_write_transaction([
        ("UPDATE dbo.Ordenes_Trabajo SET Estado = 'Anulada', MotivoAnulacion = ? WHERE IdOrdenTrabajo = ?", (motivo.strip(), id_orden)),
        (
            "UPDATE dbo.Stock_Ajustes SET Anulado = 1, MotivoAnulacion = ? WHERE Motivo = ? AND ISNULL(Anulado, 0) = 0",
            (f"Orden de trabajo {id_orden} anulada: {motivo.strip()}", f"Devolución de orden de trabajo {id_orden}"),
        ),
    ])


# ------------------------------------------------------------------ devoluciones (Historia 2)

def _renglon_insumo(id_orden_insumo: int) -> dict | None:
    fila = fetch_one(
        "SELECT IdOrdenInsumo AS idOrdenInsumo, IdOrdenTrabajo AS idOrdenTrabajo, IdProducto AS idProducto, CantidadTotal AS cantidadTotal "
        "FROM dbo.Ordenes_Trabajo_Insumos WHERE IdOrdenInsumo = ?",
        (id_orden_insumo,),
    )
    if fila is None:
        return None
    fila["cantidadTotal"] = _f(fila["cantidadTotal"])
    devuelto = fetch_one("SELECT SUM(Cantidad) AS s FROM dbo.Ordenes_Trabajo_Devoluciones WHERE IdOrdenInsumo = ?", (id_orden_insumo,))
    fila["devuelto"] = _f(devuelto["s"] if devuelto else 0)
    return fila


def registrar_devolucion(id_orden_insumo: int, datos: dict) -> int:
    renglon = _renglon_insumo(id_orden_insumo)
    if renglon is None:
        raise ValueError([f"El renglón {id_orden_insumo} no existe."])
    if datos["cantidad"] <= 0:
        raise ValueError(["La cantidad a devolver debe ser mayor a cero."])
    if datos["cantidad"] > renglon["cantidadTotal"] - renglon["devuelto"] + TOLERANCIA:
        raise ValueError([f"No se puede devolver más de lo retirado y no devuelto ({renglon['cantidadTotal'] - renglon['devuelto']:g})."])

    def linea(_r: list) -> tuple:
        return (
            "INSERT INTO dbo.Ordenes_Trabajo_Devoluciones (IdOrdenInsumo, Fecha, Cantidad, Observaciones) OUTPUT INSERTED.IdDevolucion VALUES (?, ?, ?, ?)",
            (id_orden_insumo, as_sql_datetime(datos["fecha"]), datos["cantidad"], datos.get("observaciones") or None),
        )

    # La devolución reingresa al stock como una entrada nueva (una capa FIFO más,
    # con el mismo costo que la última capa conocida del producto — mismo criterio
    # heredado que un sobrante de ajuste en Remitos, stock_datos.py línea ~181), y
    # reduce el consumo efectivo de la orden: `calcular_stock` ya lee
    # `CantidadTotal` de `Ordenes_Trabajo_Insumos` como la salida bruta, así que la
    # devolución debe entrar como una capa de remito-equivalente para que el saldo
    # neto sea correcto. Se modela como un ajuste de stock con motivo "Devolución
    # orden N", reutilizando `Stock_Ajustes` (ya soportado por stock_datos.py).
    def ajuste(_r: list) -> tuple:
        return (
            "INSERT INTO dbo.Stock_Ajustes (Fecha, IdProducto, Cantidad, CostoUnitario, Motivo) VALUES (?, ?, ?, NULL, ?)",
            (as_sql_datetime(datos["fecha"]), renglon["idProducto"], datos["cantidad"], f"Devolución de orden de trabajo {renglon['idOrdenTrabajo']}"),
        )

    resultados = execute_write_transaction([linea, ajuste])
    return resultados[0]


# ------------------------------------------------------------------ maquinaria propia (Historia 3)

def agregar_maquinaria(id_orden: int, datos: dict) -> dict:
    orden = obtener_orden(id_orden)
    if orden is None:
        raise ValueError([f"La orden {id_orden} no existe."])
    if not datos.get("descripcion", "").strip():
        raise ValueError(["Indicá qué máquina se usó."])
    if datos["costoPorHectarea"] <= 0:
        raise ValueError(["El costo por hectárea debe ser mayor a cero."])
    distribuciones = [d for r in orden["insumos"] for d in r["distribuciones"]]
    resultado_costeo = costeo.costo_maquinaria(datos["costoPorHectarea"], distribuciones)

    def linea(_r: list) -> tuple:
        return (
            "INSERT INTO dbo.Ordenes_Trabajo_Maquinaria (IdOrdenTrabajo, Descripcion, CostoPorHectarea, TipoCambioBna) OUTPUT INSERTED.IdOrdenMaquinaria VALUES (?, ?, ?, ?)",
            (id_orden, datos["descripcion"].strip(), datos["costoPorHectarea"], datos.get("tipoCambioBna")),
        )

    resultados = execute_write_transaction([linea])
    return {"idOrdenMaquinaria": resultados[0], **resultado_costeo}


# ------------------------------------------------------------------ factura de contratista (Historia 4)

def vincular_factura_contratista(id_orden: int, id_compra: int) -> dict:
    orden = obtener_orden(id_orden)
    if orden is None:
        raise ValueError([f"La orden {id_orden} no existe."])
    if orden["facturaContratista"] is not None:
        raise ValueError(["La orden ya tiene una factura de contratista vinculada."])
    distribuciones = [d for r in orden["insumos"] for d in r["distribuciones"]]
    resultado_costeo = costeo.costo_contratista(id_compra, distribuciones)
    execute_write_transaction([
        ("INSERT INTO dbo.Ordenes_Trabajo_Contratista_Factura (IdOrdenTrabajo, IdCompra) VALUES (?, ?)", (id_orden, id_compra)),
    ])
    return resultado_costeo


# ------------------------------------------------------------------ catálogo de labores (Historia 7)

def crear_tipo_labor(nombre: str) -> int:
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError(["Indicá el nombre de la labor."])
    if fetch_one("SELECT 1 AS x FROM dbo.[Tipo Labores] WHERE Labor = ?", (nombre,)):
        raise ValueError([f"Ya existe el tipo de labor «{nombre}»."])
    resultados = execute_write_transaction([
        ("INSERT INTO dbo.[Tipo Labores] (Labor) OUTPUT INSERTED.IdLabor VALUES (?)", (nombre,)),
    ])
    return resultados[0]
