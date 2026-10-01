"""Carga en bloque de las cinco vías de vínculos y de los datos de
movimientos y documentos que necesitan las reglas (031, research R3/R8).
Solo lectura. Las reglas viven en `cadenas.py`."""

from __future__ import annotations

from collections import defaultdict

from src.db.connection import fetch_all
from src.features.vinculos import cadenas

_TIPOS_DOC = ("CompraDeuda", "VentaHacienda", "VentaGranos", "Impuesto", "Remuneracion")


def _filtro_docs(columna_tipo: str | None, columna_id: str, docs: list[tuple] | None, tipos_sql: dict | None = None):
    """WHERE opcional para limitar la carga a unos documentos (validación
    al guardar y saldo de un contacto). `tipos_sql` traduce el tipo interno
    al valor guardado en la tabla (ej. CompraDeuda → 'Compras')."""
    if docs is None:
        return "", ()
    condiciones, params = [], []
    for tipo, id_doc in docs:
        valor_tipo = (tipos_sql or {}).get(tipo, tipo)
        if columna_tipo:
            condiciones.append(f"({columna_tipo} = ? AND {columna_id} = ?)")
            params += [valor_tipo, id_doc]
        elif tipo == "CompraDeuda":
            condiciones.append(f"{columna_id} = ?")
            params.append(id_doc)
    if not condiciones:
        return " AND 1 = 0", ()
    return " AND (" + " OR ".join(condiciones) + ")", tuple(params)


def _aplicaciones(docs=None) -> list[dict]:
    w, p = _filtro_docs("TipoDocumento", "IdDocumentoAplicado", docs)
    return fetch_all(
        "SELECT IdAplicacion AS idAplicacion, OrigenMovimiento AS origenMovimiento, IdMovimientoOrigen AS idMovimiento, "
        "TipoDocumento AS tipoDocumento, IdDocumentoAplicado AS idDocumento, ImporteAplicado AS importe, "
        "Origen AS origenCarga, Fecha AS fechaCarga FROM dbo.AplicacionesPago WHERE Anulada = 0" + w, p)


def _lineas_compras(docs=None) -> list[dict]:
    w, p = _filtro_docs(None, "IdCompra", docs)
    return fetch_all(
        "SELECT IdVinculo AS idVinculo, IdLineaConsumo AS idLinea, IdCompra AS idCompra, ImporteImputado AS importe "
        "FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdCompra IS NOT NULL" + w, p)


def _tesoreria(docs=None) -> list[dict]:
    inverso = {v: k for k, v in cadenas.TIPO_TESORERIA.items()}
    w, p = _filtro_docs("TipoOrigenDocumento", "IdOrigenDocumento", docs, inverso)
    return fetch_all(
        "SELECT IdConciliacion AS idConciliacion, Medio AS medio, IdMovimiento AS idMovimiento, "
        "TipoOrigenDocumento AS tipoDocumento, IdOrigenDocumento AS idDocumento, Importe AS importe "
        "FROM dbo.ConciliacionesTesoreria WHERE TipoOrigenDocumento IS NOT NULL AND IdOrigenDocumento IS NOT NULL" + w, p)


def _backfill(docs=None) -> list[dict]:
    if docs is not None and not any(t == "Impuesto" for t, _ in docs):
        return []
    ids = [i for t, i in (docs or []) if t == "Impuesto"]
    w = f" WHERE IdImpuesto IN ({','.join('?' * len(ids))})" if docs is not None else ""
    try:
        return fetch_all("SELECT IdVinculo AS idVinculo, Medio AS medio, IdMovimiento AS idMovimiento, "
                         "IdImpuesto AS idImpuesto, Importe AS importe FROM dbo.BackfillImpuestosVinculos" + w, tuple(ids))
    except Exception:  # la tabla la crea 029; sin ella no hay vínculos de esta vía
        return []


def _lineas() -> dict[int, dict]:
    return {f["idLinea"]: f for f in fetch_all(
        "SELECT l.IdLineaConsumo AS idLinea, l.IdResumen AS idResumen, l.FechaCompra AS fecha, l.Importe AS importe, "
        "l.IdContacto AS idContacto, l.Detalle AS detalle, r.ResumenCodigo AS resumen, t.TarjetaNombre AS tarjeta "
        "FROM dbo.Tarjetas_Resumenes_Lineas l LEFT JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen "
        "LEFT JOIN dbo.Tarjetas t ON t.IdTarjeta = r.IdTarjeta")}


