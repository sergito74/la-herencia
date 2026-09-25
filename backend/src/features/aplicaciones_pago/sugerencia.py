"""Sugerencia FIFO de aplicación (019, research.md §3): dado un movimiento
bancario real, sugiere los documentos pendientes más antiguos del mismo
contacto hasta cubrir su importe. Solo lectura — el usuario confirma o
edita antes de guardar (FR-003/FR-004)."""

from __future__ import annotations

from src.features.aplicaciones_pago.documentos import documentos_pendientes
from src.features.tesoreria.matching import _ANCHOR_BY_MEDIO
from src.features.tesoreria.repository import get_movimiento


def _importe_con_signo(origen_movimiento: str, row: dict) -> float | None:
    """`matching._ANCHOR_BY_MEDIO` devuelve el importe en valor absoluto
    (lo necesita para matchear contra `Deuda`, siempre positiva) — acá
    hace falta el signo real para saber si el movimiento es un egreso
    (aplica contra compras) o un ingreso (aplica contra ventas)."""
    if origen_movimiento == "bna":
        return float(row["importe"]) if row.get("importe") is not None else None
    if origen_movimiento == "galicia":
        creditos = float(row.get("creditos") or 0)
        debitos = float(row.get("debitos") or 0)
        return creditos - debitos
    if origen_movimiento == "efectivo":
        return float(row["importeImputado"]) if row.get("importeImputado") is not None else None
    if origen_movimiento == "valores-recibidos":
        return float(row["importe"]) if row.get("importe") is not None else None
    if origen_movimiento == "tarjetas":
        return -float(row["importe"]) if row.get("importe") is not None else None
    return None


def _contacto_e_importe(origen_movimiento: str, id_movimiento_origen: int) -> tuple[int | None, float | None]:
    row = get_movimiento(origen_movimiento, id_movimiento_origen)
    if row is None:
        return None, None
    anchor = _ANCHOR_BY_MEDIO.get(origen_movimiento)
    if anchor is None:
        return None, None
    id_contacto, _fecha, _importe_abs = anchor(row)
    return id_contacto, _importe_con_signo(origen_movimiento, row)


def sugerir(origen_movimiento: str, id_movimiento_origen: int) -> dict:
    id_contacto, importe = _contacto_e_importe(origen_movimiento, id_movimiento_origen)
    if id_contacto is None or importe is None:
        return {"importeMovimiento": importe or 0.0, "sugerencias": [], "saldoSinAsignar": importe or 0.0}

    # Egreso (compra) o ingreso (venta) segun el signo real del movimiento.
    tipo = "compra" if importe < 0 else "venta"
    importe_abs = round(abs(importe), 2)

    pendientes = documentos_pendientes(id_contacto, tipo)
    sugerencias = []
    restante = importe_abs
    for doc in pendientes:
        if restante <= 0:
            break
        importe_sugerido = round(min(doc["saldoPendiente"], restante), 2)
        sugerencias.append(
            {
                "tipoDocumento": doc["tipoDocumento"],
                "idDocumento": doc["idDocumento"],
                "fecha": doc["fecha"],
                "saldoPendiente": doc["saldoPendiente"],
                "importeSugerido": importe_sugerido,
            }
        )
        restante = round(restante - importe_sugerido, 2)

    return {"importeMovimiento": importe_abs, "sugerencias": sugerencias, "saldoSinAsignar": max(restante, 0.0)}
