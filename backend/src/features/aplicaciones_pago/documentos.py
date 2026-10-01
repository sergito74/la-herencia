"""Documentos pendientes de aplicación (019, data-model.md).

Compras: `importeTotal` sale de `vw_Cns_Total_Compra.GranTotal` (misma
vista que ya usa `vw_MovimientosCuenta_Base` para el saldo de
proveedores — no se reinventa la fórmula, research.md §1).

Ventas: no existe ninguna vista equivalente (research.md §2) — se reusa
el cálculo ya validado de `ventas_hacienda.repository.calcular_totales`
para Hacienda, y la columna `[Importe Neto a percibir]` ya calculada para
Granos.

En ambos casos, `saldoPendiente = importeTotal - pagado`. Desde 031 lo
pagado sale de la fuente unificada de vínculos (aplicaciones, consumos de
tarjeta, cheques propios, tesorería y backfill, sin contar dos veces) y
los documentos en dólares se expresan en pesos con el TC de la factura.
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import fetch_all
from src.features.vinculos import fuente
from src.features.ventas_hacienda.repository import calcular_totales, get_lineas_venta, get_venta_cabecera

TOLERANCIA_REDONDEO_APLICACION = 1.0


def _fecha(valor) -> date | None:
    if valor is None:
        return None
    return valor.date() if isinstance(valor, datetime) else valor


def _aplicado_de(tipo_documento: str, id_documento: int) -> float:
    """Pagado del documento contando todas las vías (031)."""
    return fuente.pagado_de_documentos([(tipo_documento, id_documento)])[(tipo_documento, id_documento)]


def _pagados(tipo_documento: str, ids: list[int]) -> dict[int, float]:
    pagado = fuente.pagado_de_documentos([(tipo_documento, i) for i in ids])
    return {i: pagado[(tipo_documento, i)] for i in ids}


def _compras_pendientes(id_contacto: int) -> list[dict]:
    filas = fetch_all(
        """
        SELECT c.IdDeuda AS idDocumento, c.Fecha AS fecha, c.[Nro Documento] AS numeroDocumento,
               tc.GranTotal AS importeTotal, c.Moneda AS moneda, c.[Tipo de Cambio] AS tc
        FROM dbo.Compras c
        JOIN dbo.vw_Cns_Total_Compra tc ON tc.IdDeuda = c.IdDeuda
        WHERE c.IdContacto = ?
        ORDER BY c.Fecha ASC, c.IdDeuda ASC
        """,
        (id_contacto,),
    )
    resultado = []
    pagados = _pagados("CompraDeuda", [f["idDocumento"] for f in filas])
    for f in filas:
        importe_total = float(f["importeTotal"] or 0)
        if f["moneda"] == "Dolares" and (f["tc"] or 0) > 1:
            importe_total *= float(f["tc"])
        aplicado = pagados[f["idDocumento"]]
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
    pagados = _pagados("VentaHacienda", [f["idVenta"] for f in filas])
    for f in filas:
        cabecera = get_venta_cabecera(f["idVenta"])
        lineas = get_lineas_venta(f["idVenta"])
        if cabecera is None or not lineas:
            continue
        importe_total = round(calcular_totales(lineas, cabecera)["importeTotal"], 2)
        aplicado = pagados[f["idVenta"]]
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
    pagados = _pagados("VentaGranos", [f["idVenta"] for f in filas])
    for f in filas:
        if f["importeTotal"] is None:
            continue
        importe_total = round(float(f["importeTotal"]), 2)
        aplicado = pagados[f["idVenta"]]
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
