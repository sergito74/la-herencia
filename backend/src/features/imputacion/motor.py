"""Motor de auto-clasificación de Rubro/Centro de Costos/Cultivo/Campaña
(017-imputacion-automatica-costos).

Sigue la cadena real factura→remito→consumo FIFO→orden→distribución
reutilizando `remitos.stock_datos.calcular_stock()` (FIFO ya implementado en
010, no se reimplementa — research.md) en vez de recalcularlo. No escribe
nada por sí solo: `repository.guardar_corrida()` persiste el resultado.
"""

from __future__ import annotations

from src.features.compras.repository import get_id_centro_costo_por_nombre
from src.features.imputacion import calendario_agricola, repository
from src.features.remitos.stock_datos import calcular_stock
from src.features.remitos.stock_datos import fecha as _normalizar_fecha

EPS = 1e-6

# Umbrales de inconsistencia (US3, research.md): sin dato real para calibrar,
# se documentan como constantes ajustables en vez de quedar hardcodeadas sin nombre.
UMBRAL_INCONSISTENCIA_PORCENTAJE = 0.05
UMBRAL_INCONSISTENCIA_MONTO_MINIMO = 10_000


def _id_centro_ganaderia() -> int | None:
    return get_id_centro_costo_por_nombre("Ganaderia")


def _id_centro_adm_general() -> int | None:
    return get_id_centro_costo_por_nombre("Adm. General")


def evaluar_inconsistencia(total_factura: float, total_repartido: float) -> bool:
    """`True` si la diferencia entre lo repartido y el total de la factura es
    demasiado grande para tolerarla como redondeo (FR-010)."""
    diferencia = abs(total_factura - total_repartido)
    if diferencia <= UMBRAL_INCONSISTENCIA_MONTO_MINIMO:
        return False
    if total_factura <= EPS:
        return diferencia > UMBRAL_INCONSISTENCIA_MONTO_MINIMO
    return (diferencia / total_factura) > UMBRAL_INCONSISTENCIA_PORCENTAJE


def _destino_de_orden_insumo(id_orden_insumo: int, id_orden_trabajo: int, cantidad: float) -> list[dict]:
    """Reparte `cantidad` entre Lote/Cultivo/Campaña de esa Orden, o la manda
    a Centro de Costos "Adm. General" si la Orden no tiene cultivo (FR-005)."""
    orden = repository.orden_trabajo_info(id_orden_trabajo)
    if orden is None:
        return []

    if orden["idRubro"] is not None:
        # Orden de mantenimiento/infraestructura, sin cultivo (spec 011).
        return [
            {
                "idOrdenTrabajo": id_orden_trabajo,
                "idCentroCosto": _id_centro_adm_general(),
                "cantidad": cantidad,
            }
        ]

    distribuciones = repository.distribucion_de_orden_insumo(id_orden_insumo)
    total_asignado = sum(float(d["cantidadAsignada"] or 0) for d in distribuciones) or 1.0
    return [
        {
            "idOrdenTrabajo": id_orden_trabajo,
            "idLote": d["idLote"],
            "idCultivo": d["idCultivo"],
            "idCampania": d["idCampania"],
            "cantidad": cantidad * (float(d["cantidadAsignada"] or 0) / total_asignado),
        }
        for d in distribuciones
    ]


def _destino_de_baja(salida_meta: dict, cantidad: float, id_producto: int) -> list[dict]:
    id_centro_ganaderia = _id_centro_ganaderia()
    id_centro = salida_meta.get("idCentro")
    es_ganaderia = id_centro is not None and id_centro == id_centro_ganaderia
    if id_centro is None:
        # Baja sin Centro de Costos cargado: prioriza la última clasificación
        # aprobada por el usuario para este producto (aprendizaje simple, FR-008)
        # en vez de dejarlo sin destino.
        referencia = repository.obtener_referencia(id_producto, es_ganaderia=True)
        if referencia is not None:
            es_ganaderia = True
    return [
        {
            "idCentroCosto": id_centro,
            "esGanaderia": es_ganaderia,
            "cantidad": cantidad,
        }
    ]


def evaluar_insumo(id_detalle_compra: int) -> tuple[list[dict], str | None]:
    """`calcular_propuesta_insumo` + validación contra el calendario agrícola
    real (`calendario_agricola.py`, pedido del usuario 2026-09-24): si alguna
    fracción imputa a un Cultivo/Campaña cuya fecha real de la Orden cae
    claramente fuera de la ventana plausible de siembra/cosecha (ni siquiera
    con el margen de labores previas), la corrida entera queda
    `RequiereIntervencion` con motivo `'fueraDeCalendarioAgricola'` en vez de
    aprobarse con un dato agronómicamente inconsistente."""
    fracciones = calcular_propuesta_insumo(id_detalle_compra)
    if not fracciones:
        return fracciones, None

    cultivos = repository.nombres_cultivos()
    campanias = repository.nombres_campanias()
    ordenes_cache: dict[int, dict | None] = {}

    for f in fracciones:
        id_orden = f.get("idOrdenTrabajo")
        id_cultivo = f.get("idCultivo")
        id_campania = f.get("idCampania")
        if id_orden is None or id_cultivo is None or id_campania is None:
            continue
        if id_orden not in ordenes_cache:
            ordenes_cache[id_orden] = repository.orden_trabajo_info(id_orden)
        orden = ordenes_cache[id_orden]
        fecha = _normalizar_fecha(orden.get("fecha")) if orden else None
        plausible = calendario_agricola.es_fecha_plausible(cultivos.get(id_cultivo), campanias.get(id_campania), fecha)
        if plausible is False:
            return [], "fueraDeCalendarioAgricola"

    return fracciones, None


