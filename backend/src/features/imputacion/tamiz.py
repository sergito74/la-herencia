"""Tamiz por rubro de los renglones de compra (050, research R-05/R-06).

Cada renglón decide solo, sin heredar del proveedor ni de otro renglón. Prioridad:
imputación manual (cultivo y campaña) > regla por producto > regla por rubro > revisión. En los insumos de stock la
imputación manual queda solo como referencia (049 FR-002): manda lo que aplican las órdenes.

`clasificar_renglon` es pura (testeable sin base); `tamizar_compra` lee, clasifica y guarda.
"""

from __future__ import annotations

import logging
import unicodedata

from src.features.imputacion import tamiz_repository as repo
from src.features.imputacion.reparto_plan import PARTES_REPARTIBLES

ETIQUETAS = {
    "CultivoStock": "Va a stock",
    "Cultivo": "A cultivo",
    "Ganaderia": "Ganadería",
    "Financiero": "Financiero",
    "Estructura": "Gasto general",
    "NoImputa": "No se imputa",
    "Depende": "Para revisar",
}

_log = logging.getLogger(__name__)

_SUELO = ("SUELO",)
_HACIENDA = ("HACIENDA", "SANGRE", "BRUCELOSIS", "TUBERCULOSIS", "BOVINO", "TORO", "VACA", "LECHE")


def normalizar(texto: str | None) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().upper()
    return " ".join(t.split())


def _resultado(r, destino, id_parte=None, cultivo=None, campania=None, origen="Rubro", estado="Aprobada", motivo=None):
    return {
        "idDetalleCompra": r["idDetalleCompra"], "destino": destino, "idParte": id_parte, "idCultivo": cultivo,
        "idCampania": campania, "origen": origen, "estado": estado, "motivo": motivo,
    }


def _manual(r) -> tuple[int | None, int | None]:
    campania = r.get("idCampania")
    if campania == repo.CAMPANIA_NO_APLICA:
        campania = None
    return r.get("idCultivo"), campania


def _regla_producto(r, reglas_producto):
    texto = normalizar(r.get("producto"))
    for regla in reglas_producto:
        if regla.get("destino") is None:
            continue
        if regla.get("idFormulado") and regla["idFormulado"] == r.get("idFormulado"):
            return regla
        if regla.get("texto") and regla["texto"] == texto:
            return regla
    return None


