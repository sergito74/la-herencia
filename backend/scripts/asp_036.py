"""036 — ASP Agroservicios Pampeanos (17), 19/10/2026: cuenta en dólares según el libro de ASP.

Fuente: "Resumen Cuenta ASP Completa.xlsx" (Resumenes de Cuenta/ASP; detalle de cuenta corriente en US$ de ASP, 06/06/2012 →
18/07/2016, con los PDF del 20/01/2014, 15/08/2014, 15/04/2016 y 15/07/2016). El saldo inicial del libro (US$3.228,83) es
exactamente FC 2769 + FC 2771 (mayo 2012): antes la cuenta estaba en cero. El libro pasa por cero varias veces y termina en
US$0,01 con el recibo 1053314 del 18/07/2016 (BNA $4.567,82).
1. Cada documento nuestro toma los US$ del libro de ASP (por número; ASP manda): las ND de intereses AgroNación cargadas en
   pesos pasan a valer sus dólares. Los documentos en pesos que no están en el libro en US$ valen 0 dólares.
2. Pagos: ASP acreditaba con recibos que agrupan varios pagos. Cada recibo reparte sus US$ entre sus pagos en proporción a
   los pesos: cheques por número según la planilla de Sergio "Resumen Cuenta ASP (1).xlsx" (columna Recibo), cupones de
   tarjeta AgroNación y otros pagos por fecha exacta del recibo; solo si el TC implícito queda a ±25% del BNA. Los pagos sin
   recibo identificado se valúan con los US$ que le faltan al tramo para cerrar en cero (antes del libro, 2010-2012, y
   el libro 2012-2016), en proporción a sus pesos.
0. Correcciones de documentos contra su PDF (o el libro de ASP si no hay PDF): FC 0213-2769 sin la percepción IIBB
   (US$53,26; total US$2.406,92); NC 0292-113 con la percepción en positivo (US$−895,38 según el PDF); FC 0292-58 con
   precios en US$ a otro TC y 30 litros de 2,4D en vez de 20 (total US$1.176,15 según el PDF); NC 0392-412 (el PDF vinculado es de otro proveedor; libro de
   ASP: 2 bolsas a US$120 + IVA = US$290,40). FC 0392-41 queda como el PDF (US$13.635,54; el libro de ASP dice 13.630,50).
3. La diferencia en pesos que queda (la cuenta se lleva en dólares) se ajusta con un AjusteCuentaCorriente de diferencia de
   cambio al 18/07/2016.
Idempotente. Uso (desde backend/): python -m scripts.asp_036 [--aplicar]
"""

from __future__ import annotations

import re
import sys
import warnings
from datetime import date

import openpyxl

from src.db.connection import _assert_target_is_wc, execute_write_transaction
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U = 17, "Sergio (barrida 036)"
CARPETA = "C:/Users/Sergio/Documents/La Herencia/Administracion y gestion/Resumenes de Cuenta/ASP/"
LIBRO = CARPETA + "Resumen Cuenta ASP Completa.xlsx"
PLANILLA = CARPETA + "Resumen Cuenta ASP (1).xlsx"
FUENTE = "Libro en US$ de ASP 2012-2016 (Resumen Cuenta ASP Completa.xlsx) y recibos de la planilla Resumen Cuenta ASP (1).xlsx"
# Tramos: antes del libro de ASP (cuenta en cero antes de las FC de mayo 2012) y el libro completo, que cierra el 18/07/2016.
# Los ceros intermedios del libro no se usan como corte: los cheques diferidos de un recibo se debitan después.
CEROS = [date(2012, 4, 30), date(2016, 7, 18)]
warnings.filterwarnings("ignore")


def _filas_libro():
    return [f for f in openpyxl.load_workbook(LIBRO, data_only=True).worksheets[0].iter_rows(values_only=True) if f[0] and hasattr(f[0], "year")]


def libro_asp() -> dict[str, float]:
    docs = {}
    for f in _filas_libro():
        if f[2] != "Recibo" and isinstance(f[4], str) and len(f[4]) >= 10:
            docs[str(int(f[4][-8:]))] = float(f[6] or 0) - float(f[7] or 0)   # por número de comprobante (sin ceros)
    docs["2769"], docs["2771"] = 2406.92, 821.91   # saldo inicial del libro (detalle en Resumen Cuenta ASP.xlsx)
    return docs


def recibos_asp():
    return [(f[0].date(), int(f[4]) if f[4] else f[0].toordinal(), float(f[7])) for f in _filas_libro() if f[2] == "Recibo"]


