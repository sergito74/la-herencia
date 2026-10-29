"""036 — Lartirigoyen (61), 28/10/2026: las imputaciones se copian tal cual de Lartirigoyen (pedido de Sergio).

Plan: specs/036-revision-sistematica-cuentas/lartirigoyen-aplicaciones-20261028.json, armado con las aplicaciones de la extranet
(AP/APC/APD/APDS/APG, cancelaciones de granos TCC, compensaciones CODO, recibos RID/RR). Cada recibo se traduce a su movimiento
en WC (transferencia, retención, venta de granos, NC) y los cobros con tarjeta AgroNación a vínculos línea→compra. Control previo:
cada comprobante y cada pago queda usado exactamente por su importe (único desvío: $0,01 entre las dos líneas de tarjeta de abril
de 2017, $76.483,91, y el RIT 478 de Lartirigoyen, $76.483,92).
1. Anula (con motivo) las aplicaciones vigentes de los comprobantes de la cuenta 61 y carga las del plan.
2. Rehace los vínculos de tarjeta de las líneas del plan.
3. Recalcula la valuación en dólares de cada pago: pesos aplicados a cada comprobante en US$ divididos por su TC.
No cambia ningún saldo en pesos. Idempotente (si ya está aplicado, no hace nada).

Uso (desde backend/): python -m scripts.lartirigoyen_aplicaciones_portal_036
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U = 61, "Sergio (barrida 036)"
NOTA = "Copia de Lartirigoyen ({}), extranet 28/10/2026"
PLAN = json.loads((Path(__file__).resolve().parents[2] / "specs/036-revision-sistematica-cuentas/lartirigoyen-aplicaciones-20261028.json")
                  .read_text(encoding="utf-8"))
VALUACION = {"galicia": "Galicia", "bna": "Banco Nacion", "retenciones": "Retenciones", "comp-venta-granos": "Venta Granos",
             "comp-compra": "Compras"}
FUENTE = "Imputación de Lartirigoyen: pesos al TC del comprobante en dólares que cancela (extranet, 28/10/2026)"


def saldo() -> float:
    return fetch_all("SELECT ROUND(SUM(Credito - Deuda), 2) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,))[0]["s"]


if __name__ == "__main__":
    _assert_target_is_wc()
    if fetch_all("SELECT TOP 1 1 AS x FROM dbo.AplicacionesPago WHERE Anulada = 0 AND NotaConciliacion LIKE 'Copia de Lartirigoyen%'", ()):
        # Segunda pasada: la venta de granos 110 la cobró Lartirigoyen por OP 186151 (no cancela facturas): sin dólares.
        if fetch_all("SELECT 1 AS x FROM dbo.ValuacionProveedor WHERE IdContacto = ? AND Origen = 'Venta Granos' AND IdOrigen = 110 AND Dolares <> 0", (C,)):
            print("Respaldo verificado:", backup_verificado("lartirigoyen-valuacion-vg110-036"))
            execute_write_transaction([("UPDATE dbo.ValuacionProveedor SET Dolares = 0, Fuente = ?, Nota = 'Cobrada por OP 0012-186151, no cancela "
                                        "facturas' WHERE IdContacto = ? AND Origen = 'Venta Granos' AND IdOrigen = 110", (FUENTE, C))])
            bimonetaria.invalidar()
            r = bimonetaria.cargar_cuenta(C, refrescar=True)
            print("bimonetaria: $", r["saldoPesos"], "US$", r["saldoDolares"])
        # Tercera pasada: NC en US$ aplicadas a facturas en US$ de otro TC (NC 0149-562 a TC 17,29 sobre la FC 5499 a 24,475): la NC
        # cancela sus propios US$; el pago principal de la factura absorbe la diferencia para que la factura quede cubierta exacta.
        docs = {r["IdDeuda"]: r for r in fetch_all("SELECT c.IdDeuda, c.Moneda, c.[Tipo de Cambio] tc, v.ImporteDocumento imp FROM dbo.Compras c "
                                                     "JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda WHERE c.IdContacto = ?", (C,))}
        apps = fetch_all("SELECT OrigenMovimiento o, IdMovimientoOrigen i, IdDocumentoAplicado d, ImporteAplicado imp FROM dbo.AplicacionesPago "
                         "WHERE Anulada = 0 AND NotaConciliacion LIKE 'Copia de Lartirigoyen%'", ())
        ajustes = []
        for d, doc in docs.items():
            if doc["Moneda"] != "Dolares":
                continue
            propias = [a for a in apps if a["d"] == d]
            ncs = [a for a in propias if a["o"] == "comp-compra" and docs[a["i"]]["Moneda"] == "Dolares" and docs[a["i"]]["tc"] != doc["tc"]]
            if not ncs:
                continue
            exceso = sum(float(a["imp"]) / float(docs[a["i"]]["tc"]) - float(a["imp"]) / float(doc["tc"]) for a in ncs)
            mayor = max((a for a in propias if a["o"] != "comp-compra"), key=lambda a: float(a["imp"]))
            ajustes.append((VALUACION[mayor["o"]], mayor["i"], round(exceso, 4)))
        hechos = fetch_all("SELECT 1 AS x FROM dbo.ValuacionProveedor WHERE IdContacto = ? AND Nota LIKE 'Incluye ajuste por NC en US$%'", (C,))
        if ajustes and not hechos:
            print("Ajustes de valuación:", ajustes)
            print("Respaldo verificado:", backup_verificado("lartirigoyen-valuacion-nc-usd-036"))
            execute_write_transaction([("UPDATE dbo.ValuacionProveedor SET Dolares = Dolares - ?, Nota = 'Incluye ajuste por NC en US$ de otro TC "
                                        "aplicada a la misma factura' WHERE IdContacto = ? AND Origen = ? AND IdOrigen = ?", (e, C, o, i))
                                       for o, i, e in ajustes])
            bimonetaria.invalidar()
            r = bimonetaria.cargar_cuenta(C, refrescar=True)
            print("bimonetaria: $", r["saldoPesos"], "US$", r["saldoDolares"])
        raise SystemExit("Ya aplicado.")
    antes = saldo()
    docs = {r["IdDeuda"]: r for r in fetch_all("SELECT IdDeuda, Moneda, [Tipo de Cambio] tc FROM dbo.Compras WHERE IdContacto = ?", (C,))}
    usd = lambda d, imp: imp / float(docs[d]["tc"]) if docs[d]["Moneda"] == "Dolares" else 0.0
    st = [("UPDATE a SET Anulada = 1, MotivoAnulacion = 'Reemplazada por la imputación de Lartirigoyen (extranet 28/10/2026)', "
           "UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
           "WHERE a.TipoDocumento = 'CompraDeuda' AND a.Anulada = 0 AND c.IdContacto = ?", (U, C))]
    dolares = collections.defaultdict(float)
    for a in PLAN["aplicaciones"]:
        st.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, "
                   "Fecha, Usuario, Anulada, Origen, NotaConciliacion) VALUES (?, ?, 'CompraDeuda', ?, ?, SYSDATETIME(), ?, 0, 'manual', ?)",
                   (a["origen"], a["idMovimiento"], a["idDeuda"], a["importe"], U, NOTA.format(a["segun"]))))
        dolares[(a["origen"], a["idMovimiento"])] += usd(a["idDeuda"], a["importe"])
    for (o, i), d in dolares.items():
        if o == "comp-compra" and docs[i]["Moneda"] == "Dolares":
            continue  # NC en dólares: su valor en US$ es el propio comprobante
        st += [("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ? AND Origen = ? AND IdOrigen = ?", (C, VALUACION[o], i)),
               ("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (VALUACION[o], i, C, round(d, 4), FUENTE, None if d else "0 = documento de la subcuenta en pesos", U))]
    lineas = sorted({v["idLineaConsumo"] for v in PLAN["vinculosTarjeta"]})
    marcas = ",".join("?" * len(lineas))
    st += [(f"DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ? AND Origen = 'Tarjetas' AND IdOrigen IN "
            f"(SELECT IdVinculo FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdLineaConsumo IN ({marcas}))", (C, *lineas)),
           (f"DELETE v FROM dbo.Tarjetas_Resumenes_Lineas_Compras v JOIN dbo.Compras c ON c.IdDeuda = v.IdCompra "
            f"WHERE c.IdContacto = ? AND v.IdLineaConsumo IN ({marcas})", (C, *lineas))]
    for v in PLAN["vinculosTarjeta"]:
        pos = len(st)
        st.append(("INSERT INTO dbo.Tarjetas_Resumenes_Lineas_Compras (IdLineaConsumo, IdCompra, ImporteImputado) OUTPUT INSERTED.IdVinculo "
                   "VALUES (?, ?, ?)", (v["idLineaConsumo"], v["idCompra"], v["importe"])))
        d = usd(v["idCompra"], v["importe"])
        st.append(lambda r, p=pos, d=d: ("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario) "
                                         "VALUES ('Tarjetas', ?, ?, ?, ?, ?, ?)",
                                         (r[p], C, round(d, 4), FUENTE, None if d else "0 = documento de la subcuenta en pesos", U)))
    print("Respaldo verificado:", backup_verificado("lartirigoyen-aplicaciones-portal-036"))
    execute_write_transaction(st)
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Aplicaciones:", len(PLAN["aplicaciones"]), " vínculos de tarjeta:", len(PLAN["vinculosTarjeta"]))
    print("Saldo vista antes/después:", antes, saldo(), " bimonetaria: $", r["saldoPesos"], "US$", r["saldoDolares"])
