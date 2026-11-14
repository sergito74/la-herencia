"""Tamiz por rubro de los renglones de compra (050, research R-05/R-06).

Cada renglón decide solo, sin heredar del proveedor ni de otro renglón. Prioridad:
regla por producto > imputación manual > regla por rubro > revisión. En los insumos de stock la
imputación manual queda solo como referencia (049 FR-002): manda lo que aplican las órdenes.

`clasificar_renglon` es pura (testeable sin base); `tamizar_compra` lee, clasifica y guarda.
"""

from __future__ import annotations

import logging
import unicodedata

from src.features.imputacion import tamiz_repository as repo

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

    regla = _regla_producto(r, reglas_producto)
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
            return _por_historia(r, aprendido)
        return _resultado(r, None, cultivo=cultivo, campania=campania, origen="Revision", estado="Pendiente",
                          motivo="El rubro no tiene regla de imputación")
    destino, parte, especial = rr["destino"], rr["idParte"], rr["regla"]

    if especial == "FleteInsumo":
        if contexto.get("tieneInsumos"):
            return _resultado(r, "CultivoStock", parte, motivo="Se suma al costo de los insumos de esta factura")
        return _resultado(r, "CultivoStock", parte, origen="Revision", estado="Pendiente",
                          motivo="Flete sin insumos en la factura: relacionarlo con la factura o remito que trajo")

    if destino == "CultivoStock":
        if r.get("idFormulado") is None:
            return _resultado(r, destino, parte, origen="Revision", estado="Pendiente",
                              motivo="Insumo sin producto del catálogo")
        return _resultado(r, destino, parte)

    if destino == "Cultivo":
        if cultivo and campania:
            return _resultado(r, destino, parte, cultivo, campania, origen="Manual")
        if not cultivo and aprendido and aprendido.base != "rubro":
            return _por_historia(r, aprendido)  # p. ej. comercialización de hacienda → Ganadería
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
                return _por_historia(r, aprendido)
            return _resultado(r, None, origen="Revision", estado="Pendiente",
                              motivo="Análisis de laboratorio: ¿de suelo o de hacienda?")
        if especial == "Combustible":
            if cultivo and campania:
                return _resultado(r, "Cultivo", None, cultivo, campania, origen="Manual")
            if aprendido and aprendido.base != "rubro":
                return _por_historia(r, aprendido)
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
                return _por_historia(r, aprendido)
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
        return _por_historia(r, aprendido)
    return _resultado(r, destino)


def _aprendido(r: dict, texto: str, contexto: dict):
    modelo = contexto.get("modelo")
    return modelo.predecir(r.get("idRubro"), texto) if modelo is not None else None


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
        if len(opciones) == 1:
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
    clasificaciones = [clasificar_renglon(r, reglas_rubro, reglas_producto, ctx) for r in renglones]
    if not forzar:
        marcados = repo.renglones_marcados(id_compra)
        if marcados is not None:
            clasificaciones = [c for c in clasificaciones if c["idDetalleCompra"] in marcados]
    if guardar and clasificaciones:
        repo.guardar_clasificaciones(clasificaciones)
    return clasificaciones


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
    return c