def clasificar_renglon(r: dict, reglas_rubro: dict, reglas_producto: list, contexto: dict) -> dict:
    """`contexto`: datos de la factura que el renglón necesita conocer (no deciden por él):
    `particular` ('total'|'parcial'|None) y `tieneInsumos` (si la factura trae insumos de stock, para el flete)."""
    cultivo, campania = _manual(r)

    if contexto.get("particular") == "total":
        return _resultado(r, "NoImputa", motivo="Compra particular")
    if contexto.get("particular") == "parcial" and "PARTICULAR" in normalizar(r.get("producto")):
        # La línea negativa descuenta la parte personal: resta en el mismo destino que el resto de la factura.
        unico = contexto.get("destinoUnicoResto")
        if unico and unico not in ("CultivoStock", "Cultivo", "Depende"):
            return _resultado(r, unico, motivo="Descuenta la parte particular de la factura")
        return _resultado(r, "NoImputa", origen="Revision", estado="Pendiente",
                          motivo="Factura con parte particular y renglones de cultivo: confirmar qué parte es del campo")

    if contexto.get("anulada"):
        # 050 (16/11/2026): factura anulada por NC (o la NC que la anula): la mercadería no se usó o se refacturó.
        return _resultado(r, "NoImputa", motivo=contexto["anulada"])

    if "REDONDEO" in normalizar(r.get("producto")):
        return _resultado(r, "NoImputa", motivo="Redondeo del comprobante")
    texto_n = normalizar(r.get("producto"))
    if ("PERCEPCION" in texto_n or "PERCEPECION" in texto_n) and "IVA" in texto_n:
        # Crédito fiscal, no costo (Sergio 17/11/2026).
        return _resultado(r, "NoImputa", motivo="Percepción de IVA: crédito fiscal")

    if r.get("idDetalleCompra") in (contexto.get("porOrdenes") or set()):
        # 17/11/2026: labor de una factura de contratista repartida por las órdenes de trabajo: va a los cultivos de
        # esas órdenes (no a la historia del texto, que podía mandarla a gasto general).
        return _resultado(r, "Cultivo", cultivo=cultivo, campania=campania, origen="Orden",
                          motivo="Repartido según las órdenes de trabajo")

    # Lo cargado en la factura (cultivo y campaña) manda sobre la regla aprendida del producto: la regla se usa
    # solo cuando la factura no trae el cultivo (Sergio 17/11/2026).
    regla = None if (cultivo and campania) else _regla_producto(r, reglas_producto)
    if regla is not None:
        destino = regla["destino"]
        if destino == "Cultivo":
            if cultivo and campania:
                return _resultado(r, destino, regla["idParte"], cultivo, campania, origen="Producto")
            return _resultado(r, destino, regla["idParte"], cultivo, campania, origen="Revision", estado="Pendiente",
                              motivo="Falta cultivo o campaña")
        return _resultado(r, destino, regla["idParte"], origen="Producto")

    texto = normalizar(r.get("producto"))
    aprendido = _aprendido(r, texto, contexto)

    rr = reglas_rubro.get(r.get("idRubro"))
    if rr is None:
        if cultivo and campania:
            return _resultado(r, "Cultivo", None, cultivo, campania, origen="Manual")
        if aprendido:
            return _historia(r, aprendido)
        return _resultado(r, None, cultivo=cultivo, campania=campania, origen="Revision", estado="Pendiente",
                          motivo="El rubro no tiene regla de imputación")
    destino, parte, especial = rr["destino"], rr["idParte"], rr["regla"]

    if especial == "FleteInsumo":
        if contexto.get("tieneInsumos"):
            return _resultado(r, "CultivoStock", parte, motivo="Se suma al costo de los insumos de esta factura")
        if cultivo and campania:
            # Flete de insumos que no tienen factura (semilla propia o entregada sin remito): va directo al cultivo y
            # campaña cargados en la compra (Sergio 17/11/2026).
            return _resultado(r, "Cultivo", parte, cultivo, campania, origen="Manual",
                              motivo="Flete de insumos sin factura: va al cultivo y campaña cargados")
        return _resultado(r, "CultivoStock", parte, origen="Revision", estado="Pendiente",
                          motivo="Flete sin insumos en la factura: relacionarlo con la factura o remito que trajo")

    if destino == "CultivoStock":
        if "REDONDEO" in texto:
            return _resultado(r, "NoImputa", motivo="Redondeo del comprobante")
        if (r.get("tipoDocumento") or "").startswith("Nota"):
            # NC / ND de insumos (ajuste de precio o de tipo de cambio): no mueven stock, siguen el reparto de su
            # documento base (Sergio 15/11/2026).
            return _resultado(r, destino, parte, motivo="Sigue a su documento base")
        if r.get("idFormulado") is None:
            sugerido = (contexto.get("sugerencias") or {}).get(r.get("idDetalleCompra"))
            motivo = "Insumo sin producto del catálogo" + (f" (¿es {repo.nombre_producto(sugerido)}?)" if sugerido else "")
            return _resultado(r, destino, parte, origen="Revision", estado="Pendiente", motivo=motivo)
        return _resultado(r, destino, parte)

    if destino == "Cultivo":
        if cultivo and campania:
            return _resultado(r, destino, parte, cultivo, campania, origen="Manual")
        if not cultivo and aprendido and aprendido.base != "rubro":
            return _historia(r, aprendido)  # p. ej. comercialización de hacienda → Ganadería
        return _deducir(r, destino, parte, cultivo, campania, contexto)

    if destino == "Depende":
        if especial == "AnalisisLaboratorio":
            if any(p in texto for p in _SUELO):
                if cultivo and campania:
                    return _resultado(r, "Cultivo", 8, cultivo, campania, origen="Manual")
                return _resultado(r, "Cultivo", 8, cultivo, campania, origen="Revision", estado="Pendiente",
                                  motivo="Análisis de suelo: falta cultivo o campaña")
            if any(p in texto for p in _HACIENDA):
                return _resultado(r, "Ganaderia")
            if cultivo and campania:
                return _resultado(r, "Cultivo", 8, cultivo, campania, origen="Manual")
            if aprendido:
                return _historia(r, aprendido)
            return _resultado(r, None, origen="Revision", estado="Pendiente",
                              motivo="Análisis de laboratorio: ¿de suelo o de hacienda?")
        if especial == "Combustible":
            if cultivo and campania:
                return _resultado(r, "Cultivo", None, cultivo, campania, origen="Manual")
            if aprendido and aprendido.base != "rubro":
                return _historia(r, aprendido)
            return _resultado(r, "Estructura", motivo="Combustible sin orden de labor propia")
        if especial == "Financiamiento":
            # Sergio 14/11: se clasifica según lo que financió (documento relacionado); si no hay, la historia.
            fin = contexto.get("financiaDestino")
            if fin:
                return _resultado(r, fin["destino"], fin.get("idParte"), fin.get("idCultivo"), fin.get("idCampania"),
                                  motivo="Según lo que financió (documento relacionado)")
            if cultivo and campania:
                return _resultado(r, "Cultivo", None, cultivo, campania, origen="Manual")
            if aprendido:
                return _historia(r, aprendido)
            return _resultado(r, None, origen="Revision", estado="Pendiente",
                              motivo="Financiamiento: relacionarlo con lo que financió")
        if especial == "SegunUsoOrden":
            if cultivo and campania:
                return _resultado(r, "Cultivo", 9, cultivo, campania, origen="Manual")
            # Sergio 14/11: el uso del silobolsa no se registra en las órdenes; lo indica él al cargar.
            # Grano para vender → A cultivo, parte Comercialización (cultivo y campaña); forraje/consumo → Ganadería.
            return _resultado(r, None, origen="Revision", estado="Pendiente",
                              motivo="Silobolsa / insumo productivo: indicar el uso (grano para vender: cultivo y campaña; forraje o consumo propio: Ganadería)")
        return _resultado(r, None, origen="Revision", estado="Pendiente", motivo="Regla sin resolver")

    # Ganadería / Financiero / Estructura: lo cargado a mano (cultivo y campaña) gana sobre el rubro (R-05);
    # sin eso, decide la historia del mismo texto en el rubro (el centro depende del destino, no del rubro).
    if destino in ("Estructura", "Financiero", "Ganaderia") and cultivo and campania:
        return _resultado(r, "Cultivo", None, cultivo, campania, origen="Manual")
    if aprendido and aprendido.base != "rubro" and aprendido.destino != destino:
        return _historia(r, aprendido)
    return _resultado(r, destino)


