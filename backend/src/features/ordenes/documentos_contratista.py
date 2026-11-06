"""048: vínculo factura de labor del contratista ↔ órdenes de trabajo.

El vínculo se guarda desde Compras (panel "Órdenes de trabajo"); la orden y el Resultado solo lo leen.
Al guardar, el documento se imputa con el motor 017 (reparto por superficie) y queda aprobado. Las NC/ND
siguen a su factura (relacionadas en "Documentos relacionados").
"""

from __future__ import annotations

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.features.imputacion import motor, repository as imputacion_repository
from src.features.imputacion.repository import RUBROS_FUERA_REPARTO, RUBROS_LABOR

_LABOR_SQL = ",".join("?" * len(RUBROS_LABOR))
_FUERA_SQL = ",".join("?" * len(RUBROS_FUERA_REPARTO))


def _tipo(id_compra: int) -> dict | None:
    return fetch_one(
        "SELECT c.IdDeuda AS idCompra, c.IdContacto AS idContacto, c.[Tipo documento] AS tipo, c.Moneda AS moneda, "
        "c.[Tipo de Cambio] AS tipoDeCambio FROM dbo.Compras c WHERE c.IdDeuda = ?", (id_compra,))


def es_nota_credito_debito(id_compra: int) -> bool:
    c = _tipo(id_compra)
    return bool(c) and (c["tipo"] or "").lower().startswith("nota")


def es_contratista(id_compra: int) -> bool:
    """El contacto de la compra ejecutó alguna orden de trabajo."""
    return fetch_one(
        "SELECT 1 AS si FROM dbo.Compras c WHERE c.IdDeuda = ? AND EXISTS (SELECT 1 FROM dbo.Ordenes_Trabajo o "
        "WHERE o.IdContratistaContacto = c.IdContacto)", (id_compra,)) is not None


# Factura anulada: sus notas de crédito relacionadas cubren todo su neto (ej. Santos 00001-00000053, cebada mal
# facturada, anulada con la NC 00001-00000006 y refacturada como trigo). No lleva orden; queda con imputación manual.
_ANULADA_SQL = """(
    (SELECT ABS(SUM(d.Cantidad * d.[Precio Unitario])) FROM dbo.Det_Compras d
      JOIN dbo.Compras n ON n.IdDeuda = d.IdCompra
      WHERE n.[Tipo documento] COLLATE Latin1_General_CI_AI = 'Nota de Credito'
        AND n.IdDeuda IN (SELECT r.IdCompraRelacionada FROM dbo.CompraDocumentosRelacionados r WHERE r.IdCompra = {c}
                          UNION SELECT r.IdCompra FROM dbo.CompraDocumentosRelacionados r WHERE r.IdCompraRelacionada = {c}))
    >= (SELECT SUM(d.Cantidad * d.[Precio Unitario]) FROM dbo.Det_Compras d WHERE d.IdCompra = {c}) - 0.01)"""


def confirmada_sin_orden(id_compra: int) -> bool:
    """Factura que no tiene orden para asociar, confirmado por el usuario: el costo sale de su imputación manual."""
    return fetch_one("SELECT 1 AS si FROM dbo.OrdenesContratistaSinOrden WHERE IdCompra = ?", (id_compra,)) is not None


def anulada_por_nc(id_compra: int) -> bool:
    return fetch_one(f"SELECT CASE WHEN {_ANULADA_SQL.format(c='?')} THEN 1 ELSE 0 END AS si".replace("?", str(int(id_compra))))["si"] == 1


def es_documento_de_labor(id_compra: int) -> bool:
    """Tiene al menos un renglón de un rubro de labor (FR-002)."""
    return fetch_one(
        "SELECT 1 AS si FROM dbo.Det_Compras d JOIN dbo.Rubros r ON r.IdRubro = d.IdRubro "
        f"WHERE d.IdCompra = ? AND r.Rubro IN ({_LABOR_SQL})", (id_compra, *RUBROS_LABOR)) is not None


def neto_repartible(id_compra: int) -> dict | None:
    """Neto de los renglones que se reparten (todos menos insumos y otros negocios), sin signo."""
    return imputacion_repository.total_neto_compra(id_compra)


