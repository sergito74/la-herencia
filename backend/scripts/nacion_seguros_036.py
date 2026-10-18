"""036 — Nación Seguros (289), 18/10/2026: pólizas de granizo en dólares 2022/23 según sus PDFs.

Las tres pólizas (FC 60446 maíz, 62593 soja 1ª, 63288 soja 2ª) y sus NC del 15/05/2023 estaban infladas: tenían renglones
"Dif. TC 238,25 - <TC factura>" cargados en DÓLARES y el campo "Ley de Sellos" con importes en PESOS dentro de documentos en
dólares. Se rearman con el PDF: prima + recargo financiero (IVA 21%) + sellos/tasa (en "Ley de Sellos"; en las NC también la
percepción de IVA). Premios: US$573,99 / 545,42 / 267,42; NC: -29,41 / -27,94 / -13,70.

Se pagaron con tarjeta al TC 238,25 (cláusula de la póliza: dólar BNA del día hábil anterior al pago) — $136.753 / $129.946,72
/ $63.713,15 y los reintegros de las NC $7.006,81 / $6.657,11 / $3.264,36 — así que en dólares cierran exacto. La diferencia
entre ese TC y el TC impositivo de cada factura es solo de pesos: un ajuste de cuenta corriente por póliza (no mueve dólares).
Las pólizas en pesos (2016-2022) y sus pagos cierran en pesos y se valúan en 0 dólares.
Idempotente.

Uso (desde backend/): python -m scripts.nacion_seguros_036
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U, TC_PAGO = 289, "Sergio (barrida 036)", 238.25
# IdDeuda: (prima, recargo, sellos/otros en USD, renglón prima, renglón recargo, TC factura, US$ premio)
DOCS = {
    2143513999: (452.02, 18.08, 5.17, 2141374468, 2141374469, 159.71, 573.99),
    2143514001: (429.52, 17.18, 4.91, 2141374472, 2141374473, 176.05, 545.42),
    2143514000: (210.60, 8.42, 2.41, 2141374470, 2141374471, 185.32, 267.42),
    2143514257: (-22.60, -0.90, -0.97, 2141375230, 2141375231, 159.71, -29.41),
    2143514145: (-21.48, -0.86, -0.91, 2141374990, 2141374991, 176.05, -27.94),
    2143514144: (-10.53, -0.42, -0.45, 2141374988, 2141374989, 185.32, -13.70),
}
# pago con tarjeta (o reintegro) de cada documento: (Origen, IdOrigen)
PAGOS = {2143513999: ("Tarjetas", 5585), 2143514001: ("Tarjetas", 5586), 2143514000: ("Tarjetas", 5587),
         2143514257: ("Tarjetas", 5534), 2143514145: ("Tarjetas", 5536), 2143514144: ("Tarjetas", 5535)}
POLIZA = {2143513999: "60446 (maíz)", 2143514001: "62593 (soja 1ª)", 2143514000: "63288 (soja 2ª)",
          2143514257: "NC 60446", 2143514145: "NC 62593", 2143514144: "NC 63288"}

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("nacion-seguros-036"))
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM dbo.AjustesCuentaCorriente WHERE IdContacto = ? AND Motivo LIKE 'Diferencia de cambio al pago de la póliza%'", C)
        cur.execute("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ?", C)
        for idc, (prima, rec, otros, r_prima, r_rec, tc, premio) in DOCS.items():
            cur.execute("DELETE FROM dbo.Det_Compras WHERE IdCompra = ? AND IdDetalleCompra NOT IN (?, ?)", idc, r_prima, r_rec)
            cur.execute("UPDATE dbo.Det_Compras SET [Precio Unitario] = ?, Cantidad = 1, IVA = 21 WHERE IdDetalleCompra = ?", prima, r_prima)
            cur.execute("UPDATE dbo.Det_Compras SET [Precio Unitario] = ?, Cantidad = 1, IVA = 21 WHERE IdDetalleCompra = ?", rec, r_rec)
            cur.execute("UPDATE dbo.Compras SET [Ingresos Brutos] = 0, PercepcionIVA = 0, [Conceptos no gravados] = 0, [Gastos Varios] = 0, "
                        "[Ley de Sellos] = ? WHERE IdDeuda = ? AND IdContacto = ? AND Moneda = 'Dolares'", otros, idc, C)
            # Dólares del pago = premio; la diferencia de TC va a la cuenta en pesos
            o, i = PAGOS[idc]
            cur.execute("SELECT Deuda, Credito FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ? AND Origen = ? AND IdOrigen = ?", C, o, i)
            d, cr = cur.fetchone()
            pagado = float(cr or 0) - float(d or 0)
            cur.execute("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) VALUES "
                        "(?, ?, ?, ?, 'Póliza Nación Seguros: premio en US$ pagado al BNA del día anterior al pago (238,25)', ?, ?, SYSDATETIME())",
                        o, i, C, abs(premio), POLIZA[idc], U)
            dif = round(pagado - premio * tc, 2)
            if abs(dif) >= 0.01:
                cur.execute("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto, Fecha, Lado, Importe, Motivo, Usuario) "
                            "SELECT ?, Fecha, ?, ?, ?, ? FROM dbo.Compras WHERE IdDeuda = ?", C, "Deuda" if dif > 0 else "Credito", abs(dif),
                            f"Diferencia de cambio al pago de la póliza {POLIZA[idc]}: US${abs(premio):,.2f} pagados a TC {TC_PAGO} "
                            f"(BNA día anterior al pago, cláusula de la póliza) vs TC impositivo {tc}.", U, idc)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    # Los ajustes de diferencia de cambio son solo de pesos
    for a in fetch_all("SELECT IdAjuste FROM dbo.AjustesCuentaCorriente WHERE IdContacto = ? AND Motivo LIKE 'Diferencia de cambio al pago de la póliza%'", (C,)):
        from src.db.connection import execute_write_transaction
        execute_write_transaction([("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) VALUES "
                                    "('Ajuste Interno', ?, ?, 0, 'Diferencia de cambio solo en pesos', NULL, ?, SYSDATETIME())", (a["IdAjuste"], C, U))])
    # Movimientos en pesos (pólizas en pesos 2016-2022 y sus pagos): cierran en pesos y no mueven dólares
    from src.db.connection import execute_write_transaction
    bimonetaria.invalidar()
    ya = {(r["Origen"], int(r["IdOrigen"])) for r in fetch_all("SELECT Origen, IdOrigen FROM dbo.ValuacionProveedor WHERE IdContacto = ?", (C,))}
    nuevos = [(f["origenTipo"], f["idOrigen"]) for f in bimonetaria.cargar_cuenta(C, refrescar=True)["filas"]
              if f["moneda"] != "Dolares" and (f["origenTipo"], f["idOrigen"]) not in ya]
    execute_write_transaction([("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) VALUES "
                                "(?, ?, ?, 0, 'Movimiento en pesos de pólizas en pesos (cierra en pesos)', NULL, ?, SYSDATETIME())", (o, i, C, U))
                               for o, i in nuevos])
    for idc in DOCS:
        print(idc, fetch_all("SELECT ImporteDocumento t FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda = ?", (idc,))[0]["t"])
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo: pesos", r["saldoPesos"], " US$", r["saldoDolares"], r["gobierna"])