def _aprendido(r: dict, texto: str, contexto: dict):
    modelo = contexto.get("modelo")
    return modelo.predecir(r.get("idRubro"), texto) if modelo is not None else None


def _historia(r: dict, pred) -> dict:
    """La historia decide sola solo si la misma descripción se imputó siempre igual (100%); si no, sugiere y pregunta
    (Sergio 17/11/2026: una palabra suelta o un texto parecido no alcanzan para el sistema autónomo)."""
    if pred.base == "texto" and pred.confianza >= 0.9999:
        return _por_historia(r, pred)
    sugerido = ETIQUETAS.get(pred.destino, pred.destino)
    return _resultado(r, pred.destino, origen="Revision", estado="Pendiente",
                      motivo=f"¿{sugerido}? Se sugiere por {pred.base} ({round(pred.confianza * 100)}% de los casos): confirmar")


def _por_historia(r: dict, pred) -> dict:
    return _resultado(r, pred.destino, origen="Historia",
                      motivo=f"Como se imputó antes ({pred.base}, {round(pred.confianza * 100)}% de los casos)")


_PARTES_ANTICIPADAS = (7,)  # seguro agrícola: se contrata antes de la campaña que cubre


def _anio_agricola(fecha, anticipado: bool) -> str | None:
    """Campaña que corresponde a la fecha. `anticipado` (seguro, barbecho): de abril a junio ya cubre la que viene."""
    if fecha is None:
        return None
    y = fecha.year if fecha.month >= 7 else fecha.year - 1
    if anticipado and 4 <= fecha.month <= 6:
        y += 1
    return f"{y}/{y + 1}"