def ordenes_del_contratista(id_compra: int) -> list[dict]:
    """Órdenes ejecutadas del contacto de la compra: primero las que no tienen factura, luego de la más nueva
    a la más vieja."""
    c = _tipo(id_compra)
    if not c:
        return []
    filas = fetch_all(
        """
        SELECT o.IdOrdenTrabajo AS idOrden, CONVERT(date, COALESCE(o.FechaEjecucion, o.FechaPedido)) AS fecha,
               CONVERT(date, o.FechaPedido) AS fechaPedido,
               tl.Labor AS labor,
               (SELECT STRING_AGG(l.[Numero Lote], ', ') FROM (SELECT DISTINCT d.IdLote FROM dbo.Ordenes_Trabajo_Distrib d
                  JOIN dbo.Ordenes_Trabajo_Insumos i ON i.IdOrdenInsumo = d.IdOrdenInsumo
                  WHERE i.IdOrdenTrabajo = o.IdOrdenTrabajo AND d.Aplicar = 1) x JOIN dbo.Lotes l ON l.IdLote = x.IdLote) AS lotes,
               (SELECT STRING_AGG(cu.Cultivo, ', ') FROM (SELECT DISTINCT d.IdCultivo FROM dbo.Ordenes_Trabajo_Distrib d
                  JOIN dbo.Ordenes_Trabajo_Insumos i ON i.IdOrdenInsumo = d.IdOrdenInsumo
                  WHERE i.IdOrdenTrabajo = o.IdOrdenTrabajo AND d.Aplicar = 1) z JOIN dbo.Cultivos cu ON cu.IdCultivo = z.IdCultivo) AS cultivos,
               (SELECT SUM(s) FROM (SELECT MAX(d.Superficie) s FROM dbo.Ordenes_Trabajo_Distrib d
                  JOIN dbo.Ordenes_Trabajo_Insumos i ON i.IdOrdenInsumo = d.IdOrdenInsumo
                  WHERE i.IdOrdenTrabajo = o.IdOrdenTrabajo AND d.Aplicar = 1 GROUP BY d.IdLote) y) AS hectareas,
               CASE WHEN EXISTS (SELECT 1 FROM dbo.OrdenesContratistaFacturas f WHERE f.IdOrdenTrabajo = o.IdOrdenTrabajo
                                 AND f.IdCompra = ?) THEN 1 ELSE 0 END AS vinculada,
               CASE WHEN EXISTS (SELECT 1 FROM dbo.OrdenesContratistaFacturas f WHERE f.IdOrdenTrabajo = o.IdOrdenTrabajo
                                 AND f.IdCompra <> ?) THEN 1 ELSE 0 END AS tieneOtraFactura
        FROM dbo.Ordenes_Trabajo o
        LEFT JOIN dbo.[Tipo Labores] tl ON tl.IdLabor = o.IdTipoLabor
        WHERE o.IdContratistaContacto = ? AND o.Estado = 'Ejecutada'
        """, (id_compra, id_compra, c["idContacto"]))
    for f in filas:
        f["vinculada"], f["tieneOtraFactura"] = bool(f["vinculada"]), bool(f["tieneOtraFactura"])
        f["hectareas"] = float(f["hectareas"] or 0)
    # Sergio 06/11: una orden que ya tiene otra factura no es candidata (salvo que también esté en esta).
    filas = [f for f in filas if f["vinculada"] or not f["tieneOtraFactura"]]
    filas.sort(key=lambda f: str(f["fecha"]), reverse=True)
    filas.sort(key=lambda f: f["tieneOtraFactura"] and not f["vinculada"])
    return filas


def datos_factura(id_compra: int) -> dict:
    """Fecha y hectáreas facturadas (renglones de labor en hectáreas o sin unidad), para comparar con las órdenes."""
    f = fetch_one(
        "SELECT CONVERT(date, c.Fecha) AS fecha, "
        "(SELECT SUM(d.Cantidad) FROM dbo.Det_Compras d JOIN dbo.Rubros r ON r.IdRubro = d.IdRubro "
        f" WHERE d.IdCompra = c.IdDeuda AND r.Rubro IN ({_LABOR_SQL}) "
        "  AND (d.Unidad IS NULL OR d.Unidad = '' OR d.Unidad LIKE 'h%')) AS hectareas "
        "FROM dbo.Compras c WHERE c.IdDeuda = ?", (*RUBROS_LABOR, id_compra)) or {}
    return {"fecha": f.get("fecha"), "hectareas": float(f["hectareas"]) if f.get("hectareas") else None}


