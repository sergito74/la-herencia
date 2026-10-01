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

# Pedido explícito de Sergio (2026-09-29): los movimientos "LEY 25413"
# (impuesto al débito/crédito bancario) no son imputables a ningún contacto
# — son un costo bancario propio, no un pago a un tercero — así que nunca
# pasan por `atribuir_egreso`/`atribuir_ingreso` (que buscarían una compra o
# venta inexistente): se les asigna este rubro fijo directamente, en una
# cuenta/centro de costos aparte, para que aparezcan como su propia línea en
# el flujo de caja en vez de mezclarse con "Sin rubro asignado".
RUBRO_LEY_25413 = "Impuesto Ley 25413 (débitos/créditos bancarios)"
CENTRO_COSTO_LEY_25413 = "Impuestos bancarios"

# Mismo criterio que Ley 25413 (2026-09-29, revisión de casos "sin
# candidata" de la conciliación masiva): "RECAUDACION ARBA" es Ingresos
# Brutos retenido/percibido por el banco sobre el movimiento bancario en sí
# — no una compra a un proveedor — así que va al mismo centro de costos de
# impuestos bancarios, con su propio rubro para no perder de vista cuánto es
# cada impuesto.
RUBRO_ARBA_RECAUDACION = "Impuesto ARBA (recaudación bancaria)"

# 019-aplicacion-pagos-cobros, FR-009/FR-010: fecha de corte confirmada por
# Sergio. Antes de esta fecha no se exige aplicar retroactivamente — se
# distingue explícitamente de "pendiente de aplicar" (posterior al corte,
# sin aplicación) para no mezclar dos situaciones distintas bajo la misma
# etiqueta.
FECHA_CORTE_APLICACION = date(2015, 9, 1)
PENDIENTE_DE_APLICAR = "Pendiente de aplicar"
HISTORICO_SIN_APLICAR = "Histórico sin aplicar"


def _rubro_de_venta(tipo_documento: str, id_documento: int) -> str:
    if tipo_documento == "VentaHacienda":
        from src.features.ventas_hacienda.repository import get_lineas_venta

        lineas = get_lineas_venta(id_documento)
        tipos = {l.get("tipoHacienda") for l in lineas if l.get("tipoHacienda")}
        return f"Venta {tipos.pop()}" if len(tipos) == 1 else "Venta Hacienda (varias categorías)"
    if tipo_documento == "VentaGranos":
        fila = fetch_all("SELECT [Tipo de Grano] AS tipoGrano FROM dbo.[Venta Granos] WHERE IdVenta = ?", (id_documento,))
        tipo_grano = fila[0]["tipoGrano"] if fila else None
        return f"Venta {tipo_grano}" if tipo_grano else "Venta Granos"
    return SIN_RUBRO


# 031: vínculos de tesorería y backfill que apuntan a impuestos y sueldos.
CENTRO_COSTO_IMPUESTOS = "Impuestos"
CENTRO_COSTO_PERSONAL = "Personal"
RUBRO_SUELDOS = "Sueldos"


def _rubro_de_impuesto(id_impuesto: int, memo: dict) -> str:
    clave = ("Impuesto", id_impuesto)
    if clave not in memo:
        fila = fetch_all(
            "SELECT TOP 1 t.[Nombre Impuesto] AS nombre FROM dbo.Impuestos i "
            "JOIN dbo.[Tipo Impuesto] t ON t.IdTipoImpuesto = i.IdTipoImpuesto AND t.IdOrganismo = i.IdOrganismo "
            "WHERE i.IdImpuesto = ?", (id_impuesto,))
        memo[clave] = (fila[0]["nombre"] if fila and fila[0]["nombre"] else "Impuestos varios")
    return memo[clave]


def rubro_sin_aplicar(fecha) -> str:
    """Remanente o movimiento sin aplicación: histórico antes del corte, pendiente después."""
    return HISTORICO_SIN_APLICAR if _fecha(fecha) < FECHA_CORTE_APLICACION else PENDIENTE_DE_APLICAR


