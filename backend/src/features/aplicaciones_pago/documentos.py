"""Documentos pendientes de aplicación (019, data-model.md).

Compras: `importeTotal` sale de `vw_Cns_Total_Compra.GranTotal` (misma
vista que ya usa `vw_MovimientosCuenta_Base` para el saldo de
proveedores — no se reinventa la fórmula, research.md §1).

Ventas: no existe ninguna vista equivalente (research.md §2) — se reusa
el cálculo ya validado de `ventas_hacienda.repository.calcular_totales`
para Hacienda, y la columna `[Importe Neto a percibir]` ya calculada para
Granos.

En ambos casos, `saldoPendiente = importeTotal - SUM(ImporteAplicado)`
sobre las aplicaciones vigentes (`Anulada = 0`) de `AplicacionesPago`.
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import fetch_all
from src.features.ventas_hacienda.repository import calcular_totales, get_lineas_venta, get_venta_cabecera

TOLERANCIA_REDONDEO_APLICACION = 1.0


def _fecha(valor) -> date | None:
    if valor is None:
        return None
    return valor.date() if isinstance(valor, datetime) else valor


def _aplicado_de(tipo_documento: str, id_documento: int) -> float:
    fila = fetch_all(
        "SELECT SUM(ImporteAplicado) AS total FROM dbo.AplicacionesPago "
        "WHERE TipoDocumento = ? AND IdDocumentoAplicado = ? AND Anulada = 0",
        (tipo_documento, id_documento),
    )
    return float(fila[0]["total"] or 0) if fila else 0.0


def _compras_pendientes(id_contacto: int) -> list[dict]:
    filas = fetch_all(
        """
        SELECT c.IdDeuda AS idDocumento, c.Fecha AS fecha, c.[Nro Documento] AS numeroDocumento,
               tc.GranTotal AS importeTotal
        FROM dbo.Compras c
        JOIN dbo.vw_Cns_Total_Compra tc ON tc.IdDeuda = c.IdDeuda
        WHERE c.IdContacto = ?
        ORDER BY c.Fecha ASC, c.IdDeuda ASC
        """,
        (id_contacto,),
    )
    resultado = []
    for f in filas:
        importe_total = float(f["importeTotal"] or 0)
        aplicado = _aplicado_de("CompraDeuda", f["idDocumento"])
        saldo = round(importe_total - aplicado, 2)
        if saldo > TOLERANCIA_REDONDEO_APLICACION:
            resultado.append(
                {
                    "tipoDocumento": "CompraDeuda",
                    "idDocumento": f["idDocumento"],
                    "fecha": _fecha(f["fecha"]),
                    "numeroDocumento": f["numeroDocumento"],
                    "importeTotal": round(importe_total, 2),
                    "aplicado": round(aplicado, 2),
                    "saldoPendiente": saldo,
                }
            )
    return resultado


def _ventas_hacienda_pendientes(id_contacto: int) -> list[dict]:
    filas = fetch_all(
        "SELECT IdVenta AS idVenta, Fecha AS fecha, [Nro documento] AS numeroDocumento "
        "FROM dbo.[Venta Hacienda] WHERE IdConsignatario = ?",
        (id_contacto,),
    )
    resultado = []
    for f in filas:
        cabecera = get_venta_cabecera(f["idVenta"])
        lineas = get_lineas_venta(f["idVenta"])
        if cabecera is None or not lineas:
            continue
        importe_total = round(calcular_totales(lineas, cabecera)["importeTotal"], 2)
        aplicado = _aplicado_de("VentaHacienda", f["idVenta"])
        saldo = round(importe_total - aplicado, 2)
        if saldo > TOLERANCIA_REDONDEO_APLICACION:
            resultado.append(
                {
                    "tipoDocumento": "VentaHacienda",
                    "idDocumento": f["idVenta"],
                    "fecha": _fecha(f["fecha"]),
                    "numeroDocumento": f["numeroDocumento"],
                    "importeTotal": importe_total,
                    "aplicado": round(aplicado, 2),
                    "saldoPendiente": saldo,
                }
            )
    return resultado


def _ventas_granos_pendientes(id_contacto: int) -> list[dict]:
    filas = fetch_all(
        "SELECT IdVenta AS idVenta, Fecha AS fecha, [Nro Documento] AS numeroDocumento, "
        "[Importe Neto a percibir] AS importeTotal "
        "FROM dbo.[Venta Granos] WHERE IdConsignatario = ?",
        (id_contacto,),
    )
    resultado = []
    for f in filas:
        if f["importeTotal"] is None:
            continue
        importe_total = round(float(f["importeTotal"]), 2)
        aplicado = _aplicado_de("VentaGranos", f["idVenta"])
        saldo = round(importe_total - aplicado, 2)
        if saldo > TOLERANCIA_REDONDEO_APLICACION:
            resultado.append(
                {
                    "tipoDocumento": "VentaGranos",
                    "idDocumento": f["idVenta"],
                    "fecha": _fecha(f["fecha"]),
                    "numeroDocumento": f["numeroDocumento"],
                    "importeTotal": importe_total,
                    "aplicado": round(aplicado, 2),
                    "saldoPendiente": saldo,
                }
            )
    return resultado


def documentos_pendientes(id_contacto: int, tipo: str | None = None) -> list[dict]:
    """`tipo`: 'compra' | 'venta' | None (ambos). Ordenado por fecha
    ascendente (más viejo primero) — insumo directo de la sugerencia FIFO."""
    resultado: list[dict] = []
    if tipo in (None, "compra"):
        resultado.extend(_compras_pendientes(id_contacto))
    if tipo in (None, "venta"):
        resultado.extend(_ventas_hacienda_pendientes(id_contacto))
        resultado.extend(_ventas_granos_pendientes(id_contacto))
    resultado.sort(key=lambda d: d["fecha"] or date.min)
    return resultado