def _pagos_resumen() -> list[dict]:
    return [dict(f, origen=(f["origen"] or "").lower()) for f in fetch_all(
        "SELECT IdPago AS idPago, IdResumen AS idResumen, Fecha AS fecha, Importe AS importe, Origen AS origen, "
        "IdMovimientoOrigen AS idMovimiento FROM dbo.Tarjetas_Resumenes_Pagos")]


def _valores() -> list[dict]:
    return fetch_all("SELECT IdValor AS idValor, CAST([Numero cheque] AS bigint) AS numero, Importe AS importe, "
                     "[Fecha emision] AS fechaEmision FROM dbo.[Valores propios]")


def movimientos_bancarios() -> dict[tuple, dict]:
    resultado: dict[tuple, dict] = {}
    for f in fetch_all("SELECT IdMovimientoBNA AS id, [Fecha / Hora Mov#] AS fecha, Importe AS importe, Concepto AS concepto, "
                       "IdContacto AS idContacto FROM dbo.[Movimientos BNA]"):
        resultado[("bna", f["id"])] = f
    for f in fetch_all("SELECT IdMovimiento AS id, Fecha AS fecha, ISNULL([Créditos],0) - ISNULL([Débitos],0) AS importe, "
                       "[Descripción] AS concepto, IdContacto AS idContacto FROM dbo.[Movimientos Galicia]"):
        resultado[("galicia", f["id"])] = f
    return resultado


def importes_efectivo() -> dict[tuple, float]:
    """Importe de los pagos en efectivo, para la regla de us$ contra pesos."""
    return {("efectivo", f["id"]): -abs(float(f["importe"] or 0))
            for f in fetch_all("SELECT IdPagoEfectivo AS id, [Importe imputado] AS importe FROM dbo.[Pagos efectivo]")}


def fechas_otros_medios(lineas: dict) -> dict[tuple, object]:
    """Fecha de los medios que no son banco, para detectar fechas incoherentes."""
    fechas = {("tarjetas", i): l["fecha"] for i, l in lineas.items()}
    for f in fetch_all("SELECT IdPagoEfectivo AS id, Fecha AS fecha FROM dbo.[Pagos efectivo]"):
        fechas[("efectivo", f["id"])] = f["fecha"]
    for f in fetch_all("SELECT IdValor AS id, [Fecha Emision] AS fecha FROM dbo.[Valores Recibidos]"):
        fechas[("valores-recibidos", f["id"])] = f["fecha"]
    return fechas


def documentos(claves: set[tuple] | None = None) -> dict[tuple, dict]:
    """Fecha, contacto, moneda y total en pesos de cada documento. Venta
    Hacienda no tiene total en una vista: se calcula solo para las ventas
    pedidas (las que tienen vínculos), con la fórmula del módulo de ventas."""
    from src.features.remuneraciones.repository import _IMPORTE_SQL
    from src.features.ventas_hacienda.repository import calcular_totales, get_lineas_venta, get_venta_cabecera

    docs: dict[tuple, dict] = {}
    for f in fetch_all("SELECT c.IdDeuda AS id, c.Fecha AS fecha, c.IdContacto AS idContacto, c.Moneda AS moneda, "
                       "c.[Tipo de Cambio] AS tc, t.GranTotal AS total, CONCAT(c.[Tipo documento], ' ', c.[Nro Documento]) AS numero "
                       "FROM dbo.Compras c "
                       "JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda = c.IdDeuda"):
        total = abs(float(f["total"] or 0))
        if f["moneda"] == "Dolares" and (f["tc"] or 0) > 1:
            total *= float(f["tc"])
        docs[("CompraDeuda", f["id"])] = {"fecha": f["fecha"], "idContacto": f["idContacto"], "moneda": f["moneda"],
                                          "tc": f["tc"], "totalArs": round(total, 2), "numero": f["numero"],
                                          "totalOriginal": abs(float(f["total"] or 0))}
    for f in fetch_all("SELECT IdVenta AS id, Fecha AS fecha, IdConsignatario AS idContacto, "
                       "[Importe Neto a percibir] AS total, [Nro Documento] AS numero FROM dbo.[Venta Granos]"):
        docs[("VentaGranos", f["id"])] = {"fecha": f["fecha"], "idContacto": f["idContacto"], "moneda": "Pesos",
                                          "numero": f"Venta granos {f['numero'] or ''}".strip(),
                                          "totalArs": None if f["total"] is None else round(float(f["total"]), 2)}
    for f in fetch_all("SELECT IdVenta AS id, Fecha AS fecha, IdConsignatario AS idContacto, [Nro documento] AS numero "
                       "FROM dbo.[Venta Hacienda]"):
        clave = ("VentaHacienda", f["id"])
        total = None
        if claves is None or clave in claves:
            cabecera, lineas = get_venta_cabecera(f["id"]), get_lineas_venta(f["id"])
            if cabecera is not None and lineas:
                total = round(calcular_totales(lineas, cabecera)["importeTotal"], 2)
        docs[clave] = {"fecha": f["fecha"], "idContacto": f["idContacto"], "moneda": "Pesos", "totalArs": total,
                       "numero": f"Venta hacienda {f['numero'] or ''}".strip()}
    for f in fetch_all("SELECT IdImpuesto AS id, Fecha AS fecha, Importe AS total FROM dbo.Impuestos"):
        docs[("Impuesto", f["id"])] = {"fecha": f["fecha"], "idContacto": None, "moneda": "Pesos",
                                       "totalArs": None if f["total"] is None else round(abs(float(f["total"])), 2)}
    for f in fetch_all(f"SELECT r.IdSalario AS id, r.[Fecha de pago] AS fecha, r.IdContacto AS idContacto, "
                       f"{_IMPORTE_SQL} AS total FROM dbo.Remuneraciones r"):
        docs[("Remuneracion", f["id"])] = {"fecha": f["fecha"], "idContacto": f["idContacto"], "moneda": "Pesos",
                                           "totalArs": None if f["total"] is None else round(float(f["total"]), 2)}
    return docs


