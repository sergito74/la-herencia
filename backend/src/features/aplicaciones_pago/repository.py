"""CRUD de `AplicacionesPago` (019). Las aplicaciones son inmutables: se
insertan o se anulan, nunca se editan (FR-005). El estado de un
documento/movimiento se calcula siempre en el momento de la consulta
(FR-007/SC-004), nunca se guarda como campo fijo."""

from __future__ import annotations

from src.db.connection import execute_write, execute_write_transaction, fetch_all
from src.features.aplicaciones_pago.documentos import TOLERANCIA_REDONDEO_APLICACION, _aplicado_de
from src.features.aplicaciones_pago.sugerencia import _contacto_e_importe


def _importe_total_documento(tipo_documento: str, id_documento: int) -> float:
    if tipo_documento == "CompraDeuda":
        fila = fetch_all(
            "SELECT GranTotal AS total FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda = ?", (id_documento,)
        )
        return float(fila[0]["total"]) if fila else 0.0
    if tipo_documento == "VentaHacienda":
        from src.features.ventas_hacienda.repository import calcular_totales, get_lineas_venta, get_venta_cabecera

        cabecera = get_venta_cabecera(id_documento)
        lineas = get_lineas_venta(id_documento)
        if cabecera is None or not lineas:
            return 0.0
        return round(calcular_totales(lineas, cabecera)["importeTotal"], 2)
    if tipo_documento == "VentaGranos":
        fila = fetch_all(
            "SELECT [Importe Neto a percibir] AS total FROM dbo.[Venta Granos] WHERE IdVenta = ?", (id_documento,)
        )
        return float(fila[0]["total"] or 0) if fila else 0.0
    raise ValueError(f"TipoDocumento desconocido: {tipo_documento}")


def estado_documento(tipo_documento: str, id_documento: int) -> dict:
    importe_total = round(_importe_total_documento(tipo_documento, id_documento), 2)
    aplicado = round(_aplicado_de(tipo_documento, id_documento), 2)
    saldo = round(importe_total - aplicado, 2)
    if aplicado <= TOLERANCIA_REDONDEO_APLICACION:
        estado = "Pendiente"
    elif saldo <= TOLERANCIA_REDONDEO_APLICACION:
        estado = "Total"
    else:
        estado = "Parcial"

    historial = fetch_all(
        "SELECT IdAplicacion AS idAplicacion, OrigenMovimiento AS origenMovimiento, "
        "IdMovimientoOrigen AS idMovimientoOrigen, ImporteAplicado AS importeAplicado, "
        "Fecha AS fecha, Usuario AS usuario, Anulada AS anulada, MotivoAnulacion AS motivoAnulacion, "
        "UsuarioAnulacion AS usuarioAnulacion, FechaAnulacion AS fechaAnulacion "
        "FROM dbo.AplicacionesPago WHERE TipoDocumento = ? AND IdDocumentoAplicado = ? ORDER BY Fecha ASC",
        (tipo_documento, id_documento),
    )
    return {
        "importeTotal": importe_total,
        "aplicado": aplicado,
        "saldoPendiente": saldo,
        "estado": estado,
        "aplicaciones": historial,
    }


def aplicaciones_vigentes_de_movimiento(origen_movimiento: str, id_movimiento_origen: int) -> list[dict]:
    return fetch_all(
        "SELECT IdAplicacion AS idAplicacion, TipoDocumento AS tipoDocumento, "
        "IdDocumentoAplicado AS idDocumentoAplicado, ImporteAplicado AS importeAplicado "
        "FROM dbo.AplicacionesPago WHERE OrigenMovimiento = ? AND IdMovimientoOrigen = ? AND Anulada = 0",
        (origen_movimiento, id_movimiento_origen),
    )


def estado_movimiento(origen_movimiento: str, id_movimiento_origen: int) -> dict:
    _id_contacto, importe = _contacto_e_importe(origen_movimiento, id_movimiento_origen)
    importe_abs = round(abs(importe), 2) if importe is not None else 0.0
    aplicaciones = aplicaciones_vigentes_de_movimiento(origen_movimiento, id_movimiento_origen)
    aplicado = round(sum(float(a["importeAplicado"]) for a in aplicaciones), 2)
    return {
        "importe": importe_abs,
        "aplicado": aplicado,
        "saldoSinAplicar": round(importe_abs - aplicado, 2),
        "aplicaciones": aplicaciones,
    }


def insertar_aplicaciones(
    origen_movimiento: str, id_movimiento_origen: int, aplicaciones: list[dict], usuario: str
) -> list[int]:
    """Valida que ningún documento ni el movimiento queden sobre-aplicados
    (FR-008) y, si todo cierra, inserta una fila por cada entrada de
    `aplicaciones` en una única transacción."""
    if not aplicaciones:
        raise ValueError("insertar_aplicaciones requiere al menos una aplicación")

    _id_contacto, importe_movimiento = _contacto_e_importe(origen_movimiento, id_movimiento_origen)
    if importe_movimiento is None:
        raise ValueError(f"Movimiento {origen_movimiento}/{id_movimiento_origen} no encontrado")
    importe_movimiento_abs = round(abs(importe_movimiento), 2)

    ya_aplicado_movimiento = sum(
        float(a["importeAplicado"]) for a in aplicaciones_vigentes_de_movimiento(origen_movimiento, id_movimiento_origen)
    )
    nuevo_total_movimiento = ya_aplicado_movimiento + sum(a["importeAplicado"] for a in aplicaciones)
    if nuevo_total_movimiento - importe_movimiento_abs > TOLERANCIA_REDONDEO_APLICACION:
        raise ValueError(
            f"El movimiento quedaría sobre-aplicado: {nuevo_total_movimiento:.2f} > {importe_movimiento_abs:.2f}"
        )

    for aplicacion in aplicaciones:
        importe_total_doc = _importe_total_documento(aplicacion["tipoDocumento"], aplicacion["idDocumento"])
        ya_aplicado_doc = _aplicado_de(aplicacion["tipoDocumento"], aplicacion["idDocumento"])
        if ya_aplicado_doc + aplicacion["importeAplicado"] - importe_total_doc > TOLERANCIA_REDONDEO_APLICACION:
            raise ValueError(
                f"El documento {aplicacion['tipoDocumento']}/{aplicacion['idDocumento']} quedaría sobre-aplicado"
            )

    statements = [
        (
            "INSERT INTO dbo.AplicacionesPago "
            "(OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, Usuario) "
            "OUTPUT INSERTED.IdAplicacion VALUES (?, ?, ?, ?, ?, ?)",
            (
                origen_movimiento,
                id_movimiento_origen,
                aplicacion["tipoDocumento"],
                aplicacion["idDocumento"],
                aplicacion["importeAplicado"],
                usuario,
            ),
        )
        for aplicacion in aplicaciones
    ]
    return execute_write_transaction(statements)


def anular_aplicacion(id_aplicacion: int, motivo: str, usuario: str) -> None:
    n = execute_write(
        "UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, "
        "FechaAnulacion = SYSUTCDATETIME() WHERE IdAplicacion = ? AND Anulada = 0",
        (motivo, usuario, id_aplicacion),
    )
    if n == 0:
        raise ValueError(f"Aplicación {id_aplicacion} no existe o ya estaba anulada")