def _k(p):
    return (p["origenTipo"], p["idOrigen"])


def _neto(p):
    return p["creditoOriginal"] - p["deudaOriginal"]


def asignar_recibos(pagos):
    """Asigna pagos a grupos de recibos de ASP (recibos a un día de distancia forman un grupo: ASP los emitía juntos)."""
    hoja = openpyxl.load_workbook(PLANILLA, data_only=True).worksheets[0]
    cheque_recibo = {str(r[3]): r[4] for r in hoja.iter_rows(values_only=True) if r[2] == "Cheque" and r[4]}
    grupos: list[dict] = []
    for fecha, nro, usd in sorted(recibos_asp()):
        if grupos and (fecha - grupos[-1]["hasta"]).days <= 1:
            g = grupos[-1]
        else:
            g = {"desde": fecha, "hasta": fecha, "nros": set(), "usd": 0.0}
            grupos.append(g)
        g["hasta"] = fecha
        g["nros"].add(nro)
        g["usd"] += usd
    de_nro = {n: i for i, g in enumerate(grupos) for n in g["nros"]}
    asig = {}
    for p in pagos:
        n = str(p["numeroDocumento"] or "")
        if n in cheque_recibo and cheque_recibo[n] in de_nro:
            asig[_k(p)] = de_nro[cheque_recibo[n]]
            continue
        dist = sorted((min(abs((g["desde"] - p["fecha"]).days), abs((g["hasta"] - p["fecha"]).days)), i) for i, g in enumerate(grupos))
        if dist and dist[0][0] <= 3 and (len(dist) == 1 or dist[1][0] > dist[0][0]):
            asig[_k(p)] = dist[0][1]
    cot = bimonetaria.cotizacion_bna()
    for i, g in enumerate(grupos):
        ks = [k for k, v in asig.items() if v == i]
        pesos = sum(_neto(p) for p in pagos if _k(p) in ks)
        bna = cot.dia_anterior(g["hasta"])
        if not ks or not bna or abs(pesos / g["usd"] / bna - 1) > 0.25:
            for k in ks:
                del asig[k]
    return asig, {i: g["usd"] for i, g in enumerate(grupos)}


def plan():
    asp = libro_asp()
    filas = bimonetaria.cargar_cuenta(C, refrescar=True)["filas"]
    val, docs_sin_libro = {}, []
    for f in filas:
        if f["origenTipo"] != "Compras":
            continue
        n = str(int(re.findall(r"\d+", f["numeroDocumento"] or "0")[-1]))
        if f["moneda"] == "Dolares":   # el motor usa el importe del documento en dólares (corregido contra su PDF)
            val[_k(f)] = round(f["deudaOriginal"] - f["creditoOriginal"], 2)
        elif n in asp:
            val[_k(f)] = asp[n]
        else:
            val[_k(f)] = 0.0
            docs_sin_libro.append((str(f["fecha"]), f["numeroDocumento"], round(f["deudaOriginal"] - f["creditoOriginal"], 2)))
    # el ajuste de diferencia de cambio en pesos (paso 3) no es un pago: no entra en el reparto y vale 0 dólares
    pagos = [f for f in filas if f["origenTipo"] not in ("Compras", "Ajuste Interno")]
    asig, usd_recibo = asignar_recibos(pagos)
    pesos_recibo: dict = {}
    for p in pagos:
        if _k(p) in asig:
            pesos_recibo[asig[_k(p)]] = pesos_recibo.get(asig[_k(p)], 0.0) + _neto(p)
    for p in pagos:
        if _k(p) in asig:
            r = asig[_k(p)]
            val[_k(p)] = round(usd_recibo[r] * _neto(p) / pesos_recibo[r], 2)
    fecha_de = {_k(f): f["fecha"] for f in filas}
    for f in filas:
        if f["origenTipo"] == "Ajuste Interno":
            val[_k(f)] = 0.0
    tramos, desde = [], date(1900, 1, 1)
    for hasta in CEROS:
        en = [k for k in val if desde < fecha_de[k] <= hasta]
        docs = sum(val[k] for k in en if k[0] == "Compras")
        ya = sum(val[k] for k in en if k[0] != "Compras")
        libres = [p for p in pagos if desde < p["fecha"] <= hasta and _k(p) not in asig]
        pesos = sum(_neto(p) for p in libres)
        falta = docs - ya
        for p in libres:
            val[_k(p)] = round(falta * _neto(p) / pesos, 2) if pesos else 0.0
        tramos.append((str(hasta), round(docs, 2), round(ya, 2), round(falta, 2), round(pesos, 2), round(pesos / falta, 3) if falta else None, len(libres)))
        desde = hasta
    resto = [p for p in pagos if p["fecha"] > CEROS[-1]]
    return val, tramos, docs_sin_libro, resto


