"""Resuelve `Origen`/`IdOrigen` de `dbo.vw_MovimientosCuenta_Base` a una
referencia explícita hacia compras o tesorería (FR-006, FR-007, FR-008).

Mapeo cerrado per data-model.md (confirmado contra datos reales 2026-09-16).
Resolución directa por clave (`IdOrigen`), no heurística — a diferencia de
`specs/003-tesoreria/matching.py` (research.md).
"""

from __future__ import annotations

from src.features.arrendamientos import repository as arrendamientos_repository
from src.features.cuentas_corrientes import repository
from src.features.impuestos import repository as impuestos_repository
from src.features.remuneraciones import repository as remuneraciones_repository
from src.features.ventas_hacienda import repository as ventas_hacienda_repository

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

    if origen_tipo == "Conciliación Tesorería":
        # 023-conciliacion-tesoreria: IdOrigen acá es el IdConciliacion, no
        # el id del movimiento original — se resuelve un nivel más antes de
        # armar el mismo link "tesoreria" que ya usan bna/galicia/efectivo.
        conciliacion = repository.get_conciliacion_tesoreria_referencia(id_origen)
        if conciliacion is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {
            "tipo": "tesoreria",
            "medio": conciliacion["medio"],
            "idMovimiento": conciliacion["idMovimiento"],
            "fecha": conciliacion.get("fecha"),
            "importe": conciliacion.get("importe"),
        }

    if origen_tipo in ("Impuestos", "Retenciones"):
        if origen_tipo == "Impuestos":
            impuesto = impuestos_repository.get_impuesto_referencia(id_origen)
            if impuesto is None:
                return dict(_NO_DISPONIBLE_SIN_REGISTRO)
            return {
                "tipo": "impuesto",
                "idImpuesto": impuesto["idImpuesto"],
                "tipoImpuesto": impuesto.get("tipoImpuesto"),
                "importe": impuesto.get("importe"),
            }
        retencion = impuestos_repository.get_retencion_referencia(id_origen)
        if retencion is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {
            "tipo": "retencion",
            "idRetencion": retencion["idRetencion"],
            "numeroCertificado": retencion.get("numeroCertificado"),
            "importe": retencion.get("importe"),
        }

    if origen_tipo == "Remuneraciones":
        remuneracion = remuneraciones_repository.get_remuneracion_referencia(id_origen)
        if remuneracion is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {
            "tipo": "remuneracion",
            "idSalario": remuneracion["idSalario"],
            "periodoLiquidado": remuneracion.get("periodoLiquidado"),
            "empleado": remuneracion.get("empleado"),
        }

    if origen_tipo == "Alquileres":
        arrendamiento = arrendamientos_repository.get_arrendamiento_referencia(id_origen)
        if arrendamiento is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {
            "tipo": "arrendamiento",
            "idAlquiler": arrendamiento["idAlquiler"],
            "contacto": arrendamiento.get("contacto"),
            "importeTotalContrato": arrendamiento.get("importeTotalContrato"),
        }

    if origen_tipo == "Ret. Ventas Hacienda":
        # Referencia a la retención, no a la venta en sí — no existe un
        # valor de `Origen` para la venta de hacienda (ver
        # specs/005-egresos-y-ventas-menores/research.md).
        retencion_venta = ventas_hacienda_repository.get_retencion_venta_hacienda_referencia(
            id_origen
        )
        if retencion_venta is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {
            "tipo": "venta_hacienda",
            "idRetencion": retencion_venta["idRetencion"],
            "numeroDocumento": retencion_venta.get("numeroDocumento"),
            "importe": retencion_venta.get("importe"),
        }

    # 034-cuenta-corriente-tarjetas: ramas de la pata deuda de las tarjetas y de Mercado Pago.
    if origen_tipo == "Tarjeta consumo":
        consumo = repository.get_tarjeta_consumo_referencia(id_origen)
        if consumo is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {
            "tipo": "tarjeta_consumo",
            "idLineaConsumo": consumo["idLineaConsumo"],
            "idResumen": consumo["idResumen"],
            "numeroDocumento": consumo.get("numeroDocumento"),
        }

    if origen_tipo == "Tarjeta cargo":
        # `IdOrigen = IdResumen * 100 + n` (n = número de cargo, 1 a 14).
        resumen = repository.get_tarjeta_resumen_referencia(id_origen // 100)
        if resumen is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {"tipo": "tarjeta_resumen", "idResumen": resumen["idResumen"], "numeroDocumento": resumen.get("numeroDocumento")}

    if origen_tipo == "Tarjeta pago":
        pago = repository.get_tarjeta_pago_referencia(id_origen)
        if pago is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {
            "tipo": "tarjeta_resumen",
            "idResumen": pago["idResumen"],
            "numeroDocumento": pago.get("numeroDocumento"),
            "importe": pago.get("importe"),
        }

    if origen_tipo == "Tarjeta devolución":
        cruce = repository.get_tarjeta_cruce_referencia(id_origen)
        if cruce is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {"tipo": "tarjeta_cruce", "idCruce": cruce["idCruce"], "idTarjeta": cruce["idTarjeta"], "importe": cruce.get("importe")}

    if origen_tipo == "Mercado Pago":
        movimiento = repository.get_mercado_libre_referencia(id_origen)
        if movimiento is None:
            return dict(_NO_DISPONIBLE_SIN_REGISTRO)
        return {
            "tipo": "tesoreria",
            "medio": "mercado-libre",
            "idMovimiento": movimiento["idMovimiento"],
            "fecha": movimiento.get("fecha"),
            "importe": movimiento.get("importe"),
        }

    # Incluye "Ret. IVA Granos" (dominio de Agricultura, fuera de alcance)
    # y cualquier valor de `Origen` no relevado (ej. "Valores propios",
    # "Tarjetas") — tratado como fuera de alcance por defecto per
    # data-model.md.
    return {"tipo": "fuera_de_alcance", "origenTipo": origen_tipo}