def _deducir(r, destino, parte, cultivo, campania, contexto) -> dict:
    """T011/T012 (FR-006): propone campaña y cultivo cuando faltan. La campaña deducida siempre queda para
    revisar; el cultivo se asigna solo cuando hay una única opción y la campaña vino cargada."""
    texto = normalizar(r.get("producto"))
    motivos = []
    campania_cargada = bool(campania)
    if not campania:
        anticipado = parte in _PARTES_ANTICIPADAS or "BARBECHO" in texto
        nombre = _anio_agricola(contexto.get("fecha"), anticipado)
        campania = (contexto.get("campaniasPorNombre") or {}).get(nombre)
        if campania:
            criterio = "campaña siguiente (se contrata antes)" if anticipado and nombre != campania_vigente(contexto.get("fecha")) else "vigente a la fecha"
            motivos.append(f"Falta campaña: se propone {nombre} ({criterio})")
        else:
            motivos.append("Falta campaña")
    if not cultivo:
        nombres = contexto.get("cultivos") or {}
        por_texto = [i for i, n in nombres.items() if n and len(normalizar(n)) >= 4 and normalizar(n) in texto]
        opciones = por_texto or ((contexto.get("cultivosPorCampania") or {}).get(campania) or [])
        if not por_texto and campania_cargada and not motivos and parte in PARTES_REPARTIBLES:
            # 050 US4: costo de la campaña y no de un cultivo → se reparte por la superficie del plan agrícola.
            if (contexto.get("superficiePlan") or {}).get(campania):
                return _resultado(r, destino, parte, None, campania, origen="Rubro",
                                  motivo="Repartido según la superficie del plan agrícola")
            motivos.append("Falta cultivo y el plan agrícola no tiene superficie para la campaña")
        elif len(opciones) == 1:
            cultivo = opciones[0]
            if not motivos and campania_cargada:
                origen = "el producto" if por_texto else "la única con órdenes en la campaña"
                return _resultado(r, destino, parte, cultivo, campania, origen="Rubro",
                                  motivo=f"Cultivo deducido por {origen}")
            motivos.append(f"Cultivo propuesto: {nombres.get(cultivo)}")
        elif opciones:
            motivos.append("Falta cultivo; opciones: " + ", ".join(sorted(nombres.get(i, str(i)) for i in opciones)))
        else:
            motivos.append("Falta cultivo")
    return _resultado(r, destino, parte, cultivo, campania, origen="Revision", estado="Pendiente",
                      motivo="; ".join(motivos))


def campania_vigente(fecha) -> str | None:
    """Año agrícola julio-junio: 15/08/2026 → '2026/2027'; 10/03/2026 → '2025/2026'."""
    if fecha is None:
        return None
    y = fecha.year if fecha.month >= 7 else fecha.year - 1
    return f"{y}/{y + 1}"


