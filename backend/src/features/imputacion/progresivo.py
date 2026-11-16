"""Imputación progresiva de los renglones en alcance (050 US9: T022–T025).

- Insumo de stock: la corrida reparte el renglón entre los usos de las órdenes (FIFO) y lo que sigue en
  stock. Se aprueba sola si usos + stock = total del renglón (precio al TC + flete) al centavo y no hay
  dudas; si no, queda Pendiente con motivo (T023). Cada fracción lleva su parte de la estructura (T022).
- Silobolsa / insumos productivos: el uso no queda en las órdenes (Sergio 14/11), así que no pasan por acá:
  el tamiz los deja "Para revisar" y Sergio indica el uso; con eso quedan como renglón de una sola vez.
- Renglón de una sola vez aprobado por el tamiz: una fracción 'Directo' con su destino (T025).

Lo ya imputado no se toca: solo actúa sobre renglones con tamiz vigente (= en alcance).
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.db.connection import fetch_all, fetch_one
from src.features.imputacion import motor, repository
from src.features.remitos import capas_factura

PARTE_COMERCIALIZACION = 9
CULTIVOS_FORRAJEROS = {7, 9}  # Pastura, Avena
_CENT = 0.005
PRECISION_BASE = 5e-6  # error relativo máximo por la precisión de las cantidades guardadas (7 dígitos)


def _tamiz(id_detalle: int) -> dict | None:
    return fetch_one(
        """
        SELECT tz.Destino AS destino, tz.IdParte AS idParte, tz.IdCultivo AS idCultivo, tz.IdCampania AS idCampania,
               tz.Estado AS estado, tr.ReglaDepende AS regla, ISNULL(d.Cantidad, 0) AS cantidad,
               ISNULL(d.[Precio Unitario], 0) AS precio, c.Moneda AS moneda, c.[Tipo de Cambio] AS tc,
               c.[Tipo documento] AS tipoDocumento, d.Unidad AS unidad
        FROM dbo.TamizRenglones tz
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.TamizRubroDestino tr ON tr.IdRubro = d.IdRubro
        WHERE tz.IdDetalleCompra = ? AND tz.Vigente = 1
        """,
        (id_detalle,),
    )


def total_renglon(t: dict, flete: float) -> float:
    unitario = capas_factura.costo_unitario_factura(t, 0.0)
    return round(float(t["cantidad"]) * unitario + flete, 2)


def asignar_partes(fracciones: list[dict], id_parte: int | None, por_uso: bool, id_centro_ganaderia: int | None) -> tuple[list[dict], str | None]:
    """Pura. Pone la parte en cada fracción; con `por_uso` (silobolsa) resuelve el destino según la orden."""
    out, motivo = [], None
    for f in fracciones:
        f = dict(f)
        if f.get("esStock"):
            out.append(f)
            continue
        if not por_uso:
            f["idParte"] = id_parte
        elif f.get("idCultivo") in CULTIVOS_FORRAJEROS:
            f["idParte"] = None
        elif f.get("idCultivo"):
            f["idParte"] = PARTE_COMERCIALIZACION
        elif f.get("esGanaderia") or (id_centro_ganaderia and f.get("idCentroCosto") == id_centro_ganaderia):
            f["esGanaderia"] = True
        else:
            motivo = "Insumo productivo usado sin cultivo ni centro: ¿para qué se usó?"
        out.append(f)
    return out, motivo


def decidir_estado(fracciones: list[dict], total: float, motivo: str | None) -> tuple[list[dict], str | None]:
    """Pura (T023): todo Aprobada si cierra al centavo y no hay motivo de duda."""
    suma = round(sum(float(f["importe"]) for f in fracciones), 2)
    # Precisión de la base (16/11/2026): las cantidades se guardan con 7 dígitos (tipo real), así el costo por unidad
    # del remito difiere en millonésimas del precio de la factura (Lambda 451193: 15-21 centavos sobre $ 70-100 mil).
    # Esa diferencia no es real: va a la fracción más grande para que el renglón cierre al centavo.
    diferencia = round(total - suma, 2)
    if fracciones and _CENT < abs(diferencia) <= max(abs(total) * PRECISION_BASE, _CENT):
        fracciones = [dict(f) for f in fracciones]
        mayor = max(fracciones, key=lambda f: abs(float(f["importe"])))
        mayor["importe"] = round(float(mayor["importe"]) + diferencia, 2)
        suma = round(sum(float(f["importe"]) for f in fracciones), 2)
    if motivo is None and abs(suma - total) > _CENT:
        motivo = f"Usos + stock ({suma:,.2f}) no igualan el total del renglón ({total:,.2f})"
    if motivo is None:
        ahora = datetime.now(timezone.utc)
        return [{**f, "estado": "Aprobada", "fechaAprobacion": ahora} for f in fracciones], None
    return repository.marcar_stock_sin_consumir_aprobada(fracciones), motivo


def _misma_corrida(id_detalle: int, fracciones: list[dict], origen: str) -> bool:
    vigente = repository.corrida_vigente(id_detalle, origen)
    if vigente is None:
        return False
    previas = repository.fracciones_de_corrida(vigente)
    clave = lambda f: (f.get("idOrdenTrabajo"), f.get("idLote"), f.get("idCultivo"), f.get("idCampania"),
                       f.get("idCentroCosto"), round(float(f.get("importe") or 0), 2))
    return sorted(map(clave, previas)) == sorted(map(clave, fracciones))


def imputar_insumo(id_detalle: int) -> dict:
    t = _tamiz(id_detalle)
    if t is None or t["destino"] != "CultivoStock" or t["estado"] != "Aprobada":
        return {"accion": "fueraDeAlcance"}
    if (t.get("tipoDocumento") or "").startswith("Nota"):
        # NC / ND de insumos: sigue el reparto de su factura base (050, 16/11/2026).
        total = total_renglon(t, 0.0)
        if (t.get("tipoDocumento") or "").startswith("Nota de Cr") and total > 0:
            total = -total
        fracciones, motivo = motor.evaluar_nota_insumo(id_detalle, total)
        if not fracciones:
            return {"accion": "pendiente", "idCorrida": repository.guardar_requiere_intervencion("Insumo", id_detalle, motivo), "motivo": motivo}
        fracciones, motivo = decidir_estado(fracciones, round(total, 2), None)
        if _misma_corrida(id_detalle, fracciones, "Insumo"):
            return {"accion": "sinCambios"}
        id_corrida = repository.guardar_corrida("Insumo", id_detalle, fracciones)
        return {"accion": "aprobada" if motivo is None else "pendiente", "idCorrida": id_corrida, "motivo": motivo}
    fracciones = motor.calcular_propuesta_insumo(id_detalle)
    if not fracciones:
        return {"accion": "sinCapa"}
    fracciones, motivo = asignar_partes(fracciones, t["idParte"], False, motor._id_centro_ganaderia())
    if motivo is None and posible_duplicado(id_detalle):
        motivo = "Posible duplicado: hay un remito sin vincular del mismo proveedor y producto"
    total = total_renglon(t, capas_factura.flete_por_renglon().get(id_detalle, 0.0))
    fracciones, motivo = decidir_estado(fracciones, total, motivo)
    if _misma_corrida(id_detalle, fracciones, "Insumo"):
        return {"accion": "sinCambios"}
    id_corrida = repository.guardar_corrida("Insumo", id_detalle, fracciones)
    return {"accion": "aprobada" if motivo is None else "pendiente", "idCorrida": id_corrida, "motivo": motivo}


def fracciones_directo(t: dict, total: float, id_centro_adm: int | None) -> list[dict]:
    """Pura (T025): la fracción única de un renglón de una sola vez."""
    base = {"importe": total, "idParte": t.get("idParte"), "estado": "Aprobada",
            "fechaAprobacion": datetime.now(timezone.utc)}
    if t["destino"] == "Cultivo":
        return [{**base, "idCultivo": t["idCultivo"], "idCampania": t["idCampania"]}]
    if t["destino"] == "Ganaderia":
        return [{**base, "esGanaderia": True}]
    if t["destino"] == "Estructura":
        return [{**base, "idCentroCosto": id_centro_adm}]
    return []  # Financiero / NoImputa: no van a costo de cultivo


def calcular_directo(id_detalle: int) -> dict:
    t = _tamiz(id_detalle)
    if t is None or t["estado"] != "Aprobada" or t["destino"] in ("CultivoStock", "Depende", None):
        return {"accion": "fueraDeAlcance"}
    fracciones = fracciones_directo(t, total_renglon(t, 0.0), motor._id_centro_adm_general())
    if not fracciones or _misma_corrida(id_detalle, fracciones, "Directo"):
        return {"accion": "sinCambios"}
    return {"accion": "aprobada", "idCorrida": repository.guardar_corrida("Directo", id_detalle, fracciones)}


def imputar_renglon(id_detalle: int) -> dict:
    t = _tamiz(id_detalle)
    if t is None:
        return {"accion": "fueraDeAlcance"}
    return imputar_insumo(id_detalle) if t["destino"] == "CultivoStock" else calcular_directo(id_detalle)


def detalles_en_alcance_por_producto(id_producto: int) -> list[int]:
    """Renglones de stock en alcance de un producto (T024: los recalcula la orden aunque no tengan corrida)."""
    return [f["id"] for f in fetch_all(
        "SELECT tz.IdDetalleCompra AS id FROM dbo.TamizRenglones tz JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra "
        "WHERE tz.Vigente = 1 AND tz.Destino = 'CultivoStock' AND tz.Estado = 'Aprobada' AND d.IdFormulado = ?",
        (id_producto,),
    )]


def posible_duplicado(id_detalle: int) -> bool:
    """R-03: la capa de la factura convive con un remito sin vincular del mismo proveedor y producto."""
    return fetch_one(
        """
        SELECT TOP 1 1 AS x FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.Remitos r ON r.IdProveedor = c.IdContacto
        JOIN dbo.Remitos_Detalles rd ON rd.IdRemito = r.IdRemito AND rd.IdFormulado = d.IdFormulado
        LEFT JOIN dbo.Remitos_Extra x ON x.IdRemito = r.IdRemito
        WHERE d.IdDetalleCompra = ? AND ISNULL(x.Anulado, 0) = 0
          AND NOT EXISTS (SELECT 1 FROM dbo.tblRemitoCompra t WHERE t.IdDetalleCompra = d.IdDetalleCompra)
          AND NOT EXISTS (SELECT 1 FROM dbo.tblRemitoCompra t WHERE t.IdDetalleRemito = rd.IdDetalleRemito)
          AND r.Fecha BETWEEN DATEADD(day, -60, c.Fecha) AND DATEADD(day, 30, c.Fecha)
        """,
        (id_detalle,),
    ) is not None


def renglones_en_alcance() -> list[dict]:
    return fetch_all(
        "SELECT tz.IdDetalleCompra AS id, d.IdCompra AS idCompra, tz.Destino AS destino FROM dbo.TamizRenglones tz "
        "JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra WHERE tz.Vigente = 1 AND tz.Estado = 'Aprobada'"
    )