def partes_desde_aplicaciones(aplicaciones: list[dict], importe_movimiento: float, fecha, memo_compras: dict | None = None) -> list[dict] | None:
    """030 (aclaración del usuario): el movimiento se reparte según lo
    aplicado a cada documento — ya no va entero al rubro de mayor peso. Una
    compra con renglones de varios rubros se reparte en proporción al
    importe de cada renglón. Lo no aplicado va a Pendiente/Histórico. Si lo
    aplicado supera el movimiento, se escala: el banco manda. Devuelve
    partes `{rubro, centroCosto, importe, documentoAplicado}` con importe
    en valor absoluto; `None` si no hay aplicaciones (el llamador usa el
    fallback de 018 v2)."""
    if not aplicaciones:
        return None
    memo = memo_compras if memo_compras is not None else {}
    total_mov = round(abs(importe_movimiento), 2)
    aplicado = sum(float(a["importeAplicado"]) for a in aplicaciones)
    escala = total_mov / aplicado if aplicado > total_mov + 0.005 else 1.0

    partes: list[dict] = []
    for a in aplicaciones:
        importe = float(a["importeAplicado"]) * escala
        doc = {"tipo": a["tipoDocumento"], "id": a["idDocumentoAplicado"], "via": a.get("via", "aplicacion")}
        if a["tipoDocumento"] == "Impuesto":
            partes.append({"rubro": _rubro_de_impuesto(a["idDocumentoAplicado"], memo), "centroCosto": CENTRO_COSTO_IMPUESTOS,
                           "importe": importe, "documentoAplicado": doc})
        elif a["tipoDocumento"] == "Remuneracion":
            partes.append({"rubro": RUBRO_SUELDOS, "centroCosto": CENTRO_COSTO_PERSONAL, "importe": importe, "documentoAplicado": doc})
        elif a["tipoDocumento"] == "CompraDeuda":
            if a["idDocumentoAplicado"] not in memo:
                memo[a["idDocumentoAplicado"]] = _rubros_de_compra(a["idDocumentoAplicado"])
            grupos: dict[tuple, float] = defaultdict(float)
            for l in memo[a["idDocumentoAplicado"]]:
                grupos[(l["rubro"] or SIN_RUBRO, l["centroCosto"] or CENTRO_COSTO_SIN_ASIGNAR)] += max(float(l.get("peso") or 0), 0)
            if not grupos:
                grupos[(SIN_RUBRO, CENTRO_COSTO_SIN_ASIGNAR)] = 1.0
            total_peso = sum(grupos.values())
            for (rubro, centro), peso in grupos.items():
                share = peso / total_peso if total_peso > 0 else 1 / len(grupos)
                partes.append({"rubro": rubro, "centroCosto": centro, "importe": importe * share, "documentoAplicado": doc})
        else:
            partes.append({"rubro": _rubro_de_venta(a["tipoDocumento"], a["idDocumentoAplicado"]),
                           "centroCosto": None, "importe": importe, "documentoAplicado": doc})

    resto = total_mov - sum(p["importe"] for p in partes)
    if resto > 0.005:
        partes.append({"rubro": rubro_sin_aplicar(fecha), "centroCosto": None, "importe": resto, "documentoAplicado": None})

    for p in partes:
        p["importe"] = round(p["importe"], 2)
    # La última parte absorbe el redondeo: la suma es exactamente el movimiento.
    partes[-1]["importe"] = round(partes[-1]["importe"] + total_mov - sum(p["importe"] for p in partes), 2)
    return [p for p in partes if abs(p["importe"]) >= 0.005] or partes[-1:]


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
               cc.[Centro de costos] AS centroCosto,
               ISNULL(dc.Cantidad, 0) * ISNULL(dc.[Precio Unitario], 0) AS peso
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


def es_ley_25413(concepto: str | None) -> bool:
    return bool(concepto) and "25413" in concepto


def es_arba_recaudacion(concepto: str | None) -> bool:
    return bool(concepto) and "RECAUDACION ARBA" in concepto.upper()


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
