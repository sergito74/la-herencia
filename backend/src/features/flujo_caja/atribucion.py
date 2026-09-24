"""Atribuye cada movimiento bancario real (no interno) a un Rubro, para la
vista de flujo de caja por rubro (018 v2, pedido explícito de Sergio
2026-09-24: "quiero que se muestren los ingresos y egresos de dinero
reales" — nunca documentos de venta/compra, siempre el movimiento bancario).

Egresos: reusa el mismo patrón de matching exacto ya usado en
`tesoreria/matching.py` (IdContacto + fecha + importe, sin adivinar si hay
más de un candidato) contra `Compras`, y de ahí toma el Rubro/Centro de
Costos ya cargado en `Det_Compras`. Un movimiento sin match único queda
"Sin rubro asignado" — nunca se oculta (mismo principio que FR-009 de 018).

Ingresos: mismo patrón exacto, pero contra `Venta Hacienda`/`Venta Granos`
(no hay vista de deuda equivalente para ventas, así que se recalcula el
importe real de cada venta con las mismas fórmulas que ya usa el módulo de
ventas — `ventas_hacienda.repository.calcular_totales` — para no reinventar
ni aproximar la fórmula de comisión/IVA/retenciones)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from src.db.connection import fetch_all
from src.db.params import as_sql_datetime
from src.features.ventas_hacienda.repository import calcular_totales

SIN_RUBRO = "Sin rubro asignado"
CENTRO_COSTO_SIN_ASIGNAR = "Sin centro de costos"


def _fecha(valor) -> date | None:
    if valor is None:
        return None
    return valor.date() if isinstance(valor, datetime) else valor


def _redondear(valor: float) -> float:
    return round(float(valor), 2)


def _rubros_de_compra(id_compra: int) -> list[dict]:
    return fetch_all(
        """
        SELECT dc.IdRubro AS idRubro, r.Rubro AS rubro, dc.IdCentroCostos AS idCentroCostos,
               cc.[Centro de costos] AS centroCosto
        FROM dbo.Det_Compras dc
        LEFT JOIN dbo.Rubros r ON r.IdRubro = dc.IdRubro
        LEFT JOIN dbo.[Centro de costos] cc ON cc.IdCentro = dc.IdCentroCostos
        WHERE dc.IdCompra = ?
        """,
        (id_compra,),
    )


def _candidatas_compra(id_contacto: int, fecha: date, importe_abs: float) -> list[int]:
    filas = fetch_all(
        """
        SELECT cmp.IdDeuda AS idCompra
        FROM dbo.Compras cmp
        JOIN dbo.vw_MovimientosCuenta_Base v ON v.IdOrigen = cmp.IdDeuda AND v.Origen = 'Compras'
        WHERE cmp.IdContacto = ? AND v.Fecha = ? AND v.Deuda = ?
        """,
        (id_contacto, as_sql_datetime(fecha), importe_abs),
    )
    return [f["idCompra"] for f in filas]


def atribuir_egreso(id_contacto: int | None, fecha: date | None, importe_abs: float) -> dict:
    """`{rubro, centroCosto}` — SIN_RUBRO si no hay contacto, no hay match
    único, o la compra tiene renglones con más de un Rubro (no se reparte a
    ciegas)."""
    if id_contacto is None or fecha is None:
        return {"rubro": SIN_RUBRO, "centroCosto": CENTRO_COSTO_SIN_ASIGNAR}

    candidatas = _candidatas_compra(id_contacto, fecha, importe_abs)
    if len(candidatas) != 1:
        return {"rubro": SIN_RUBRO, "centroCosto": CENTRO_COSTO_SIN_ASIGNAR}

    lineas = _rubros_de_compra(candidatas[0])
    rubros = {l["rubro"] for l in lineas if l["rubro"]}
    centros = {l["centroCosto"] for l in lineas if l["centroCosto"]}
    return {
        "rubro": rubros.pop() if len(rubros) == 1 else "Compra con varios rubros",
        "centroCosto": centros.pop() if len(centros) == 1 else CENTRO_COSTO_SIN_ASIGNAR,
    }


def _ventas_hacienda_en_rango(fecha_desde: date, fecha_hasta: date) -> list[dict]:
    from src.features.ventas_hacienda.repository import get_lineas_venta, get_venta_cabecera

    filas = fetch_all(
        "SELECT IdVenta AS idVenta, Fecha AS fecha, IdConsignatario AS idConsignatario "
        "FROM dbo.[Venta Hacienda] WHERE Fecha BETWEEN ? AND ?",
        (as_sql_datetime(fecha_desde), as_sql_datetime(fecha_hasta)),
    )
    ventas = []
    for f in filas:
        cabecera = get_venta_cabecera(f["idVenta"])
        lineas = get_lineas_venta(f["idVenta"])
        if cabecera is None or not lineas:
            continue
        totales = calcular_totales(lineas, cabecera)
        tipos = {l.get("tipoHacienda") for l in lineas if l.get("tipoHacienda")}
        rubro = f"Venta {tipos.pop()}" if len(tipos) == 1 else "Venta Hacienda (varias categorías)"
        ventas.append(
            {
                "idContacto": f["idConsignatario"],
                "fecha": _fecha(f["fecha"]),
                "importe": _redondear(totales["importeTotal"]),
                "rubro": rubro,
            }
        )
    return ventas


def _ventas_granos_en_rango(fecha_desde: date, fecha_hasta: date) -> list[dict]:
    filas = fetch_all(
        "SELECT IdConsignatario AS idConsignatario, Fecha AS fecha, "
        "[Importe Neto a percibir] AS importe, [Tipo de Grano] AS tipoGrano "
        "FROM dbo.[Venta Granos] WHERE Fecha BETWEEN ? AND ?",
        (as_sql_datetime(fecha_desde), as_sql_datetime(fecha_hasta)),
    )
    return [
        {
            "idContacto": f["idConsignatario"],
            "fecha": _fecha(f["fecha"]),
            "importe": _redondear(f["importe"]) if f["importe"] is not None else None,
            "rubro": f"Venta {f['tipoGrano']}" if f["tipoGrano"] else "Venta Granos",
        }
        for f in filas
        if f["importe"] is not None
    ]


def construir_indice_ingresos(fecha_desde: date, fecha_hasta: date) -> dict[tuple, list[dict]]:
    """`{(idContacto, fecha, importe): [venta, ...]}` — se arma una vez por
    consulta y se reusa para atribuir todos los movimientos del rango
    (evita N ventas × M movimientos de round-trips a la base)."""
    indice: dict[tuple, list[dict]] = defaultdict(list)
    for venta in [*_ventas_hacienda_en_rango(fecha_desde, fecha_hasta), *_ventas_granos_en_rango(fecha_desde, fecha_hasta)]:
        if venta["fecha"] is None or venta["importe"] is None:
            continue
        indice[(venta["idContacto"], venta["fecha"], venta["importe"])].append(venta)
    return indice


def atribuir_ingreso(indice: dict[tuple, list[dict]], id_contacto: int | None, fecha: date | None, importe_abs: float) -> dict:
    if id_contacto is None or fecha is None:
        return {"rubro": SIN_RUBRO, "centroCosto": None}
    candidatas = indice.get((id_contacto, fecha, importe_abs), [])
    if len(candidatas) != 1:
        return {"rubro": SIN_RUBRO, "centroCosto": None}
    return {"rubro": candidatas[0]["rubro"], "centroCosto": None}
