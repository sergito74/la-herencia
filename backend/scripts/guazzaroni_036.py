"""036 — Guazzaroni Greco (604), 18/10/2026: cuenta según el resumen de cuenta corriente de Guazzaroni (22/06/2026, mail de
Melina García) y los comprobantes recibidos por mail.

1. Faltaban FC 0037-3310 (US$414,46) y 0037-3313 (US$3.271,13) del 13/04/2026 y la NC 0023-13569 (US$3.442,53, 22/04/2026):
   la NC anula las FC 3231/3233 ("cambia cond. de pago") y las 3310/3313 las refacturan en CANJE DIRECTO, vto. 31/12/2026.
2. Imputaciones como las aplicó Guazzaroni: NC 11801 → FC 1670; transferencia Galicia 3024 ($321.656,51) → FC 1669 (US$216,86,
   cancelada al TC 1444,5) + ND 0023-24007 ($48.412,91, diferencia de cambio). La ND es ajuste de TC (no mueve dólares) y el
   pago se valúa en los US$216,86 que acreditó Guazzaroni.
Queda pendiente, no vencido, la deuda en dólares del canje soja 26/27 (FC 3310, 3313 y 4338). Idempotente.

Uso (desde backend/): python -m scripts.guazzaroni_036
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U = 604, "Sergio (barrida 036)"
FC1669, FC1670, NC11801, ND24007, FC3231, FC3233 = 2143515118, 2143515119, 2143515145, 2143515381, 2143516381, 2143516382
CAB = "Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], [Fecha Vto], [Documento Original], " \
      "[Ingresos Brutos], PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], [Ley de Sellos], " \
      "[Res gral 4169/96], [Ajusta Tipo Cambio]"
# Nro: (fecha, tipo, TC, vto, pdf, [(renglón modelo, descripción, cantidad, precio US$, IVA)])
NUEVOS = {
    "0037-00003310": ("2026-04-13", "Factura", 1370.0, "2026-12-31", "20260413_Guazzaroni 001.pdf",
                      [(FC3231, "HERB GLIFOSATO 66% x 20 Lts", 4, 85.6325, 21)]),
    "0037-00003313": ("2026-04-13", "Factura", 1370.0, "2026-12-31", "20260413_Guazzaroni 002.pdf",
                      [(FC3233, "MZCLA 7N-39P-00-5S", 3.5, 845.80, 10.5)]),
    "0023-00013569": ("2026-04-22", "Nota de Crédito", 1368.0, "2026-04-22", "20260422_Guazzaroni.pdf",
                      [(FC3233, "NC FC 3233 MZCLA 7N-39P (cambia cond.)", 3.5, -750.0, 10.5),
                       (FC3231, "NC FC 3231 GLIFOSATO (cambia cond.)", 4, -80.0, 21),
                       (FC3233, "NC Fletes fertilizantes", 3.5, -40.0, 10.5)]),
}
APLIC = [("comp-compra", NC11801, FC1670, round(483.04 * 1260, 2)),
         ("galicia", 3024, FC1669, 273243.60), ("galicia", 3024, ND24007, 48412.91),
         ("comp-compra", None, FC3231, None), ("comp-compra", None, FC3233, None)]

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("guazzaroni-036"))
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        ids = {}
        for nro, (f, tipo, tc, vto, pdf, renglones) in NUEVOS.items():
            cur.execute("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", C, nro)
            fila = cur.fetchone()
            if fila:
                ids[nro] = fila[0]
                cur.execute("DELETE FROM dbo.Det_Compras WHERE IdCompra = ?", fila[0])
            else:
                doc = f"04 2026 - 03 2027\\{pdf}#04 2026 - 03 2027\\{pdf}#"
                cur.execute(f"INSERT INTO dbo.Compras ({CAB}) OUTPUT INSERTED.IdDeuda VALUES (?, ?, 'A', ?, ?, 'Dolares', ?, ?, ?, "
                            "0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", f, C, tipo, nro, tc, vto, doc)
                ids[nro] = cur.fetchone()[0]
            for modelo, desc, cant, pu, iva in renglones:
                cur.execute("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, "
                            "IdRubro, IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) SELECT TOP 1 ?, ?, ?, 0, IdCentroCostos, "
                            "IdDestino, IdRubro, IdCampaña, [Campaña], ?, ?, 0 FROM dbo.Det_Compras WHERE IdCompra = ? ORDER BY IdDetalleCompra",
                            ids[nro], cant, desc, pu, iva, modelo)
        cur.execute("UPDATE dbo.Compras SET [Ajusta Tipo Cambio] = 1 WHERE IdDeuda = ?", ND24007)
        cur.execute("UPDATE a SET Anulada = 1, MotivoAnulacion = 'Reemplazada según resumen de Guazzaroni (barrida 036)', UsuarioAnulacion = ?, "
                    "FechaAnulacion = SYSDATETIME() FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
                    "WHERE c.IdContacto = ? AND a.Anulada = 0", U, C)
        nc = ids["0023-00013569"]
        aplic = APLIC[:3] + [("comp-compra", nc, FC3231, round(387.20 * 1368, 2)), ("comp-compra", nc, FC3233, round(3055.33 * 1368, 2))]
        for m, i, d, x in aplic:
            cur.execute("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, "
                        "ImporteAplicado, Fecha, Usuario, Anulada, Origen, NotaConciliacion) VALUES (?, ?, 'CompraDeuda', ?, ?, SYSDATETIME(), "
                        "?, 0, 'manual', 'Barrida 036: según resumen de cuenta Guazzaroni 22/06/2026')", m, i, d, x, U)
        cur.execute("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ?", C)
        cur.execute("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) VALUES "
                    "('Galicia', 3024, ?, 216.86, 'Resumen cta. cte. Guazzaroni 22/06/2026: cancela FC 1669 al TC 1444,5', NULL, ?, SYSDATETIME())", C, U)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo: pesos", r["saldoPesos"], " US$", r["saldoDolares"], r["gobierna"])
