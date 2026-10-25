"""036: 5 pagos en efectivo de Access (caja «La Herencia») que faltaban en el libro de la caja Giamigli 2011–2015.

Sergio 25/10/2026, «Adelante con estos ajustes»: 2137 Sergio empleado (sueldo, parte en efectivo), 363 AgroNacion adm.
anterior (cierra con su factura del mismo día), 1563 Municipalidad (guías 13/03/2014), 2638 XXXXXXXXX (segundo pago de
$300 del 07/10/2013, cancela otra factura S/D) y 708 Agrovet (factura 0001-00077521). Egresos con IdPagoEfectivo; el
remanente no identificado (mov. 1947) absorbe la diferencia y los saldos de la caja no cambian. Idempotente.
"""

from decimal import Decimal

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

USUARIO = "Sergio (036, reconstrucción caja 2011-2015 25/10/2026)"
PAGOS = (2137, 363, 1563, 2638, 708)
REMANENTE = 1947


def main():
    _assert_target_is_wc()
    p = fetch_all("""SELECT p.IdPagoEfectivo id, CONVERT(date,p.Fecha) f, p.[Importe imputado] i, p.Cuenta, c.[Razon Social] r
        FROM dbo.[Pagos efectivo] p LEFT JOIN dbo.Contactos c ON c.IdContacto=p.IdContacto
        WHERE p.IdPagoEfectivo IN (%s) AND NOT EXISTS (SELECT 1 FROM dbo.MovimientosCajaEfectivo m WHERE m.IdPagoEfectivo=p.IdPagoEfectivo AND m.Anulada=0)"""
                  % ",".join(map(str, PAGOS)))
    if not p:
        print("ya aplicado"); return
    total = sum(Decimal(str(x["i"])) for x in p)
    rem = Decimal(str(fetch_all("SELECT Importe FROM dbo.MovimientosCajaEfectivo WHERE IdMovimiento=?", (REMANENTE,))[0]["Importe"]))
    print(backup_verificado("caja_giamigli_5_pagos_036"))
    st = [("INSERT INTO dbo.MovimientosCajaEfectivo (Caja,Fecha,Concepto,Detalle,Importe,Cuenta,IdPagoEfectivo,Usuario) VALUES ('GiamigliSA',?,?,?,?,?,?,?)",
           (str(x["f"]), x["r"], f"Pago en efectivo de Access (caja La Herencia) {x['id']}, faltaba en la planilla", -Decimal(str(x["i"])),
            "B" if x["Cuenta"] == "Blue" else "White", x["id"], USUARIO)) for x in p]
    st.append(("UPDATE dbo.MovimientosCajaEfectivo SET Importe=? WHERE IdMovimiento=?", (rem + total, REMANENTE)))
    execute_write_transaction(st)
    print(len(p), "egresos", total, "| remanente", rem, "->", rem + total)


if __name__ == "__main__":
    main()
