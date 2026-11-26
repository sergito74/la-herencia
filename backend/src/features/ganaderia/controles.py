"""Controles ganaderos (052 FR-011, T036).

Cada control devuelve casos {tipo, clave, texto, enlace}. Un caso revisado se acepta con motivo (GanControlAceptado:
quién, cuándo, por qué) y deja de mostrarse; la marca se puede quitar. Los controles son reglas generales: ningún caso
está escrito en el código.

Grupos: Ventas, Consignatarios, Stock, Pastaje, Imputación, Forrajes.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import date, datetime, timedelta

from src.db.connection import execute_write, fetch_all

KG_CABEZA = (0.35, 2.5)  # rango admitido de kg/cabeza contra el peso típico de la categoría
DIAS_CONSIGNATARIO = 30
DESDE_VENTAS = date(2016, 1, 1)
DESDE_IMPUTACION = date(2025, 4, 1)  # 050: imputación por renglón desde el ejercicio 2025/26
_cache: dict = {}


def _pesos(v: float, moneda: str = "$") -> str:
    t = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if v < 0 else ''}{moneda} {t}"


def _caso(tipo: str, clave, texto: str, enlace: str | None = None) -> dict:
    return {"tipo": tipo, "clave": str(clave), "texto": texto, "enlace": enlace}


def _venta(r) -> str:
    return f"Venta {r['doc'] or r['idVenta']} del {str(r['fecha'])[:10]}"


# ---------- Ventas (funciones puras sobre los renglones) ----------

def controles_ventas(renglones: list[dict], peso_tipico: dict) -> list[dict]:
    """renglones: {idVenta, idDetalle, fecha, doc, tipo, producto, cantidad, unidad, peso, precio}."""
    from src.features.ganaderia import categorias

    out = []
    por_venta = defaultdict(list)
    for r in renglones:
        por_venta[r["idVenta"]].append(r)
    for idv, rs in por_venta.items():
        enl = f"/ventas/hacienda/{idv}/editar"
        vistos = defaultdict(list)
        for r in rs:
            x = categorias.cabezas_y_kg(r["cantidad"], r["unidad"], r["peso"], peso_tipico.get(r["tipo"]))
            if not x["esHacienda"]:
                continue
            if not x["cabezas"] or x["kgEstimado"] or not x["kg"]:
                falta = "cabezas" if not x["cabezas"] else "kg"
                out.append(_caso("venta_sin_dato", r["idDetalle"], f"{_venta(r)}: {r['producto']} sin {falta}", enl))
            elif peso_tipico.get(r["tipo"]):
                kc = abs(x["kg"] / x["cabezas"])
                lo, hi = (peso_tipico[r["tipo"]] * k for k in KG_CABEZA)
                if not lo <= kc <= hi:
                    out.append(_caso("venta_kg_cabeza", r["idDetalle"],
                                     f"{_venta(r)}: {r['producto']} con {kc:,.0f} kg por cabeza".replace(",", "."), enl))
            vistos[(r["tipo"], r["cantidad"], r["peso"], r["precio"])].append(r)
        for k, iguales in vistos.items():
            if len(iguales) > 1:
                r = iguales[0]
                out.append(_caso("venta_renglon_repetido", ",".join(str(i["idDetalle"]) for i in iguales),
                                 f"{_venta(r)}: {len(iguales)} renglones idénticos de {r['producto']}. "
                                 "Verificar con el PDF de la liquidación", enl))
        for r in rs:
            c = float(r["cantidad"] or 0)
            if c < 0 and not any(o is not r and o["tipo"] == r["tipo"] and float(o["cantidad"] or 0) == -c for o in rs):
                out.append(_caso("venta_negativo_sin_par", r["idDetalle"],
                                 f"{_venta(r)}: renglón negativo de {r['producto']} sin el renglón que corrige", enl))
    return out


def _ventas() -> list[dict]:
    from src.features.ganaderia import stock

    rs = fetch_all(
        "SELECT v.IdVenta idVenta, d.IdDetalleVenta idDetalle, v.Fecha fecha, v.[Nro documento] doc, "
        "d.IdTipoProducto tipo, t.[Tipo de Hacienda] producto, d.Cantidad cantidad, d.[Unidad de medida] unidad, "
        "d.[Peso Total] peso, ISNULL(d.[Precio unitario (A)],0) + ISNULL(d.[Precio unitario (B)],0) precio "
        "FROM dbo.[Det_Ventas Hacienda] d JOIN dbo.[Venta Hacienda] v ON v.IdVenta = d.IdVenta "
        "LEFT JOIN dbo.[Tipo Hacienda] t ON t.IdTipoHacienda = d.IdTipoProducto WHERE v.Fecha >= ?", (DESDE_VENTAS,))
    cats = stock._catalogos()[0]
    peso = {th: float(cats[c]["peso"] or 0) for th, c in stock.categoria_de_tipo_hacienda().items() if c in cats}
    return controles_ventas(rs, peso)


# ---------- Consignatarios ----------

def _consignatarios(hoy: date) -> list[dict]:
    from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta

    out = []
    for r in fetch_all("SELECT v.IdConsignatario id, k.[Razon Social] nombre, MAX(v.Fecha) ultima, "
                       "SUM(ISNULL(v.Complemento,0)) complemento FROM dbo.[Venta Hacienda] v "
                       "JOIN dbo.Contactos k ON k.IdContacto = v.IdConsignatario WHERE v.IdConsignatario IS NOT NULL "
                       "GROUP BY v.IdConsignatario, k.[Razon Social]"):
        ultima = r["ultima"].date() if isinstance(r["ultima"], datetime) else r["ultima"]
        if (hoy - ultima).days < DIAS_CONSIGNATARIO:
            continue
        c = cargar_cuenta(r["id"])
        usd = c["filas"] and c.get("gobierna") == "Dolares"
        saldo = round(c["saldoDolares"] if usd else c["saldoPesos"], 2) if c["filas"] else 0.0
        if abs(saldo) >= 0.01:
            txt = f"{r['nombre']}: saldo {_pesos(saldo, 'us$' if usd else '$')}"
            txt += f" a más de {DIAS_CONSIGNATARIO} días de la última venta ({ultima:%d/%m/%Y})"
            if r["complemento"]:
                txt += ". Tiene ventas con Complemento: revisar que el efectivo esté cobrado"
            out.append(_caso("consignatario_saldo", f"{r['id']}|{saldo:.2f}", txt,
                             f"/finanzas/cuentas-corrientes?contacto={r['id']}"))
    return out


# ---------- Stock ----------

def _stock(hoy: date) -> list[dict]:
    from src.features.ganaderia import stock

    out = []
    fechas = sorted({str(r["fecha"])[:10] for r in stock._recuentos_db()})
    for f in fechas + [hoy.isoformat()]:
        st = stock.stock(date.fromisoformat(f), None, "todos")
        for c in st["categorias"]:
            if c["cabezas"] < 0:
                out.append(_caso("stock_negativo", f"{f}|{c['idEstablecimiento']}|{c['categoria']}|{c['dueno']}",
                                 f"{c['establecimiento']} al {f[8:]}/{f[5:7]}/{f[:4]}: {c['categoria']} ({c['duenoNombre'] or c['dueno']}) en "
                                 f"{c['cabezas']} cabezas", "/ganaderia/stock"))
        if f != hoy.isoformat():
            for s in st["sinExplicar"]:
                out.append(_caso("stock_recuento", f"{f}|{s['establecimiento']}|{s['categoria']}|{s['dueno']}",
                                 f"Recuento {s['establecimiento']} del {f[8:]}/{f[5:7]}/{f[:4]}: {s['categoria']} ({s['dueno']}) "
                                 f"{'+' if s['diferencia'] > 0 else ''}{s['diferencia']} contra lo esperado "
                                 "por los movimientos", "/ganaderia/stock"))
    return list({c["clave"] + c["tipo"]: c for c in out}.values())


# ---------- Pastaje ----------

def _pastaje(hoy: date) -> list[dict]:
    out = []
    liq = defaultdict(list)
    for r in fetch_all("SELECT l.IdLiquidacion id, l.IdContratoPastaje c, l.Periodo p, l.Total total, "
                       "(SELECT SUM(CASE WHEN x.Tipo LIKE 'nota%credito%' THEN -x.Total ELSE x.Total END) FROM dbo.PastajeComprobantes x "
                       " WHERE x.IdLiquidacion = l.IdLiquidacion AND x.Estado = 'vigente') facturado "
                       "FROM dbo.PastajeLiquidaciones l WHERE l.Estado = 'confirmada'"):
        liq[r["c"]].append(r)
    for k in fetch_all("SELECT c.IdContratoPastaje id, c.FechaInicio ini, c.FechaFin fin, x.[Razon Social] nombre "
                       "FROM dbo.ContratosPastaje c JOIN dbo.Contactos x ON x.IdContacto = c.IdContactoCliente "
                       "WHERE c.Estado <> 'anulado'"):
        ini = date.fromisoformat(str(k["ini"])[:10])
        fin = date.fromisoformat(str(k["fin"])[:10]) if k["fin"] else hoy
        hechos = {str(r["p"])[:7] for r in liq[k["id"]]}
        m = ini.replace(day=1)
        while m < min(fin, hoy).replace(day=1):  # meses ya terminados
            if m.isoformat()[:7] not in hechos:
                out.append(_caso("pastaje_sin_liquidar", f"{k['id']}|{m:%Y-%m}",
                                 f"{k['nombre']}: {m:%m/%Y} sin liquidación confirmada", "/ventas/pastaje"))
            m = (m + timedelta(days=32)).replace(day=1)
        for r in liq[k["id"]]:
            fac = float(r["facturado"] or 0)
            if abs(fac - float(r["total"] or 0)) >= 0.01:
                txt = (f"{k['nombre']} {str(r['p'])[5:7]}/{str(r['p'])[:4]}: "
                       + ("liquidación sin factura emitida" if not fac else
                          f"facturado {_pesos(fac)} distinto de lo liquidado {_pesos(float(r['total']))}"))
                out.append(_caso("pastaje_facturado", r["id"], txt, f"/ventas/pastaje/{k['id']}"))
    return out


# ---------- Imputación ----------

def _imputacion() -> list[dict]:
    out = []
    for r in fetch_all(
            "SELECT d.IdDetalleCompra id, c.IdDeuda idCompra, c.Fecha f, c.[Nro Documento] doc, k.[Razon Social] prov, "
            "d.[Producto/Servicio] item FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra "
            "LEFT JOIN dbo.Contactos k ON k.IdContacto = c.IdContacto "
            "WHERE d.IdCentroCostos IS NULL OR d.IdCentroCostos NOT IN (SELECT IdCentro FROM dbo.[Centro de costos])"):
        out.append(_caso("imputacion_sin_centro", r["id"],
                         f"{r['prov']} {r['doc']} ({str(r['f'])[:10]}): «{r['item']}» sin centro de costos; "
                         "la suma de los centros no daría el total de compras", f"/compras/{r['idCompra']}/editar"))
    for r in fetch_all(
            "SELECT d.IdDetalleCompra id, c.IdDeuda idCompra, c.Fecha f, c.[Nro Documento] doc, k.[Razon Social] prov, "
            "d.[Producto/Servicio] item, d.IdCentroCostos cc, t.Destino destino FROM dbo.TamizRenglones t "
            "JOIN dbo.Det_Compras d ON d.IdDetalleCompra = t.IdDetalleCompra JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra "
            "LEFT JOIN dbo.Contactos k ON k.IdContacto = c.IdContacto WHERE t.Vigente = 1 AND "
            "((t.Destino = 'Ganaderia' AND d.IdCentroCostos <> 2) OR "
            " (d.IdCentroCostos = 2 AND t.Destino IN ('Estructura','Financiero')))"):
        out.append(_caso("imputacion_contradictoria", r["id"],
                         f"{r['prov']} {r['doc']} ({str(r['f'])[:10]}): «{r['item']}» con centro "
                         f"{'Ganadería' if r['cc'] == 2 else 'no ganadero'} e imputado a {r['destino']}",
                         f"/compras/{r['idCompra']}/editar"))
    for r in fetch_all(
            "SELECT d.IdDetalleCompra id, c.IdDeuda idCompra, c.Fecha f, c.[Nro Documento] doc, k.[Razon Social] prov, "
            "d.[Producto/Servicio] item FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra "
            "LEFT JOIN dbo.Contactos k ON k.IdContacto = c.IdContacto WHERE d.IdCentroCostos = 2 AND c.Fecha >= ? "
            "AND NOT EXISTS (SELECT 1 FROM dbo.TamizRenglones t WHERE t.IdDetalleCompra = d.IdDetalleCompra AND t.Vigente = 1)",
            (DESDE_IMPUTACION,)):
        out.append(_caso("imputacion_ganaderia_pendiente", r["id"],
                         f"{r['prov']} {r['doc']} ({str(r['f'])[:10]}): «{r['item']}» de Ganadería sin imputar",
                         f"/compras/{r['idCompra']}/editar"))
    for r in fetch_all(
            "SELECT d.IdDetalleCompra id, c.IdDeuda idCompra, c.Fecha f, c.[Nro Documento] doc, k.[Razon Social] prov, "
            "d.[Producto/Servicio] item, ABS(d.Cantidad * d.[Precio Unitario]) renglon, s.imp "
            "FROM (SELECT p.IdDetalleCompra, SUM(p.Importe) imp FROM dbo.ImputacionPropuestas p "
            "      WHERE p.Origen = 'Directo' AND p.Estado = 'Aprobada' AND p.IdCorrida = (SELECT TOP 1 p2.IdCorrida "
            "        FROM dbo.ImputacionPropuestas p2 WHERE p2.IdDetalleCompra = p.IdDetalleCompra AND p2.Origen = 'Directo' "
            "        AND p2.Estado <> 'Reemplazada' ORDER BY p2.FechaCalculo DESC, p2.IdPropuesta DESC) "
            "      GROUP BY p.IdDetalleCompra) s "
            "JOIN dbo.Det_Compras d ON d.IdDetalleCompra = s.IdDetalleCompra JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra "
            "LEFT JOIN dbo.Contactos k ON k.IdContacto = c.IdContacto "
            "WHERE c.Moneda <> 'Dolares' AND ABS(ABS(s.imp) - ABS(d.Cantidad * d.[Precio Unitario])) >= 0.01"):
        from src.features.imputacion.progresivo import factor_particular

        fac = factor_particular(r["id"])  # compra con parte particular: se imputa solo la parte de la empresa
        if fac is not None and abs(abs(float(r["imp"])) - float(r["renglon"]) * fac) < 0.05:
            continue
        out.append(_caso("imputacion_fracciones", r["id"],
                         f"{r['prov']} {r['doc']} ({str(r['f'])[:10]}): «{r['item']}» imputado {_pesos(float(r['imp']))} "
                         f"y el renglón es {_pesos(float(r['renglon']))}", f"/compras/{r['idCompra']}/editar"))
    return out


# ---------- Forrajes ----------

def _forrajes(hoy: date) -> list[dict]:
    from src.features.ganaderia import reservas

    return [_caso("reserva_sin_consumo", r["id"],
                  f"Silo maíz {r['campania']} ({r['fuente']}): sin consumo registrado; se estima consumido en el "
                  "ejercicio siguiente al de confección", "/ganaderia/stock")
            for r in reservas.reservas(hoy)["items"] if r["estado"] != "Registrado"]


GRUPOS = [("Ventas", lambda h: _ventas()), ("Consignatarios", _consignatarios), ("Stock", _stock),
          ("Pastaje", _pastaje), ("Imputación", lambda h: _imputacion()), ("Forrajes", _forrajes)]


def aceptados() -> list[dict]:
    return fetch_all("SELECT IdAceptado id, Tipo tipo, Clave clave, Motivo motivo, Usuario usuario, Fecha fecha "
                     "FROM dbo.GanControlAceptado WHERE Vigente = 1 ORDER BY Fecha DESC")


def filtrar(grupos: list[dict], acept: list[dict]) -> list[dict]:
    """Función pura: saca los casos aceptados (tipo + clave)."""
    marca = {(a["tipo"], a["clave"]) for a in acept}
    return [{**g, "items": [i for i in g["items"] if (i["tipo"], i["clave"]) not in marca]} for g in grupos]


def correr(hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    grupos = []
    for nombre, fn in GRUPOS:
        try:
            grupos.append({"grupo": nombre, "items": fn(hoy), "error": None})
        except Exception as exc:  # un control roto no tapa a los demás: se muestra el error
            grupos.append({"grupo": nombre, "items": [], "error": str(exc)[:300]})
    _cache["ultimo"] = {"corrido": datetime.now().isoformat(timespec="seconds"), "grupos": grupos}
    _cache["t"] = time.time()
    return resultado()


def resultado() -> dict:
    if "ultimo" not in _cache or time.time() - _cache["t"] > 6 * 3600:
        return correr()
    acept = aceptados()
    u = _cache["ultimo"]
    gs = filtrar(u["grupos"], acept)
    return {"corrido": u["corrido"], "grupos": [{**g, "cantidad": len(g["items"])} for g in gs],
            "aceptados": [{**a, "fecha": str(a["fecha"])[:19]} for a in acept]}


def invalidar() -> None:
    _cache.pop("ultimo", None)


def aceptar(tipo: str, clave: str, motivo: str, usuario: str | None) -> None:
    if len((motivo or "").strip()) < 3:
        raise ValueError("Indicá el motivo")
    execute_write("INSERT INTO dbo.GanControlAceptado (Tipo, Clave, Motivo, Usuario) VALUES (?, ?, ?, ?)",
                  (tipo, clave[:200], motivo.strip()[:300], usuario))


def quitar(id_aceptado: int) -> None:
    execute_write("UPDATE dbo.GanControlAceptado SET Vigente = 0 WHERE IdAceptado = ?", (id_aceptado,))
