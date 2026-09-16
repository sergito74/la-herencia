"""Resuelve `Origen`/`IdOrigen` de `dbo.vw_MovimientosCuenta_Base` a una
referencia explícita hacia compras o tesorería (FR-006, FR-007, FR-008).

Mapeo cerrado per data-model.md (confirmado contra datos reales 2026-09-16).
Resolución directa por clave (`IdOrigen`), no heurística — a diferencia de
`specs/003-tesoreria/matching.py` (research.md).
"""

from __future__ import annotations

from src.features.cuentas_corrientes import repository

_MEDIO_POR_ORIGEN_TIPO = {
    "Banco Nacion": "bna",
    "Galicia": "galicia",
    "Pagos efectivo": "efectivo",
    "Cobros Valores Recibidos": "valores_recibidos",
    "Pagos Valores Recibidos": "valores_recibidos",
}

_LOOKUP_POR_MEDIO = {
    "bna": "get_bna_referencia",
    "galicia": "get_galicia_referencia",
    "efectivo": "get_efectivo_referencia",
    "valores_recibidos": "get_valores_recibidos_referencia",
}

_NO_DISPONIBLE_SIN_ID = {"tipo": "no_disponible", "motivo": "IdOrigen sin cargar"}
_NO_DISPONIBLE_SIN_REGISTRO = {
    "tipo": "no_disponible",
    "motivo": "registro de origen no encontrado",
}


def resolve_origen(origen_tipo: str | None, id_origen: int | None) -> dict:
    """Devuelve siempre uno de los 4 estados definidos en el contrato de API."""
    if id_origen is None:
        return dict(_NO_DISPONIBLE_SIN_ID)

    if origen_tipo == "Compras":
        compra = repository.get_compra_referencia(id_origen)
        if compra is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {
            "tipo": "compra",
            "idCompra": compra["idCompra"],
            "numeroDocumento": compra.get("numeroDocumento"),
            "proveedor": compra.get("proveedor"),
        }

    medio = _MEDIO_POR_ORIGEN_TIPO.get(origen_tipo)
    if medio is not None:
        lookup = getattr(repository, _LOOKUP_POR_MEDIO[medio])
        referencia = lookup(id_origen)
        if referencia is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {
            "tipo": "tesoreria",
            "medio": medio,
            "idMovimiento": referencia["idMovimiento"],
            "fecha": referencia.get("fecha"),
            "importe": referencia.get("importe"),
        }

    # Incluye los 6 valores confirmados sin módulo en alcance y cualquier
    # valor de `Origen` no relevado (ej. "Valores propios", "Tarjetas") —
    # tratado como fuera de alcance por defecto per data-model.md.
    return {"tipo": "fuera_de_alcance", "origenTipo": origen_tipo}