def calcular_propuesta_insumo(id_detalle_compra: int) -> list[dict]:
    """Reparto propuesto para un renglón de factura de insumo, siguiendo la
    cadena capa FIFO → Orden/baja → Lote/Cultivo/Campaña (FR-001/FR-002/FR-005).

    Devuelve `[]` si el renglón está fuera de alcance (sin producto, o sin
    ningún remito vinculado todavía — FR-014).
    """
    id_producto = repository.det_compra_producto(id_detalle_compra)
    if id_producto is None:
        return []

    vinculos = repository.vinculos_remito_para_compra(id_detalle_compra)
    if not vinculos:
        return []
    peso_por_detalle_remito = {v["idDetalleRemito"]: float(v["cantidadRemitida"] or 0) for v in vinculos}
    unidades_por_remito = {v["idDetalleRemito"]: v.get("unidad") for v in vinculos}

    stock = calcular_stock(id_producto).get(id_producto, {})
    capas = {c["id"]: c for c in stock.get("capas", [])}
    consumos = stock.get("consumos", {})
    salida_meta = stock.get("salidaMeta", {})

    fracciones: list[dict] = []

    for capa_id, cantidad_remitida in peso_por_detalle_remito.items():
        capa_key = f"R{capa_id}"
        capa = capas.get(capa_key)
        if capa is None or capa["cantidad"] <= EPS:
            continue
        peso_factura_en_capa = cantidad_remitida / float(capa["cantidad"])
        # consumo_base / entrada_base es una proporción; al multiplicarla
        # por CantidadRemitida, la cantidad resultante queda en la unidad
        # original del remito, que puede diferir de la base FIFO y la factura.
        unidad = unidades_por_remito[capa_id]
        costo_unitario = capa.get("costoUnitario") or 0.0

        # Fracción todavía en stock (no consumida) atribuible a esta factura.
        cantidad_stock = float(capa.get("restante", 0)) * peso_factura_en_capa
        if cantidad_stock > EPS:
            fracciones.append({"importe": round(cantidad_stock * costo_unitario, 2), "esStock": True,
                               "cantidad": cantidad_stock, "unidad": unidad})

        for sid, consumo in consumos.items():
            tomado_de_esta_capa = sum(
                float(item["cantidad"]) for item in consumo["items"] if item["capa"] == capa_key
            )
            if tomado_de_esta_capa <= EPS:
                continue
            cantidad_atribuida = tomado_de_esta_capa * peso_factura_en_capa
            importe = round(cantidad_atribuida * costo_unitario, 2)
            meta = salida_meta.get(sid, {})

            if meta.get("tipo") == "ordenTrabajo":
                for destino in _destino_de_orden_insumo(int(sid[2:]), meta["idOrdenTrabajo"], cantidad_atribuida):
                    proporcion = destino["cantidad"] / cantidad_atribuida if cantidad_atribuida > EPS else 0
                    fracciones.append({**destino, "importe": round(importe * proporcion, 2), "unidad": unidad})
            elif meta.get("tipo") == "baja":
                for destino in _destino_de_baja(meta, cantidad_atribuida, id_producto):
                    fracciones.append({**destino, "importe": importe, "unidad": unidad})
            # Otros tipos de salida (ajuste faltante, orden heredada) quedan
            # fuera de alcance de este motor (FR-014): no se les propone reparto.

    return [f for f in fracciones if abs(f["importe"]) > EPS or f.get("esStock")]


def recalcular_si_corresponde(id_detalle_compra: int, origen: str = "Insumo") -> str | None:
    """Vuelve a calcular el reparto de un renglón y guarda una corrida nueva
    en `Estado='Pendiente'` — nunca pisa una corrida ya `Aprobada`, solo
    agrega una nueva por encima (FR-011/FR-012, Clarifications: reemplazo
    completo al aprobar, no incremental). Si el renglón todavía no tiene
    ninguna corrida, no hace nada (no hay nada que recalcular todavía)."""
    if repository.corrida_vigente(id_detalle_compra) is None:
        return None

    if origen == "Contratista":
        fracciones, motivo = evaluar_contratista(id_detalle_compra)
    else:
        fracciones, motivo = evaluar_insumo(id_detalle_compra)
    if not fracciones:
        if motivo:
            return repository.guardar_requiere_intervencion(origen, id_detalle_compra, motivo)
        return None

    fracciones = repository.marcar_stock_sin_consumir_aprobada(fracciones)
    return repository.guardar_corrida(origen, id_detalle_compra, fracciones)