def _contexto(renglones: list[dict], reglas_rubro: dict) -> dict:
    textos = [normalizar(r.get("producto")) for r in renglones]
    hay_particular = any("PARTICULAR" in t for t in textos)
    total = sum(float(r["cantidad"]) * float(r["precio"]) for r in renglones)
    particular = None
    if hay_particular:
        particular = "total" if abs(total) < 0.01 else "parcial"
    tiene_insumos = any(
        (reglas_rubro.get(r.get("idRubro")) or {}).get("destino") == "CultivoStock"
        and (reglas_rubro.get(r.get("idRubro")) or {}).get("regla") is None
        for r in renglones
    )
    destinos_resto = {
        (reglas_rubro.get(r.get("idRubro")) or {}).get("destino")
        for r, t in zip(renglones, textos) if "PARTICULAR" not in t
    }
    destino_unico = next(iter(destinos_resto)) if len(destinos_resto) == 1 else None
    return {"particular": particular, "tieneInsumos": tiene_insumos, "destinoUnicoResto": destino_unico}


def tamizar_compra(id_compra: int, *, guardar: bool = True, forzar: bool = False, modelo=None) -> list[dict]:
    """Clasifica todos los renglones de una compra. Solo guarda si la compra está en alcance (o `forzar`,
    para la vista previa del informe de impacto, que pasa `guardar=False`)."""
    if not forzar and not repo.compra_en_alcance(id_compra):
        return []
    renglones = repo.renglones_de_compra(id_compra)
    reglas_rubro = repo.reglas_rubro()
    reglas_producto = repo.reglas_producto()
    ctx = _contexto(renglones, reglas_rubro)
    if modelo is None:
        from src.features.imputacion import aprendizaje

        modelo = aprendizaje.modelo()
    ctx["modelo"] = modelo
    ctx["financiaDestino"] = repo.destino_financiado(id_compra)
    ctx["anulada"] = repo.anulada(id_compra)
    from src.features.imputacion import repository as _rep
    ctx["porOrdenes"] = {r["idDetalleCompra"] for r in renglones if _rep.en_reparto_por_ordenes(r["idDetalleCompra"])}
    # Renglón de insumo sin producto del catálogo: se busca por el texto (050, 16/11/2026). Con una coincidencia segura
    # se le asigna el producto; si no, queda pendiente con la sugerencia.
    asignados = _sugerir_productos(renglones, reglas_rubro, ctx)
    if not ctx.get("tieneInsumos") and repo.relacionada_con_insumos(id_compra):
        # Flete facturado aparte y relacionado con la factura de la mercadería: se suma a esos insumos.
        ctx["tieneInsumos"] = True
    fecha = renglones[0].get("fecha") if renglones else None
    if hasattr(fecha, "date"):
        fecha = fecha.date()
    ctx["fecha"] = fecha
    if any(r.get("idCultivo") is None or r.get("idCampania") in (None, repo.CAMPANIA_NO_APLICA) for r in renglones):
        nombres = {n for n in (_anio_agricola(fecha, False), _anio_agricola(fecha, True)) if n}
        ctx["campaniasPorNombre"] = {n: repo.campania_por_nombre(n) for n in nombres}
        ctx["cultivos"] = repo.cultivos()
        camps = {c for c in ctx["campaniasPorNombre"].values() if c} | {
            r["idCampania"] for r in renglones if r.get("idCampania") not in (None, repo.CAMPANIA_NO_APLICA)}
        ctx["cultivosPorCampania"] = {c: repo.cultivos_con_ordenes(c) for c in camps}
        from src.features.imputacion import reparto_plan
        ctx["superficiePlan"] = {c: reparto_plan.superficie_por_cultivo(c) for c in camps}
    clasificaciones = [clasificar_renglon(r, reglas_rubro, reglas_producto, ctx) for r in renglones]
    if not forzar:
        marcados = repo.renglones_marcados(id_compra)
        if marcados is not None:
            clasificaciones = [c for c in clasificaciones if c["idDetalleCompra"] in marcados]
    # Una corrección hecha a mano (OrigenDecision = 'Manual') no se pisa al volver a clasificar la compra.
    manuales = repo.renglones_corregidos_a_mano(id_compra)
    clasificaciones = [c for c in clasificaciones if c["idDetalleCompra"] not in manuales]
    if guardar and clasificaciones:
        if asignados:
            from src.db.connection import execute_write_transaction
            execute_write_transaction([("UPDATE dbo.Det_Compras SET IdFormulado = ? WHERE IdDetalleCompra = ? AND ISNULL(IdFormulado, 0) = 0",
                                        (pid, idd)) for idd, pid in asignados.items()])
        repo.guardar_clasificaciones(clasificaciones)
    return clasificaciones


