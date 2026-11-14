"""Motor de auto-clasificación de Rubro/Centro de Costos/Cultivo/Campaña
(017-imputacion-automatica-costos).

Sigue la cadena real factura→remito→consumo FIFO→orden→distribución
reutilizando `remitos.stock_datos.calcular_stock()` (FIFO ya implementado en
010, no se reimplementa — research.md) en vez de recalcularlo. No escribe
nada por sí solo: `repository.guardar_corrida()` persiste el resultado.
"""

from __future__ import annotations
from collections import defaultdict

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
    if repository.corrida_vigente(id_detalle_compra, origen if origen == "Contratista" else None) is None:
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

    # 13/11/2026 (Sergio): la imputación manual de cada renglón (cultivo/campaña) manda. El importe de cada
    # renglón va a los lotes de las órdenes con ese cultivo y campaña (o solo ese cultivo); lo que no encaja
    # se reparte por superficie entre todas las órdenes, como antes.
    importes: dict[int, float] = defaultdict(float)  # índice en con_cultivo -> importe
    importe_sin_cultivo = 0.0
    sin_lote: dict[tuple, float] = defaultdict(float)
    cambio_campania: dict[tuple, float] = defaultdict(float)
    renglones = repository.renglones_repartibles(id_compra)
    neto_renglones = sum(float(r["neto"] or 0) for r in renglones)
    resto = monto_total
    if abs(neto_renglones) > EPS:
        for r in renglones:
            monto = monto_total * float(r["neto"] or 0) / neto_renglones
            destino = [i for i, f in enumerate(con_cultivo)
                       if r["idCultivo"] and f["idCultivo"] == r["idCultivo"] and f["idCampania"] == r["idCampania"]]
            sup = sum(con_cultivo[i]["superficie"] for i in destino)
            otra_campania = [i for i, f in enumerate(con_cultivo) if r["idCultivo"] and f["idCultivo"] == r["idCultivo"]]
            sup_otra = sum(con_cultivo[i]["superficie"] for i in otra_campania)
            if destino and sup > EPS:
                for i in destino:
                    importes[i] += monto * con_cultivo[i]["superficie"] / sup
                resto -= monto
            elif otra_campania and sup_otra > EPS:
                # Mismo cultivo, otra campaña en la orden: lotes de la orden, campaña la imputada a mano.
                for i in otra_campania:
                    cambio_campania[(i, r["idCampania"])] += monto * con_cultivo[i]["superficie"] / sup_otra
                resto -= monto
            elif r["idCultivo"]:
                # Cultivo imputado a mano que ninguna orden tiene: queda en su cultivo/campaña, sin lote.
                sin_lote[(r["idCultivo"], r["idCampania"])] += monto
                resto -= monto
    for i, f in enumerate(con_cultivo):
        importes[i] += resto * f["superficie"] / peso_total
    importe_sin_cultivo = resto / peso_total

    fracciones: list[dict] = []
    total_repartido = 0.0
    for i, f in enumerate(con_cultivo):
        importe = round(importes[i], 2)
        total_repartido += importe
        fracciones.append({**f, "importe": importe})
    for f in sin_cultivo:
        importe = round(importe_sin_cultivo, 2)
        total_repartido += importe
        fracciones.append({**f, "importe": importe})
    for (i, id_campania), monto in cambio_campania.items():
        fracciones.append({**con_cultivo[i], "idCampania": id_campania, "importe": round(monto, 2)})
    for (id_cultivo, id_campania), monto in sin_lote.items():
        fracciones.append({"idOrdenTrabajo": ordenes[0], "idLote": None, "idCultivo": id_cultivo,
                           "idCampania": id_campania, "superficie": 0.0, "importe": round(monto, 2)})
    fracciones = [f for f in fracciones if abs(f["importe"]) > 0.004] or fracciones
    total_repartido = sum(f["importe"] for f in fracciones)

    # 048: la última fracción absorbe el redondeo para cerrar al centavo.
    if fracciones:
        fracciones[-1]["importe"] = round(fracciones[-1]["importe"] + round(monto_total, 2) - round(total_repartido, 2), 2)
        total_repartido = sum(f["importe"] for f in fracciones)
    if evaluar_inconsistencia(monto_total, total_repartido):
        return [], "repartoNoCierra"

    return fracciones, None


def evaluar_nota_relacionada(id_nc: int) -> list[dict]:
    """048: NC/ND de contratista — replica las proporciones del reparto vigente de su factura sobre su propio
    neto repartible, con signo negativo para la NC. Sin factura con reparto: []."""
    id_factura = repository.factura_de_nota(id_nc)
    id_corrida = repository.reparto_contratista_vigente(id_factura) if id_factura else None
    nota = repository.total_neto_compra(id_nc)
    if not id_corrida or not nota or not nota["neto"]:
        return []
    base = [f for f in repository.fracciones_de_corrida(id_corrida) if f["idOrdenTrabajo"] is not None]
    total_base = sum(float(f["importe"]) for f in base)
    if abs(total_base) <= EPS:
        return []
    neto = float(nota["neto"])
    tc = float(nota["tipoDeCambio"] or 0)
    monto = neto * tc if (nota["moneda"] or "Pesos") == "Dolares" and tc else neto
    if (nota["tipoDocumento"] or "").lower().replace("é", "e").startswith("nota de credito"):
        monto = -monto
    fracciones = [{**{k: f[k] for k in ("idOrdenTrabajo", "idLote", "idCultivo", "idCampania", "idCentroCosto")},
                   "importe": round(monto * float(f["importe"]) / total_base, 2)} for f in base]
    fracciones[-1]["importe"] = round(fracciones[-1]["importe"] + round(monto, 2) - sum(f["importe"] for f in fracciones), 2)
    return fracciones


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
