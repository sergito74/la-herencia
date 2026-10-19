"""036 — Lartirigoyen (61), 18/10/2026: imputaciones y valuación en dólares según las aplicaciones de Lartirigoyen.

Reemplaza el orden cronológico de `imputaciones_lartirigoyen_036` y `valuacion_lartirigoyen_036` (Sergio: "cierra con
el criterio de las aplicaciones del proveedor"). Lartirigoyen siempre cancela sus facturas en dólares pesificándolas al
TC de la propia factura ("Canc. Pesificación", TCC, AP) y cobra la diferencia con el dólar del día en ND en pesos; por
eso los dólares que movió cada crédito salen de qué documentos canceló.

`PLAN`: para cada crédito nuestro, los documentos que canceló según la aplicación FINAL de Lartirigoyen (tomada de):
- 2017-2018: resúmenes del 18/06/2018 y 17/07/2018 (CA 2581, 2638, 2787, 20388, 2987/2988/2989, 21309, 22232-22234,
  3110, 3111) y "Analisis CC Lartirigoyen.xlsx";
- 2019: TCC 34987/34988 (ficha del 26/05/2019) y mail del 14/06/2019 (saldo USD 1.552,81 y gastos de secado/cámara);
- 2020: resumen del 21/05/2020 (TCC 54515, AP 5516, OP 186151/186606) y OP 188537 / 189005;
- 2021: mail del 29/05/2021 (las 5 facturas del pago de $231.400), RD 2626 (eCheq FC 9398), RID 2808 (FC 9731);
- 2022-2024: AP 7850, 7885, 7886, 7888, 7896 (resúmenes 2023) y AP 8221 (extranet);
- tarjeta: las líneas de resumen ya vinculadas a sus documentos (Tarjetas_Resumenes_Lineas_Compras).
Claves del plan: número de comprobante (sufijo), 'B<id>' = débito BNA (pago de Lartirigoyen a nosotros), 'A<id>' =
ajuste de cuenta corriente al Debe, 'T<id>' = débito de tarjeta (reversión); '<doc>:<importe>' limita lo aplicado. Lo que el plan no cubre se aplica en orden cronológico y se informa.
Graba AplicacionesPago (origen 'manual') y ValuacionProveedor de la cuenta. Idempotente.

Uso (desde backend/): python -m scripts.aplicacion_lartirigoyen_036 [--aplicar]
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U = 61, "Sergio (barrida 036)"
NOTA = "Aplicación de Lartirigoyen (resúmenes y comprobantes 2017-2024) — barrida 036 18/10/2026"
FUENTE = "Aplicación de Lartirigoyen: pesos al TC de la factura en dólares que cancela (resúmenes 2017-2024, Sergio 18/10/2026)"
MEDIO = {"Banco Nacion": "bna", "Galicia": "galicia", "Venta Granos": "comp-venta-granos", "Retenciones": "retenciones",
         "Compras": "comp-compra"}

PLAN: dict[tuple[str, int], list[str]] = {
    ("Banco Nacion", 15024): ["A22"],
    ("Banco Nacion", 15025): ["3552", "3551", "1727", "1728"],                     # CA 2581 (quedan $178,18 sin pagar)
    ("Banco Nacion", 15026): ["4154"],                                             # RD 570 / CA 2787
    ("Retenciones", 1): ["1728", "1727", "4176"],                                 # RR 251: los $178,18 y el resto a FC 4176
    ("Banco Nacion", 15027): ["4176"],                                            # RD 583 cheque 3619952 + RR 251 = FC 4176
    ("Banco Nacion", 15028): ["4522", "4523", "4524", "4554", "5261", "2060"],     # RD 603 / CA 2987
    ("Banco Nacion", 15029): ["4522", "4523", "4524", "4554", "5261", "2060"],     # RD 608 / CA 2987
    ("Banco Nacion", 15030): ["2157", "5052", "5261", "13491", "2062", "5499"],
    ("Banco Nacion", 15031): ["6075"],
    ("Banco Nacion", 15032): ["6026"],
    ("Banco Nacion", 15033): ["6205", "5834"],                                    # RD 1122 (sobran $104,33 a la TCC 2019)
    ("Venta Granos", 88): ["5525:3340.05", "126136:560", "6862:6667.58", "41068:5025.71", "5499:52749.99",
                           "5514:104292.93", "5562:11266.96", "5834:17672.48", "41069"],          # TCC 34987
    ("Venta Granos", 89): ["41071", "41070", "5834:2528.49"],                      # TCC 34988
    ("Venta Granos", 90): ["5834"],
    ("Venta Granos", 91): ["5834"],
    ("Venta Granos", 94): ["41808", "41809", "41810", "41811", "5834", "2901", "2902"],
    ("Venta Granos", 95): ["41808", "41809", "41810", "41811", "5834", "2901", "2902"],
    ("Banco Nacion", 15034): ["127049"],                                          # secado y cámara del maíz (mail 14/06/2019)
    ("Banco Nacion", 15035): ["6370", "6391", "6399", "2929", "2930", "2901", "2902"],  # saldo USD 1.552,81 + dif. TC con IVA
    ("Venta Granos", 96): ["7107", "2929", "2930"],
    ("Banco Nacion", 15036): ["7107"],
    ("Banco Nacion", 15037): ["3448"],
    ("Venta Granos", 110): ["7573", "143402", "55586", "55587", "B15038"],         # TCC 54515 + OP 186151
    ("Venta Granos", 111): ["7573", "143402", "55586", "55587", "B15038"],
    ("Venta Granos", 112): ["B15040"],                                            # OP 188537 (LC + IVA RG 2300; la deducción mal cargada se borró el 19/10/2026)
    ("Venta Granos", 113): ["B15041"],                                            # OP 189005
    ("Venta Granos", 114): ["B15041"],
    ("Banco Nacion", 15042): ["8268", "3728"],
    ("Banco Nacion", 15043): ["8416", "3791"],
    ("Banco Nacion", 15044): ["8723", "3728", "3791", "3962", "3963"],  # pesificado al TC del día
    ("Banco Nacion", 15045): ["8848", "3962", "3963"],
    ("Galicia", 3): ["8540", "8894", "8895", "8903", "8984", "3962", "3963", "4118", "4117"],  # mail 29/05/2021, TC 94,56
    ("Galicia", 458): ["9398"],                                                   # RD 2626 eCheq
    ("Retenciones", 11): ["9398", "4117", "4118"],
    ("Galicia", 225): ["9731", "19813"],                                          # RID 2808
    ("Retenciones", 32): ["9731", "19813"],
    ("Galicia", 873): ["10918"],
    ("Retenciones", 71): ["10918", "4645", "4646"],
    ("Galicia", 879): ["4646"],
    ("Galicia", 880): ["4645", "11506", "11518", "11517"],
    ("Ajuste Interno", 23): ["11992"],                                            # RR 1283 en AP 7888
    ("Galicia", 1191): ["11506", "11518", "11517", "5185"],
    ("Galicia", 1201): ["5119", "5120", "5185"],                                  # AP 7850
    ("Retenciones", 104): ["11970", "11992"],                                     # RR 1408 en AP 7885 / 7888
    ("Retenciones", 105): ["5494"],                                               # saldo $19.366,94 aplicado en 2024
    ("Galicia", 1802): ["12422", "5324"],
    ("Galicia", 1969): ["12612", "5494"],                                         # AP 8221
    ("Retenciones", 152): ["12612", "5494"],
    ("Ajuste Interno", 25): ["5494"],
}
# Notas de crédito (por número): documento que corrigen
PLAN_NC = {"00000545": ["5684", "5693", "2157"], "00000546": ["2157"], "00007581": ["2060"], "00007600": ["13491"],
           "00007601": ["2062"], "00007602": ["2061", "T5523"], "00007603": ["2177"], "00000561": ["13514", "2177", "T5524"],
           "00000562": ["1905"], "00007668": ["5834"], "00000683": ["6205", "6370"], "00000930": ["2929", "2930", "7107"],
           "00000932": ["2929", "2930", "7107"], "00065348": ["143402"], "00065355": ["B15039"], "00092846": ["5210"],
           "00001944": ["12440"], "00001971": ["12509"], "00007543": ["13096"]}


def sufijo(nro: str) -> str:
    return re.sub(r"\D", "", (nro or "").split("-")[-1]).lstrip("0")


if __name__ == "__main__":
    aplicar_cambios = "--aplicar" in sys.argv
    _assert_target_is_wc()
    filas = bimonetaria.cargar_cuenta(C, refrescar=True)["filas"]
    tarjeta = defaultdict(float)
    for r in fetch_all("SELECT t.IdCompra AS i, t.ImporteImputado AS s FROM dbo.Tarjetas_Resumenes_Lineas_Compras t "
                       "JOIN dbo.Compras c ON c.IdDeuda = t.IdCompra WHERE c.IdContacto = ?", (C,)):
        tarjeta[r["i"]] += float(r["s"])
    tarjeta_por_importe = {round(float(r["s"]), 2): r["i"] for r in fetch_all(
        "SELECT t.IdCompra AS i, t.ImporteImputado AS s FROM dbo.Tarjetas_Resumenes_Lineas_Compras t "
        "JOIN dbo.Compras c ON c.IdDeuda = t.IdCompra WHERE c.IdContacto = ?", (C,))}

    # Documentos (deudas) con su capacidad en pesos y su TC si son en dólares
    docs: dict[str, dict] = {}
    orden: list[str] = []
    creditos: list[dict] = []
    tc_doc: dict[int, float] = {}
    for f in filas:
        clave = (f["origenTipo"], f["idOrigen"])
        if f["origenTipo"] == "Compras" and f["moneda"] == "Dolares":
            tc_doc[f["idOrigen"]] = f["tipoDeCambio"]
        if f["origenTipo"] == "Compras" and f["deudaOriginal"]:
            k = sufijo(f["numeroDocumento"])
            assert k not in docs, f"número repetido {k}"
            cap = round(f["deudaPesos"] - tarjeta.get(f["idOrigen"], 0.0), 2)
            docs[k] = {"id": f["idOrigen"], "nro": f["numeroDocumento"], "cap": cap, "usd": f["moneda"] == "Dolares",
                       "tc": f["tipoDeCambio"], "fecha": f["fecha"]}
            orden.append(k)
        elif f["origenTipo"] == "Banco Nacion" and f["deudaOriginal"]:
            docs[f"B{f['idOrigen']}"] = {"id": None, "nro": f"BNA {f['idOrigen']}", "cap": f["deudaPesos"], "usd": False, "tc": None, "fecha": f["fecha"]}
            orden.append(f"B{f['idOrigen']}")
        elif f["origenTipo"] in ("Tarjetas", "Tarjeta sin imputar") and f["deudaOriginal"]:
            docs[f"T{f['idOrigen']}"] = {"id": None, "nro": f"Tarjeta {f['idOrigen']}", "cap": f["deudaPesos"], "usd": False, "tc": None, "fecha": f["fecha"]}
            orden.append(f"T{f['idOrigen']}")
        elif f["origenTipo"] == "Ajuste Interno" and f["deudaOriginal"]:
            docs[f"A{f['idOrigen']}"] = {"id": None, "nro": f"Ajuste {f['idOrigen']}", "cap": f["deudaPesos"], "usd": False, "tc": None, "fecha": f["fecha"]}
            orden.append(f"A{f['idOrigen']}")
        elif f["creditoPesos"] and f["origenTipo"] not in ("Tarjetas", "Tarjeta sin imputar"):
            plan = PLAN_NC.get(re.sub(r"\D", "", f["numeroDocumento"] or "")[-8:]) if f["origenTipo"] == "Compras" else PLAN.get(clave)
            creditos.append({"clave": clave, "resto": f["creditoPesos"], "plan": plan, "usd": f["moneda"] == "Dolares",
                             "tc": f["tipoDeCambio"], "fecha": f["fecha"], "nro": f["numeroDocumento"]})
    faltan_plan = [c for c in creditos if c["plan"] is None]
    asignaciones: list[tuple] = []   # (clave crédito, doc key, pesos)

    def asignar(cr, k, tope=None):
        d = docs[k]
        x = round(min(cr["resto"], d["cap"], tope if tope is not None else cr["resto"]), 2)
        if x >= 0.01:
            asignaciones.append((cr["clave"], k, x)); cr["resto"] = round(cr["resto"] - x, 2); d["cap"] = round(d["cap"] - x, 2)

    for cr in creditos:                       # 1) aplicación de Lartirigoyen
        for item in cr["plan"] or []:
            if cr["resto"] < 0.01: break
            k, _, tope = item.partition(":")
            if k not in docs: raise SystemExit(f"documento {k} del plan no existe ({cr['clave']})")
            asignar(cr, k, float(tope) if tope else None)
    fallback = []
    for cr in creditos:                       # 2) lo que no cubre el plan: orden cronológico
        for k in orden:
            if cr["resto"] < 0.01: break
            if docs[k]["cap"] >= 0.01:
                antes = cr["resto"]; asignar(cr, k)
                if cr["resto"] < antes: fallback.append((cr["clave"], cr["nro"], docs[k]["nro"], round(antes - cr["resto"], 2)))

    sin_cubrir = [(docs[k]["nro"], docs[k]["cap"]) for k in orden if docs[k]["cap"] >= 0.01]
    sobrante = [(c["clave"], c["resto"]) for c in creditos if c["resto"] >= 0.01]
    print("Créditos sin plan:", [(c["clave"], c["nro"]) for c in faltan_plan])
    print("Aplicado en orden cronológico (sin documento de Lartirigoyen):")
    for x in fallback: print("  ", x)
    print("Documentos sin cubrir:", sin_cubrir)
    print("Créditos sobrantes:", sobrante)

    # Valuación: dólares por crédito en pesos = pesos aplicados a documentos en dólares / TC de la factura
    val: dict[tuple[str, int], float] = defaultdict(float)
    for f in filas:
        if f["moneda"] != "Dolares":
            val[(f["origenTipo"], f["idOrigen"])] += 0.0
    for clave, k, x in asignaciones:
        if docs[k]["usd"] and clave[0] != "Compras" or (docs[k]["usd"] and clave[0] == "Compras"):
            cr_usd = any(c["clave"] == clave and c["usd"] for c in creditos)
            if not cr_usd:
                val[clave] += x / docs[k]["tc"]
    for f in filas:                           # tarjeta: según el documento al que está vinculada
        if f["origenTipo"] in ("Tarjetas", "Tarjeta sin imputar") and f["creditoPesos"]:
            idc = tarjeta_por_importe.get(round(f["creditoPesos"], 2))
            tc = tc_doc.get(idc) if idc else None
            val[(f["origenTipo"], f["idOrigen"])] = f["creditoPesos"] / tc if tc else 0.0
    usd_docs = sum(f["deudaOriginal"] - f["creditoOriginal"] for f in filas if f["moneda"] == "Dolares")
    # redondeo de centavos (TC con 2-4 decimales en las facturas): se ajusta en el último pago (Galicia 28/06/2024, AP 8221)
    val[("Galicia", 1969)] += usd_docs - sum(val.values())
    print("USD facturado neto:", round(usd_docs, 2), " USD acreditado por pagos en pesos:", round(sum(val.values()), 2))

    imputaciones = [(MEDIO[clave[0]], clave[1], docs[k]["id"], x) for clave, k, x in asignaciones
                    if clave[0] in MEDIO and docs[k]["id"]]
    print("Imputaciones a grabar:", len(imputaciones))
    if not aplicar_cambios:
        print("Simulación: usar --aplicar para grabar.")
        raise SystemExit
    print("Respaldo verificado:", backup_verificado("aplicacion-lartirigoyen-036"))
    stmts = [("UPDATE a SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() "
              "FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
              "WHERE c.IdContacto = ? AND a.TipoDocumento = 'CompraDeuda' AND a.Anulada = 0",
              ("Reemplazada por la aplicación de Lartirigoyen (barrida 036)", U, C)),
             ("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ?", (C,))]
    stmts += [("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, "
               "ImporteAplicado, Fecha, Usuario, Anulada, Origen, NotaConciliacion) VALUES (?, ?, 'CompraDeuda', ?, ?, SYSDATETIME(), ?, 0, 'manual', ?)",
               (m, i, d, x, U, NOTA)) for m, i, d, x in imputaciones]
    stmts += [("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) "
               "VALUES (?, ?, ?, ?, ?, ?, ?, SYSDATETIME())",
               (o, i, C, round(d, 4), FUENTE, None if d else "0 = documento de la subcuenta en pesos", U)) for (o, i), d in val.items()]
    execute_write_transaction(stmts)
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo:", r["saldoPesos"], r["saldoDolares"])