def _sugerir_productos(renglones: list[dict], reglas_rubro: dict, ctx: dict) -> dict[int, int]:
    pendientes = [r for r in renglones if r.get("idFormulado") is None
                  and (reglas_rubro.get(r.get("idRubro")) or {}).get("destino") == "CultivoStock"
                  and (reglas_rubro.get(r.get("idRubro")) or {}).get("regla") != "FleteInsumo"
                  and not (r.get("tipoDocumento") or "").startswith("Nota")
                  and (r.get("unidad") or "").strip().upper() not in ("ARS", "USD")]
    if not pendientes:
        return {}
    from src.features.imputacion.sugeridor import SEGURAS, Sugeridor
    sug, asignados = Sugeridor(), {}
    ctx.setdefault("sugerencias", {})
    for r in pendientes:
        pid, via = sug.sugerir(r.get("producto"))
        if pid and via in SEGURAS:
            r["idFormulado"] = int(pid)
            asignados[r["idDetalleCompra"]] = int(pid)
        elif pid:
            ctx["sugerencias"][r["idDetalleCompra"]] = int(pid)
    return asignados


def tamizar_al_guardar(id_compra: int) -> None:
    """Disparo del guardado de la compra (T013): solo en alcance y nunca impide guardar."""
    try:
        clasificaciones = tamizar_compra(id_compra)
        if clasificaciones:
            from src.features.imputacion import progresivo
            from src.features.remitos import vinculo_auto

            vinculo_auto.vincular_seguro(vinculo_auto.vincular_por_compra, id_compra)
            for c in clasificaciones:
                if c["estado"] == "Aprobada":
                    progresivo.imputar_renglon(c["idDetalleCompra"])  # T025 / imputación progresiva
            # La factura nueva cambia las capas FIFO de sus productos: se reimputan los demás renglones (050, 16/11/2026).
            pids = {r["idFormulado"] for r in repo.renglones_de_compra(id_compra) if r.get("idFormulado")}
            progresivo.recalcular_seguro(progresivo.recalcular_productos, pids)
    except Exception:  # noqa: BLE001 - el tamiz no puede romper el alta de la compra
        _log.exception("Tamiz 050: no se pudo clasificar la compra %s", id_compra)


def corregir_renglon(id_detalle: int, destino: str, id_parte: int | None, id_cultivo: int | None,
                     id_campania: int | None, guardar_regla: bool, usuario: str | None) -> dict:
    """Corrección a mano (PUT /tamiz/renglon): queda aprobada; opcionalmente aprende la regla por producto."""
    if destino not in ETIQUETAS:
        raise ValueError("Destino inválido")
    if destino == "Cultivo" and not (id_cultivo and id_campania and id_campania != repo.CAMPANIA_NO_APLICA):
        raise ValueError("Para imputar a cultivo hacen falta cultivo y campaña")
    c = {"idDetalleCompra": id_detalle, "destino": destino, "idParte": id_parte, "idCultivo": id_cultivo,
         "idCampania": id_campania, "origen": "Manual", "estado": "Aprobada", "motivo": "Corregido a mano"}
    repo.guardar_clasificaciones([c], usuario)
    if guardar_regla:
        repo.guardar_regla_producto(id_detalle, destino, id_parte, usuario)
    from src.features.imputacion import progresivo

    progresivo.imputar_renglon(id_detalle)  # la corrección se refleja en el costo en el momento
    return c
