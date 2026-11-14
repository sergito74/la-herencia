"""Tamiz por rubro de los renglones de compra (050, research R-05/R-06).

Cada renglón decide solo, sin heredar del proveedor ni de otro renglón. Prioridad:
regla por producto > imputación manual > regla por rubro > revisión. En los insumos de stock la
imputación manual queda solo como referencia (049 FR-002): manda lo que aplican las órdenes.

`clasificar_renglon` es pura (testeable sin base); `tamizar_compra` lee, clasifica y guarda.
"""

from __future__ import annotations

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

    rr = reglas_rubro.get(r.get("idRubro"))
    if rr is None:
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
        falta = "cultivo y campaña" if not cultivo and not campania else ("cultivo" if not cultivo else "campaña")
        return _resultado(r, destino, parte, cultivo, campania, origen="Revision", estado="Pendiente",
                          motivo=f"Falta {falta}")

    if destino == "Depende":
        texto = normalizar(r.get("producto"))
        if especial == "AnalisisLaboratorio":
            if any(p in texto for p in _SUELO):
                if cultivo and campania:
                    return _resultado(r, "Cultivo", 8, cultivo, campania, origen="Manual")
                return _resultado(r, "Cultivo", 8, cultivo, campania, origen="Revision", estado="Pendiente",
                                  motivo="Análisis de suelo: falta cultivo o campaña")
            if any(p in texto for p in _HACIENDA):
                return _resultado(r, "Ganaderia")
            return _resultado(r, None, origen="Revision", estado="Pendiente",
                              motivo="Análisis de laboratorio: ¿de suelo o de hacienda?")
        if especial == "Combustible":
            return _resultado(r, "Estructura", motivo="Combustible sin orden de labor propia")
        if especial == "Financiamiento":
            if contexto.get("financiaInsumo"):
                return _resultado(r, "Cultivo", None, origen="Revision", estado="Pendiente",
                                  motivo="Interés de un insumo financiado: va al cultivo de ese insumo")
            return _resultado(r, "Financiero")
        if especial == "SegunUsoOrden":
            return _resultado(r, "CultivoStock", None,
                              motivo="Se imputa según lo que guarde la orden que lo use")
        return _resultado(r, None, origen="Revision", estado="Pendiente", motivo="Regla sin resolver")

    # Ganadería / Financiero / Estructura / NoImputa: si a mano se cargó cultivo y campaña, se contradicen (P13).
    if destino in ("Estructura", "Financiero") and cultivo and campania:
        return _resultado(r, destino, origen="Revision", estado="Pendiente",
                          motivo="El rubro es gasto general pero el renglón tiene cultivo y campaña cargados")
    return _resultado(r, destino)


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


def tamizar_compra(id_compra: int, *, guardar: bool = True, forzar: bool = False) -> list[dict]:
    """Clasifica todos los renglones de una compra. Solo guarda si la compra está en alcance (o `forzar`,
    para la vista previa del informe de impacto, que pasa `guardar=False`)."""
    if not forzar and not repo.compra_en_alcance(id_compra):
        return []
    renglones = repo.renglones_de_compra(id_compra)
    reglas_rubro = repo.reglas_rubro()
    reglas_producto = repo.reglas_producto()
    ctx = _contexto(renglones, reglas_rubro)
    clasificaciones = [clasificar_renglon(r, reglas_rubro, reglas_producto, ctx) for r in renglones]
    if guardar:
        repo.guardar_clasificaciones(clasificaciones)
    return clasificaciones
