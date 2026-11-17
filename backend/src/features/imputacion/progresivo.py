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
from src.features.imputacion import motor, reparto_plan, repository
from src.features.remitos import capas_factura

PARTE_COMERCIALIZACION = 9
CULTIVOS_FORRAJEROS = {7, 9}  # Pastura, Avena
_CENT = 0.005
PRECISION_BASE = 2e-5  # error relativo máximo por la precisión de las cantidades guardadas (7 dígitos) y del TC


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


def valuar_a_precio_propio(fracciones: list[dict], total: float, cantidad_vinculada: float | None) -> list[dict]:
    """Pura (050, 16/11/2026). Un remito que comparten facturas de distinto precio da un costo promedio; cada
    factura reparte SU importe según las cantidades que consumió cada orden. Solo si las cantidades del reparto
    cubren todo lo vinculado (±0,5%): si falta cantidad (p. ej. un faltante de recuento) no se toca y queda pendiente."""
    if not fracciones or not cantidad_vinculada:
        return fracciones
    cant = sum(float(f.get("cantidad") or 0) for f in fracciones)
    suma = sum(float(f["importe"]) for f in fracciones)
    if abs(cant - cantidad_vinculada) > 0.005 * cantidad_vinculada or abs(suma) <= _CENT or abs(total - suma) <= _CENT:
        return fracciones
    out = [{**f, "importe": round(float(f["importe"]) * total / suma, 2)} for f in fracciones]
    mayor = max(out, key=lambda f: abs(f["importe"]))
    mayor["importe"] = round(mayor["importe"] + round(total - sum(f["importe"] for f in out), 2), 2)
    return out


def cantidad_vinculada_base(id_detalle: int) -> float | None:
    """Lo que la factura tiene vinculado a remitos, en la unidad de las fracciones del motor (la del remito)."""
    filas = repository.vinculos_remito_para_compra(id_detalle)
    if not filas:
        return None
    from src.features.remitos.stock_datos import _familia_unidad
    total = 0.0
    for v in filas:
        q = float(v["cantidadRemitida"] or 0)
        if _familia_unidad(v.get("unidadCompra")) != _familia_unidad(v.get("unidad")) and float(v.get("sumaVinculadaRemito") or 0) > 0:
            rd = fetch_one("SELECT Cantidad AS c FROM dbo.Remitos_Detalles WHERE IdDetalleRemito = ?", (v["idDetalleRemito"],))
            q = q / float(v["sumaVinculadaRemito"]) * float(rd["c"] or 0) if rd else q
        total += q
    return total


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
    clave = lambda f: tuple(-1 if v is None else v for v in (
        f.get("idOrdenTrabajo"), f.get("idLote"), f.get("idCultivo"), f.get("idCampania"), f.get("idCentroCosto"))) + (
        round(float(f.get("importe") or 0), 2), f.get("estado") or "Pendiente")
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
    fracciones = valuar_a_precio_propio(fracciones, total, cantidad_vinculada_base(id_detalle))
    fracciones, motivo = decidir_estado(fracciones, total, motivo)
    if _misma_corrida(id_detalle, fracciones, "Insumo"):
        return {"accion": "sinCambios"}
    id_corrida = repository.guardar_corrida("Insumo", id_detalle, fracciones)
    # 17/11/2026: las NC/ND siguen el reparto de su factura; si este cambió, se recalculan en el mismo momento
    # (antes solo se recalculaban cuando el cambio venía por un producto y quedaban con un reparto viejo).
    fila = fetch_one("SELECT IdCompra AS c FROM dbo.Det_Compras WHERE IdDetalleCompra = ?", (id_detalle,))
    if fila:
        for n in notas_de_compra(fila["c"]):
            imputar_insumo(n)
    return {"accion": "aprobada" if motivo is None else "pendiente", "idCorrida": id_corrida, "motivo": motivo}


def fracciones_directo(t: dict, total: float, id_centro_adm: int | None, superficies: dict[int, float] | None = None) -> list[dict]:
    """Pura (T025): la fracción única de un renglón de una sola vez. Sin cultivo (US4): una fracción por cultivo del
    plan agrícola de la campaña, según su superficie."""
    base = {"importe": total, "idParte": t.get("idParte"), "estado": "Aprobada",
            "fechaAprobacion": datetime.now(timezone.utc)}
    if t["destino"] == "Cultivo" and t.get("idCultivo") is None:
        # Clave (cultivo, campaña): la avena y la pastura llevan su campaña de un año (Avena 2025 en 2025/2026).
        return [{**base, "importe": imp, "idCultivo": k[0] if isinstance(k, tuple) else k,
                 "idCampania": k[1] if isinstance(k, tuple) else t["idCampania"]}
                for k, imp in reparto_plan.repartir(total, superficies or {}).items()]
    if t["destino"] == "Cultivo":
        return [{**base, "idCultivo": t["idCultivo"], "idCampania": t["idCampania"]}]
    if t["destino"] == "Ganaderia":
        return [{**base, "esGanaderia": True}]
    if t["destino"] == "Estructura":
        return [{**base, "idCentroCosto": id_centro_adm}]
    return []  # Financiero / NoImputa: no van a costo de cultivo


