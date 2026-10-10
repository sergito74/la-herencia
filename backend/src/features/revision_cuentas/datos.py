"""Carga de solo lectura de los movimientos de una cuenta — 036 (T005).

Todo sale de `dbo.vw_MovimientosCuenta_Base` (saldo = crédito − deuda). Este módulo no escribe nada.
`ORIGENES_*` y `sentido_de_cuenta` son puros: el detector los usa para armar los dos lados de una cuenta.
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import fetch_all, fetch_one

# Orígenes de la vista que son un documento de venta: en ellos el crédito es lo que nos deben (cuentas de clientes).
ORIGENES_VENTA = frozenset({"Venta Granos", "Venta Hacienda"})

# Orígenes que son documentos de compra o de gasto: la deuda es lo que debemos y el crédito es una nota que la reduce.
ORIGENES_DOCUMENTO = frozenset({
    "Compras", "Alquileres", "Impuestos", "Remuneraciones", "Ajuste Interno",
    "Tarjeta consumo", "Tarjeta cargo", "Tarjeta impuesto", "Tarjeta sin imputar",
})

# Traducción del Origen de la vista al Medio de RevisionPagosSinFactura (data-model.md). Lo que no figura se normaliza.
MEDIO_POR_ORIGEN = {
    "Banco Nacion": "bna",
    "Galicia": "galicia",
    "Pagos efectivo": "efectivo",
    "Tarjetas": "tarjetas",
    "Retenciones": "retencion",
    "Cobros Valores Recibidos": "valores",
    "Pagos Valores Recibidos": "valores",
    "Venta Granos": "venta-granos",
}


def medio_de_origen(origen: str) -> str:
    """Medio de una marca: la traducción del modelo de datos o el nombre normalizado (minúsculas y guiones)."""
    if origen in MEDIO_POR_ORIGEN:
        return MEDIO_POR_ORIGEN[origen]
    return "-".join((origen or "otro").lower().replace("ó", "o").replace("í", "i").split())


def _dia(valor) -> date:
    return valor.date() if isinstance(valor, datetime) else valor


def movimientos_de_cuenta(id_contacto: int, hasta: date | None = None) -> list[dict]:
    """Movimientos de la cuenta en orden de fecha (hasta una fecha de corte inclusive, si se indica)."""
    filtro, params = "", [id_contacto]
    if hasta is not None:
        filtro = " AND Fecha < ?"
        params.append(_dia_siguiente(hasta))
    filas = fetch_all(
        "SELECT Fecha, Documento, [Nro Documento] AS nro, Deuda, Credito, Origen, IdOrigen "
        "FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?" + filtro + " ORDER BY Fecha, Origen, IdOrigen", tuple(params))
    return [{"fecha": _dia(f["Fecha"]), "documento": f["Documento"], "nro": f["nro"],
             "deuda": round(float(f["Deuda"] or 0), 2), "credito": round(float(f["Credito"] or 0), 2),
             "origen": f["Origen"], "idOrigen": int(f["IdOrigen"]) if f["IdOrigen"] is not None else 0} for f in filas]


def _dia_siguiente(d: date) -> datetime:
    """El día siguiente a medianoche: `Fecha < esa fecha` incluye todo el día de corte."""
    from datetime import timedelta
    return datetime.combine(d + timedelta(days=1), datetime.min.time())


def saldo_al_corte(id_contacto: int, corte: date) -> float:
    """Saldo (crédito menos deuda) de una cuenta hasta el día de corte inclusive."""
    f = fetch_one("SELECT SUM(Credito) - SUM(Deuda) AS s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ? AND Fecha < ?",
                  (id_contacto, _dia_siguiente(corte)))
    return round(float(f["s"] or 0), 2) if f else 0.0


def saldos_al_corte(corte: date) -> dict[int, float]:
    """Saldo al corte de todas las cuentas con movimientos, en una sola consulta."""
    filas = fetch_all("SELECT IdContacto AS i, SUM(Credito) - SUM(Deuda) AS s FROM dbo.vw_MovimientosCuenta_Base "
                      "WHERE IdContacto IS NOT NULL AND Fecha < ? GROUP BY IdContacto", (_dia_siguiente(corte),))
    return {int(f["i"]): round(float(f["s"] or 0), 2) for f in filas}


def actividad_de_cuentas(hasta: date | None = None) -> dict[int, dict]:
    """Por cuenta: razón social, cantidad de movimientos y volumen en pesos (suma de deuda y crédito, como el FIFO)."""
    filtro, params = "", ()
    if hasta is not None:
        filtro, params = " AND Fecha < ?", (_dia_siguiente(hasta),)
    filas = fetch_all(
        "SELECT IdContacto AS i, MAX([Razon Social]) AS n, COUNT(*) AS m, SUM(Deuda) + SUM(Credito) AS v "
        "FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto IS NOT NULL" + filtro + " GROUP BY IdContacto", params)
    return {int(f["i"]): {"razonSocial": f["n"], "movimientos": int(f["m"]), "volumen": round(float(f["v"] or 0), 2)} for f in filas}


def razon_social(id_contacto: int) -> str | None:
    f = fetch_one("SELECT [Razon Social] AS n FROM dbo.Contactos WHERE IdContacto = ?", (id_contacto,))
    return f["n"] if f else None


def sentido_de_cuenta(movimientos: list[dict]) -> str:
    """`proveedor`, `cliente` o `mixta` según los documentos que tiene la cuenta (research D1, clientes y mixtas)."""
    con_compra = any(m["origen"] in ORIGENES_DOCUMENTO and m["deuda"] > 0 for m in movimientos)
    con_venta = any(m["origen"] in ORIGENES_VENTA and m["credito"] > 0 for m in movimientos)
    if con_compra and con_venta:
        return "mixta"
    return "cliente" if con_venta else "proveedor"


def imputaciones_de_cuentas(ids: list[int] | None = None, hasta: date | None = None) -> dict[int, dict]:
    """Por cuenta (facturas en pesos): lo facturado, lo imputado con pagos y lo cubierto por vínculos de tarjeta.

    Sirve para medir si las imputaciones están sanas (criterio C5). No incluye las facturas en dólares (se revisan en la cola F).
    """
    filtro = ""
    params: tuple = ()
    if ids:
        filtro = " AND c.IdContacto IN (" + ",".join("?" * len(ids)) + ")"
        params = tuple(ids)
    if hasta is not None:  # solo las facturas hasta el corte, igual que el saldo
        filtro += " AND c.Fecha < ?"
        params += (_dia_siguiente(hasta),)
    facturado = fetch_all(
        "SELECT c.IdContacto AS i, SUM(CASE WHEN v.ImporteDocumento > 0 THEN v.ImporteDocumento ELSE 0 END) AS s, COUNT(*) AS n "
        "FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda "
        "WHERE c.Moneda <> 'Dolares'" + filtro + " GROUP BY c.IdContacto", params)
    aplicado = fetch_all(
        "SELECT c.IdContacto AS i, SUM(a.ImporteAplicado) AS s FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
        "WHERE a.Anulada = 0 AND a.TipoDocumento = 'CompraDeuda' AND c.Moneda <> 'Dolares'" + filtro + " GROUP BY c.IdContacto", params)
    # Solo lo imputado a facturas (positivo): una nota de crédito imputada a la línea baja lo que cobró la tarjeta, no deja la factura sin imputar
    tarjeta = fetch_all(
        "SELECT c.IdContacto AS i, SUM(CASE WHEN t.ImporteImputado > 0 THEN t.ImporteImputado ELSE 0 END) AS s "
        "FROM dbo.Tarjetas_Resumenes_Lineas_Compras t JOIN dbo.Compras c ON c.IdDeuda = t.IdCompra "
        "WHERE c.Moneda <> 'Dolares'" + filtro + " GROUP BY c.IdContacto", params)
    # Mercado Libre y valores propios no generan AplicacionesPago (el FIFO solo lee banco, efectivo y tarjeta): su vínculo vive en la conciliación de tesorería
    # (con o sin documento). Los ajustes internos de crédito también cubren facturas sin pasar por AplicacionesPago.
    f_ids = " AND IdContacto IN (" + ",".join("?" * len(ids)) + ")" if ids else ""
    p_ids = tuple(ids) if ids else ()
    f_hasta = " AND Fecha < ?" if hasta is not None else ""
    p_hasta = (_dia_siguiente(hasta),) if hasta is not None else ()
    f_c = " AND ct.IdContacto IN (" + ",".join("?" * len(ids)) + ")" if ids else ""
    f_cd = " AND c.Fecha < ?" if hasta is not None else ""
    f_ml = " AND ml.Fecha < ?" if hasta is not None else ""
    # la fecha que cuenta es la del documento o la del movimiento, no la de la conciliación (que se carga después)
    tesoreria = fetch_all(
        "SELECT ct.IdContacto AS i, SUM(ct.Importe) AS s FROM dbo.ConciliacionesTesoreria ct JOIN dbo.Compras c ON c.IdDeuda = ct.IdOrigenDocumento "
        "WHERE ct.Medio IN ('mercado-libre', 'valores-propios') AND ct.TipoOrigenDocumento = 'Compras'" + f_c + f_cd + " GROUP BY ct.IdContacto", p_ids + p_hasta)
    tesoreria += fetch_all(
        "SELECT ct.IdContacto AS i, SUM(ct.Importe) AS s FROM dbo.ConciliacionesTesoreria ct JOIN dbo.[Movimientos Mercado Libre] ml ON ml.IdMovimiento = ct.IdMovimiento "
        "WHERE ct.Medio = 'mercado-libre' AND ct.TipoOrigenDocumento IS NULL" + f_c + f_ml + " GROUP BY ct.IdContacto", p_ids + p_hasta)
    # los contratos de arrendamiento entran como crédito en la cuenta (neto de la retención) y compensan facturas sin pasar por AplicacionesPago
    tesoreria += fetch_all(
        "SELECT IdContacto AS i, SUM([Importe total del contrato] - ISNULL([Retencion Ganancias], 0)) AS s FROM dbo.Alquileres WHERE 1 = 1" + f_ids + f_hasta + " GROUP BY IdContacto", p_ids + p_hasta)
    tesoreria += fetch_all(
        "SELECT IdContacto AS i, SUM(Importe) AS s FROM dbo.AjustesCuentaCorriente WHERE Lado = 'Credito'" + f_ids + f_hasta + " GROUP BY IdContacto", p_ids + p_hasta)
    r: dict[int, dict] = {int(f["i"]): {"facturado": round(float(f["s"] or 0), 2), "facturas": int(f["n"]), "aplicado": 0.0, "tarjeta": 0.0} for f in facturado}
    for f in aplicado:
        r.setdefault(int(f["i"]), {"facturado": 0.0, "facturas": 0, "aplicado": 0.0, "tarjeta": 0.0})["aplicado"] = round(float(f["s"] or 0), 2)
    for f in tarjeta:
        r.setdefault(int(f["i"]), {"facturado": 0.0, "facturas": 0, "aplicado": 0.0, "tarjeta": 0.0})["tarjeta"] = round(float(f["s"] or 0), 2)
    for f in tesoreria:
        d = r.setdefault(int(f["i"]), {"facturado": 0.0, "facturas": 0, "aplicado": 0.0, "tarjeta": 0.0})
        d["aplicado"] = round(d["aplicado"] + float(f["s"] or 0), 2)
    return r


def retenciones_sin_certificado(id_contacto: int | None = None) -> dict[int, int]:
    """Retenciones sin número de certificado, por cuenta (o solo de una)."""
    filtro, params = ("", ()) if id_contacto is None else (" AND IdContacto = ?", (id_contacto,))
    filas = fetch_all("SELECT IdContacto AS i, COUNT(*) AS n FROM dbo.Retenciones WHERE ([Numero Certificado] IS NULL OR LTRIM(RTRIM([Numero Certificado])) = '')"
                      + filtro + " GROUP BY IdContacto", params)
    return {int(f["i"]): int(f["n"]) for f in filas}


def movimientos_por_cuenta(hasta: date | None = None, ids: list[int] | None = None) -> dict[int, list[dict]]:
    """Movimientos de varias cuentas (todas si `ids` es None) en una sola consulta, hasta una fecha de corte inclusive."""
    condiciones, params = ["IdContacto IS NOT NULL"], []
    if hasta is not None:
        condiciones.append("Fecha < ?")
        params.append(_dia_siguiente(hasta))
    if ids:
        condiciones.append("IdContacto IN (" + ",".join("?" * len(ids)) + ")")
        params.extend(ids)
    filas = fetch_all("SELECT IdContacto AS i, Fecha, Documento, [Nro Documento] AS nro, Deuda, Credito, Origen, IdOrigen "
                      "FROM dbo.vw_MovimientosCuenta_Base WHERE " + " AND ".join(condiciones) + " ORDER BY IdContacto, Fecha, Origen, IdOrigen", tuple(params))
    salida: dict[int, list[dict]] = {}
    for f in filas:
        salida.setdefault(int(f["i"]), []).append({
            "fecha": _dia(f["Fecha"]), "documento": f["Documento"], "nro": f["nro"], "deuda": round(float(f["Deuda"] or 0), 2),
            "credito": round(float(f["Credito"] or 0), 2), "origen": f["Origen"], "idOrigen": int(f["IdOrigen"]) if f["IdOrigen"] is not None else 0})
    return salida


def tarjetas_duplicadas() -> dict[int, dict]:
    """Imputaciones de origen `tarjetas` que sobran: la factura ya está cubierta por los otros pagos y quitarlas deja su importe exacto.

    Es el caso de Jauregui (corrección 42 del 09/10/2026: cinco imputaciones de tarjeta pegadas a una factura que ya estaba pagada). Las
    imputaciones de tarjeta que reflejan el vínculo del resumen sobre la misma factura NO entran. Por cuenta: ids, cantidad e importe.
    """
    filas = fetch_all(
        "WITH f AS (SELECT c.IdDeuda, c.IdContacto, v.ImporteDocumento AS imp, "
        " ISNULL((SELECT SUM(a.ImporteAplicado) FROM dbo.AplicacionesPago a WHERE a.Anulada = 0 AND a.IdDocumentoAplicado = c.IdDeuda), 0) AS ap, "
        " ISNULL((SELECT SUM(a.ImporteAplicado) FROM dbo.AplicacionesPago a WHERE a.Anulada = 0 AND a.OrigenMovimiento = 'tarjetas' AND a.IdDocumentoAplicado = c.IdDeuda), 0) AS apt "
        " FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda WHERE c.Moneda <> 'Dolares') "
        "SELECT f.IdContacto AS i, a.IdAplicacion AS ida, a.ImporteAplicado AS importe FROM f "
        "JOIN dbo.AplicacionesPago a ON a.IdDocumentoAplicado = f.IdDeuda AND a.Anulada = 0 AND a.OrigenMovimiento = 'tarjetas' "
        "WHERE f.apt > 0 AND f.ap - f.imp > 1 AND ABS((f.ap - f.apt) - f.imp) <= 1", ())
    salida: dict[int, dict] = {}
    for f in filas:
        d = salida.setdefault(int(f["i"]), {"ids": [], "importe": 0.0})
        d["ids"].append(int(f["ida"]))
        d["importe"] = round(d["importe"] + float(f["importe"]), 2)
    for d in salida.values():
        d["ids"] = sorted(d["ids"])
    return salida