def _guardar_aprobada(id_compra: int, fracciones: list[dict], usuario: str) -> None:
    if not fracciones:  # retiro: corrida aprobada sin reparto (importe 0, sin orden)
        fracciones = [{"importe": 0.0}]
    id_corrida = imputacion_repository.guardar_corrida("Contratista", id_compra, fracciones)
    imputacion_repository.aprobar_corrida(id_corrida, usuario=usuario)


def recalcular_nota(id_nc: int, usuario: str) -> None:
    """NC/ND: replica las proporciones del reparto vigente de su factura, con su signo; sin factura con
    reparto, retira."""
    fracciones = motor.evaluar_nota_relacionada(id_nc)
    if fracciones or imputacion_repository.reparto_contratista_vigente(id_nc):
        _guardar_aprobada(id_nc, fracciones, usuario)


def notas_relacionadas(id_compra: int) -> list[int]:
    filas = fetch_all(
        "SELECT r.IdCompraRelacionada AS id FROM dbo.CompraDocumentosRelacionados r WHERE r.IdCompra = ? "
        "UNION SELECT r.IdCompra FROM dbo.CompraDocumentosRelacionados r WHERE r.IdCompraRelacionada = ?",
        (id_compra, id_compra))
    return [f["id"] for f in filas if es_nota_credito_debito(f["id"])]


def recalcular(id_compra: int, usuario: str) -> list[dict]:
    """Reimputa la factura según sus vínculos actuales y luego sus NC/ND."""
    if imputacion_repository.ordenes_vinculadas_a_compra(id_compra):
        fracciones, motivo = motor.evaluar_contratista(id_compra)
        if not fracciones:
            raise ValueError([f"No se pudo repartir la factura: {motivo}"])
        _guardar_aprobada(id_compra, fracciones, usuario)
    elif imputacion_repository.reparto_contratista_vigente(id_compra):
        _guardar_aprobada(id_compra, [], usuario)
    for id_nc in notas_relacionadas(id_compra):
        recalcular_nota(id_nc, usuario)
    return reparto(id_compra)


def fijar_vinculos(id_compra: int, ids_orden: list[int], usuario: str) -> list[dict]:
    """Deja vinculadas exactamente `ids_orden` a la factura e imputa (FR-001/FR-004)."""
    c = _tipo(id_compra)
    if c is None:
        raise ValueError(["El documento no existe."])
    if es_nota_credito_debito(id_compra):
        raise ValueError(["Las notas de crédito/débito se imputan como su factura: relacionala en Documentos relacionados."])
    ids = sorted(set(int(i) for i in ids_orden))
    if ids and not es_documento_de_labor(id_compra):
        raise ValueError(["El documento no tiene renglones de labor de contratista."])
    if ids:
        marcas = ",".join("?" * len(ids))
        validas = fetch_all(
            f"SELECT IdOrdenTrabajo AS id FROM dbo.Ordenes_Trabajo WHERE IdOrdenTrabajo IN ({marcas}) "
            "AND IdContratistaContacto = ? AND Estado = 'Ejecutada'", (*ids, c["idContacto"]))
        if len(validas) != len(ids):
            raise ValueError(["Alguna orden no es de este contratista o no está ejecutada."])
    actuales = set(imputacion_repository.ordenes_vinculadas_a_compra(id_compra))
    stmts = [("DELETE FROM dbo.OrdenesContratistaFacturas WHERE IdCompra = ? AND IdOrdenTrabajo = ?", (id_compra, o))
             for o in actuales - set(ids)]
    stmts += [("INSERT INTO dbo.OrdenesContratistaFacturas (IdOrdenTrabajo, IdCompra, UsuarioConfirmacion) VALUES (?, ?, ?)",
               (o, id_compra, usuario)) for o in set(ids) - actuales]
    if stmts:
        execute_write_transaction(stmts)
    try:
        return recalcular(id_compra, usuario)
    except Exception:
        # Todo o nada: si la imputación falla, los vínculos vuelven a como estaban (hallazgo E2E 06/11).
        revertir = [("DELETE FROM dbo.OrdenesContratistaFacturas WHERE IdCompra = ? AND IdOrdenTrabajo = ?", (id_compra, o))
                    for o in set(ids) - actuales]
        revertir += [("INSERT INTO dbo.OrdenesContratistaFacturas (IdOrdenTrabajo, IdCompra, UsuarioConfirmacion) VALUES (?, ?, ?)",
                      (o, id_compra, usuario)) for o in actuales - set(ids)]
        if revertir:
            execute_write_transaction(revertir)
        raise