def calcular_directo(id_detalle: int) -> dict:
    t = _tamiz(id_detalle)
    if t is None or t["destino"] in ("CultivoStock", "Depende", None):
        return {"accion": "fueraDeAlcance"}
    if t["estado"] != "Aprobada":
        return {"accion": "pendiente"}
    superficies = (reparto_plan.superficie_por_cultivo(t["idCampania"])
                   if t["destino"] == "Cultivo" and t.get("idCultivo") is None and t.get("idCampania") else None)
    fracciones = fracciones_directo(t, total_renglon(t, 0.0), motor._id_centro_adm_general(), superficies)
    if not fracciones:
        # Financiero / No se imputa: si antes iba a un costo, esa imputación deja de valer.
        # Se marca como reemplazada (no se borra: queda quién la aprobó y cuándo).
        return {"accion": "anulada" if repository.marcar_reemplazada(id_detalle, "Directo") else "sinCambios"}
    if _misma_corrida(id_detalle, fracciones, "Directo"):
        return {"accion": "sinCambios"}
    return {"accion": "aprobada", "idCorrida": repository.guardar_corrida("Directo", id_detalle, fracciones)}


def imputar_renglon(id_detalle: int) -> dict:
    t = _tamiz(id_detalle)
    if t is None:
        return {"accion": "fueraDeAlcance"}
    # La imputación del otro origen deja de valer (VIGENTE_050 ya la ignora); se marca como reemplazada sin borrarla.
    repository.marcar_reemplazada(id_detalle, "Directo" if t["destino"] == "CultivoStock" else "Insumo")
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


# ---------------------------------------------------------------- recálculo (050, 16/11/2026)

def notas_de_compra(id_compra: int) -> list[int]:
    """Renglones de NC/ND en alcance relacionados con esta factura (siguen su reparto)."""
    return [f["id"] for f in fetch_all(
        """
        SELECT tz.IdDetalleCompra AS id FROM dbo.TamizRenglones tz
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        WHERE tz.Vigente = 1 AND tz.Estado = 'Aprobada' AND c.[Tipo documento] LIKE 'Nota%'
          AND d.IdCompra IN (SELECT IdCompra FROM dbo.CompraDocumentosRelacionados WHERE IdCompraRelacionada = ?
                             UNION SELECT IdCompraRelacionada FROM dbo.CompraDocumentosRelacionados WHERE IdCompra = ?)
        """,
        (id_compra, id_compra),
    )]


def recalcular_detalle(id_detalle: int) -> None:
    """Vuelve a imputar un renglón (y las notas que siguen a su factura). Fuera de alcance: el recálculo viejo."""
    t = _tamiz(id_detalle)
    if t is None:
        return  # fuera de alcance (anterior a la activación): la historia no se recalcula
    imputar_renglon(id_detalle)
    fila = fetch_one("SELECT IdCompra AS c FROM dbo.Det_Compras WHERE IdDetalleCompra = ?", (id_detalle,))
    if fila:
        for n in notas_de_compra(fila["c"]):
            imputar_renglon(n)


def recalcular_productos(ids_producto) -> None:
    """Cambió el stock de estos productos (orden, remito, recuento): se reimputan todos sus renglones en alcance y
    sus notas. Lo anterior a la activación no se recalcula (no se corrige la historia)."""
    compras = set()
    for pid in {int(p) for p in ids_producto if p}:
        en_alcance = detalles_en_alcance_por_producto(pid)
        for d in en_alcance:
            imputar_insumo(d)
            fila = fetch_one("SELECT IdCompra AS c FROM dbo.Det_Compras WHERE IdDetalleCompra = ?", (d,))
            if fila:
                compras.add(fila["c"])
    for c in compras:
        for n in notas_de_compra(c):
            imputar_renglon(n)


def recalcular_seguro(funcion, *args) -> None:
    """Disparo desde un guardado: un error de imputación nunca impide guardar."""
    import logging
    try:
        funcion(*args)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("Imputación 050: no se pudo recalcular %s", args)