def cargar() -> dict:
    """Todo lo necesario para las reglas, el control y la corrección."""
    lineas = _lineas()
    raw = {
        "aplicaciones": _aplicaciones(),
        "lineasCompras": _lineas_compras(),
        "tesoreria": _tesoreria(),
        "backfill": _backfill(),
        "lineas": lineas,
        "pagosResumen": _pagos_resumen(),
        "valores": _valores(),
        "movimientos": movimientos_bancarios(),
        "importesOtros": importes_efectivo(),
    }
    con_vinculo = {(a["tipoDocumento"], a["idDocumento"]) for a in raw["aplicaciones"]}
    raw["documentos"] = documentos(con_vinculo)
    raw["fechasOtros"] = fechas_otros_medios(lineas)
    raw["vinculos"] = cadenas.construir_vinculos(raw)
    return raw


def vinculos_de_documentos(docs: list[tuple]) -> list[dict]:
    """Vínculos de nivel documento de unas facturas puntuales, sin cargar
    todo: para el saldo pendiente y la validación al guardar. No arma las
    cadenas de movimiento (no hacen falta para "cuánto está pagado")."""
    if not docs:
        return []
    claves = set(docs)
    raw = {"aplicaciones": [], "lineasCompras": [], "tesoreria": [], "backfill": _backfill(docs)}
    for i in range(0, len(docs), 300):
        lote = docs[i:i + 300]
        raw["aplicaciones"] += _aplicaciones(lote)
        raw["lineasCompras"] += _lineas_compras(lote)
        raw["tesoreria"] += _tesoreria(lote)
    raw["documentos"] = {k: v for k, v in _documentos_livianos(claves).items()}
    return cadenas.construir_vinculos(raw)


def _documentos_livianos(claves: set[tuple]) -> dict[tuple, dict]:
    """Moneda y TC de las compras pedidas (lo único que usa la pesificación)."""
    ids = [i for t, i in claves if t == "CompraDeuda"]
    docs: dict[tuple, dict] = {}
    for i in range(0, len(ids), 500):
        lote = ids[i:i + 500]
        for f in fetch_all(f"SELECT IdDeuda AS id, Moneda AS moneda, [Tipo de Cambio] AS tc FROM dbo.Compras "
                           f"WHERE IdDeuda IN ({','.join('?' * len(lote))})", tuple(lote)):
            docs[("CompraDeuda", f["id"])] = f
    return docs


def pagado_de_documentos(docs: list[tuple]) -> dict[tuple, float]:
    pagado = defaultdict(float, cadenas.pagado_por_documento(vinculos_de_documentos(docs)))
    return {k: round(pagado[k], 2) for k in docs}