def facturas_de_orden(id_orden: int) -> list[int]:
    return [f["id"] for f in fetch_all(
        "SELECT IdCompra AS id FROM dbo.OrdenesContratistaFacturas WHERE IdOrdenTrabajo = ?", (id_orden,))]


def quitar_orden(id_orden: int, usuario: str) -> None:
    """Orden anulada: borra sus vínculos y reimputa las facturas afectadas."""
    facturas = facturas_de_orden(id_orden)
    if facturas:
        execute_write_transaction([("DELETE FROM dbo.OrdenesContratistaFacturas WHERE IdOrdenTrabajo = ?", (id_orden,))])
    for id_compra in facturas:
        recalcular(id_compra, usuario)


def reparto(id_compra: int, id_orden: int | None = None) -> list[dict]:
    """Fracciones del reparto vigente (última corrida aprobada de contratista)."""
    id_corrida = imputacion_repository.reparto_contratista_vigente(id_compra)
    if not id_corrida:
        return []
    filtro, params = ("AND p.IdOrdenTrabajo = ?", (id_corrida, id_orden)) if id_orden else ("", (id_corrida,))
    return fetch_all(
        "SELECT p.IdOrdenTrabajo AS idOrden, l.[Numero Lote] AS lote, cu.Cultivo AS cultivo, ca.Campaña AS campania, "
        "p.Importe AS importe FROM dbo.ImputacionPropuestas p "
        "LEFT JOIN dbo.Lotes l ON l.IdLote = p.IdLote LEFT JOIN dbo.Cultivos cu ON cu.IdCultivo = p.IdCultivo "
        "LEFT JOIN dbo.Campañas ca ON ca.IdCampaña = p.IdCampania "
        f"WHERE p.IdCorrida = ? AND p.IdOrdenTrabajo IS NOT NULL {filtro} ORDER BY l.[Numero Lote]", params)


def sin_orden(id_contacto: int | None = None) -> list[dict]:
    """Facturas de labor de contratistas sin orden vinculada, con sus renglones (FR-008)."""
    filtro, params = ("AND c.IdContacto = ?", (id_contacto,)) if id_contacto else ("", ())
    return fetch_all(
        f"""
        SELECT c.IdDeuda AS idCompra, k.[Razon Social] AS contratista, CONVERT(date, c.Fecha) AS fecha,
               c.[Nro Documento] AS numero, c.Moneda AS moneda, ru.Rubro AS rubro, d.[Producto/Servicio] AS concepto,
               d.Cantidad AS cantidad, d.Unidad AS unidad, d.Cantidad * d.[Precio Unitario] AS neto,
               de.Destino AS destino, ca.Campaña AS campania
        FROM dbo.Compras c
        JOIN dbo.Contactos k ON k.IdContacto = c.IdContacto
        JOIN dbo.Det_Compras d ON d.IdCompra = c.IdDeuda
        LEFT JOIN dbo.Rubros ru ON ru.IdRubro = d.IdRubro
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        LEFT JOIN dbo.Campañas ca ON ca.IdCampaña = d.IdCampaña
        WHERE c.[Tipo documento] = 'Factura'
          AND c.IdContacto IN (SELECT IdContratistaContacto FROM dbo.Ordenes_Trabajo WHERE IdContratistaContacto IS NOT NULL)
          AND EXISTS (SELECT 1 FROM dbo.Det_Compras d2 JOIN dbo.Rubros r2 ON r2.IdRubro = d2.IdRubro
                      WHERE d2.IdCompra = c.IdDeuda AND r2.Rubro IN ({_LABOR_SQL}))
          AND NOT EXISTS (SELECT 1 FROM dbo.OrdenesContratistaFacturas f WHERE f.IdCompra = c.IdDeuda)
          AND NOT {_ANULADA_SQL.format(c="c.IdDeuda")}
          AND NOT EXISTS (SELECT 1 FROM dbo.OrdenesContratistaSinOrden s WHERE s.IdCompra = c.IdDeuda)
          {filtro}
        ORDER BY k.[Razon Social], c.Fecha, c.IdDeuda
        """, (*RUBROS_LABOR, *params))