if __name__ == "__main__":
    _assert_target_is_wc()
    val, tramos, sin_libro, resto = plan()
    for t in tramos:
        print("tramo hasta", t[0], "US$ docs", t[1], "US$ por recibos", t[2], "US$ resto", t[3], "pesos resto", t[4], "TC resto", t[5], "pagos", t[6])
    print("Docs en pesos fuera del libro US$ (valen 0):", sin_libro)
    print("Pagos posteriores al último cero:", [(str(p["fecha"]), p["origenTipo"], p["creditoOriginal"]) for p in resto])
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar")
    print("Respaldo verificado:", backup_verificado("asp-036"))
    execute_write_transaction([
        ("UPDATE dbo.Compras SET [Ingresos Brutos] = 53.26 WHERE IdDeuda = 2143509417", ()),
        ("UPDATE dbo.Compras SET [Ingresos Brutos] = -18.12 WHERE IdDeuda = 2143509688", ()),
        ("UPDATE dbo.Det_Compras SET [Precio Unitario] = -120 WHERE IdCompra = 2143509912", ()),
        # FC 58: precios del PDF en pesos / TC 4,633 de la factura; IIBB $110,31
        ("UPDATE dbo.Det_Compras SET [Precio Unitario] = 14.59 / 4.633 WHERE IdCompra = 2143509530 AND [Producto/Servicio] LIKE '%Glifosato%'", ()),
        ("UPDATE dbo.Det_Compras SET [Precio Unitario] = 62.55 / 4.633 WHERE IdCompra = 2143509530 AND [Producto/Servicio] LIKE '%Li Plus%'", ()),
        ("UPDATE dbo.Det_Compras SET [Precio Unitario] = 39.38 / 4.633 WHERE IdCompra = 2143509530 AND [Producto/Servicio] LIKE '%Choice%'", ()),
        ("UPDATE dbo.Det_Compras SET [Precio Unitario] = 39.38 / 4.633, Cantidad = 20 WHERE IdCompra = 2143509530 AND [Producto/Servicio] LIKE '%2,4D%'", ()),
        ("UPDATE dbo.Compras SET [Ingresos Brutos] = ROUND(110.31 / 4.633, 2) WHERE IdDeuda = 2143509530", ()),
    ])
    bimonetaria.invalidar()
    val, *_ = plan()
    st = [("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ?", (C,)),
          ("DELETE FROM dbo.AjustesCuentaCorriente WHERE IdContacto = ? AND Motivo LIKE 'Diferencia de cambio acumulada (cuenta en US$ de ASP%'", (C,))]
    st += [("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) VALUES (?, ?, ?, ?, ?, NULL, ?, SYSDATETIME())",
            (o, i, C, abs(v), FUENTE, U)) for (o, i), v in val.items()]
    execute_write_transaction(st)
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    pesos = round(r["saldoPesos"], 2)
    if abs(pesos) > 0.01:
        execute_write_transaction([("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto, Fecha, Lado, Importe, Motivo, Usuario, FechaAlta) VALUES "
                                    "(?, '2016-07-18', ?, ?, ?, ?, SYSDATETIME())",
                                    (C, "Deuda" if pesos > 0 else "Credito", abs(pesos),
                                     "Diferencia de cambio acumulada (cuenta en US$ de ASP, cerrada en US$0 con el recibo 1053314 del 18/07/2016)", U))])
        bimonetaria.invalidar()
        r = bimonetaria.cargar_cuenta(C, refrescar=True)
        execute_write_transaction([("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) "
                                    "VALUES (?, ?, ?, 0, 'Diferencia de cambio en pesos (no mueve dólares)', NULL, ?, SYSDATETIME())", (f["origenTipo"], f["idOrigen"], C, U))
                                   for f in r["filas"] if f["origenTipo"] == "Ajuste Interno"
                                   and (f["origenTipo"], f["idOrigen"]) not in {k for k in val}])
        bimonetaria.invalidar()
        r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo: pesos", r["saldoPesos"], " US$", r["saldoDolares"], r["gobierna"])