def calcular_propuesta_contratista(id_compra: int) -> list[dict]:
    """Reparto propuesto para una factura de contratista/maquinaria — ver
    `evaluar_contratista` si además se necesita el motivo cuando no hay
    propuesta (US3)."""
    fracciones, _motivo = evaluar_contratista(id_compra)
    return fracciones


def evaluar_contratista(id_compra: int) -> tuple[list[dict], str | None]:
    """Reparto propuesto para una factura de contratista/maquinaria, según las
    Órdenes de Trabajo vinculadas en `OrdenesContratistaFacturas` (N a N,
    FR-003/FR-004). Devuelve `([], motivo)` si no se puede proponer un reparto
    confiable — `motivo` es `"sinOrdenVinculada"` o `"repartoNoCierra"` (US3,
    FR-009/FR-010)."""
    ordenes = repository.ordenes_vinculadas_a_compra(id_compra)
    if not ordenes:
        return [], "sinOrdenVinculada"

    compra = repository.total_neto_compra(id_compra)
    if compra is None:
        return [], "sinOrdenVinculada"
    neto = float(compra["neto"] or 0)
    tc = float(compra["tipoDeCambio"] or 0)
    monto_total = neto * tc if (compra["moneda"] or "Pesos") == "Dolares" and tc else neto

    con_cultivo: list[dict] = []
    sin_cultivo: list[dict] = []
    for id_orden in ordenes:
        orden = repository.orden_trabajo_info(id_orden)
        if orden is None:
            continue
        if orden["idRubro"] is not None:
            sin_cultivo.append({"idOrdenTrabajo": id_orden, "idCentroCosto": _id_centro_adm_general()})
        else:
            for fila in repository.distribucion_de_orden(id_orden):
                con_cultivo.append({"idOrdenTrabajo": id_orden, **fila, "superficie": float(fila["superficie"] or 0)})

    superficie_total = sum(f["superficie"] for f in con_cultivo)
    peso_total = superficie_total + len(sin_cultivo)  # cada Orden sin cultivo pesa como 1 unidad
    if peso_total <= EPS:
        return [], "sinOrdenVinculada"

    fracciones: list[dict] = []
    total_repartido = 0.0
    for f in con_cultivo:
        importe = round(monto_total * f["superficie"] / peso_total, 2)
        total_repartido += importe
        fracciones.append({**f, "importe": importe})
    for f in sin_cultivo:
        importe = round(monto_total * 1 / peso_total, 2)
        total_repartido += importe
        fracciones.append({**f, "importe": importe})

    if evaluar_inconsistencia(monto_total, total_repartido):
        return [], "repartoNoCierra"

    return fracciones, None


def trazabilidad_insumo(id_detalle_compra: int) -> list[dict]:
    """Remonta, on-demand (sin persistir), qué remito/capa/Orden/renglón de
    distribución originó cada fracción de la propuesta vigente de un renglón
    de insumo (FR-013)."""
    id_producto = repository.det_compra_producto(id_detalle_compra)
    if id_producto is None:
        return []

    vinculos = repository.vinculos_remito_para_compra(id_detalle_compra)
    stock = calcular_stock(id_producto).get(id_producto, {})
    capas = {c["id"]: c for c in stock.get("capas", [])}
    consumos = stock.get("consumos", {})
    salida_meta = stock.get("salidaMeta", {})

    trazas: list[dict] = []
    for v in vinculos:
        capa_key = f"R{v['idDetalleRemito']}"
        capa = capas.get(capa_key)
        if capa is None:
            continue
        remito = repository.info_remito_de_capa(v["idDetalleRemito"])
        consumos_de_capa = []
        for sid, consumo in consumos.items():
            tomado = sum(float(i["cantidad"]) for i in consumo["items"] if i["capa"] == capa_key)
            if tomado <= EPS:
                continue
            meta = salida_meta.get(sid, {})
            entrada = {"tipoConsumo": meta.get("tipo"), "cantidad": tomado}
            if meta.get("tipo") == "ordenTrabajo":
                entrada["orden"] = repository.info_orden_trabajo(meta["idOrdenTrabajo"])
                entrada["distribucion"] = repository.distribucion_de_orden_insumo(int(sid[2:]))
            elif meta.get("tipo") == "baja":
                entrada["baja"] = {"idBaja": meta.get("idBaja"), "motivo": meta.get("motivo"), "idCentro": meta.get("idCentro")}
            consumos_de_capa.append(entrada)

        trazas.append(
            {
                "idDetalleRemito": v["idDetalleRemito"],
                "cantidadRemitida": v["cantidadRemitida"],
                "remito": remito,
                "capaCostoUnitario": capa.get("costoUnitario"),
                "capaRestante": capa.get("restante"),
                "consumos": consumos_de_capa,
            }
        )
    return trazas
