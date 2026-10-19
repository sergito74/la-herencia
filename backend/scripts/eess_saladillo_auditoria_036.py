"""036 — EESS Saladillo (30), 19/10/2026: auditoría de los tickets pagados con QR / App YPF contra el PDF del ticket.

Reemplaza las 7 NC "DESCAPP" de zafiro_eess_036 (se borran): las diferencias ticket − cargo de la tarjeta NO eran descuentos.
A. Descuento mal cargado (el ticket cobra el total con el descuento ya aplicado, sin IVA sobre el descuento):
   - 08934-39843 (03/02/2025): descuento $6.600 cargado como $5.454,55 → total $42.415,07 = Mercado Pago.
   - 08938-68681 (05/02/2025): descuento $3.100 cargado como $2.449 + IVA y los conceptos no gravados ($5.211,30) en el campo
     de IIBB → total $35.907,03 = Mercado Pago $35.907,02 + efectivo $0,01.
B. Percepción IIBB Bs As pagada en EFECTIVO en el surtidor (el ticket dice "Mercado Pago/App YPF $X + Efectivo $Y"); el
   total cargado ya estaba bien. Pago en efectivo con fondos propios de Sergio (Caja 'Particular S') + 'Devolucion' en su
   cuenta de socio, como los tickets YPF de la barrida del 17/10: 28/03/2025 $69,67; 22/04/2025 $42,48; 11/09/2025 $150,58;
   20/10/2025 $101,91; 22/10/2025 $86,68.
Idempotente.

Uso (desde backend/): python -m scripts.eess_saladillo_auditoria_036
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

C, U = 30, "Sergio (barrida 036)"
T39843, T68681 = 2143514965, 2143514964
EFECTIVO = [("2025-03-28", 69.67, "08938-00071647"), ("2025-04-22", 42.48, "08930-00049304"), ("2025-09-11", 150.58, "08934-00048739"),
            ("2025-10-20", 101.91, "08930-00059914"), ("2025-10-22", 86.68, "08938-00064116"), ("2025-02-05", 0.01, "08938-00068681")]

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("eess-saladillo-auditoria-036"))
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] LIKE 'DESCAPP %'", C)
        for (nc,) in cur.fetchall():
            cur.execute("UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = 'NC DESCAPP borrada: no era descuento (barrida 036)', "
                        "UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() WHERE OrigenMovimiento = 'comp-compra' AND IdMovimientoOrigen = ? "
                        "AND Anulada = 0", U, nc)
            cur.execute("DELETE FROM dbo.Det_Compras WHERE IdCompra = ?", nc)
            cur.execute("DELETE FROM dbo.Compras WHERE IdDeuda = ?", nc)
        cur.execute("UPDATE dbo.Det_Compras SET [Precio Unitario] = -6600, IVA = 0, [Producto/Servicio] = 'Descuento QR' "
                    "WHERE IdCompra = ? AND [Precio Unitario] < 0", T39843)
        cur.execute("UPDATE dbo.Det_Compras SET [Precio Unitario] = -3100, IVA = 0 WHERE IdCompra = ? AND [Precio Unitario] < 0", T68681)
        cur.execute("UPDATE dbo.Compras SET [Conceptos no gravados] = 5211.30, [Ingresos Brutos] = 0 WHERE IdDeuda = ? AND [Ingresos Brutos] = 5211.30", T68681)
        for fecha, importe, nro in EFECTIVO:
            motivo = f"Pago de percepciones del ticket EESS Saladillo {nro} (efectivo ${importe:,.2f}) con fondos propios de Sergio".replace(".", "#").replace(",", ".").replace("#", ",") \
                if importe > 0.01 else f"Pago en efectivo del ticket EESS Saladillo {nro} ($0,01) con fondos propios de Sergio"
            cur.execute("SELECT 1 FROM dbo.[Pagos efectivo] WHERE IdContacto = ? AND Fecha = ? AND [Importe imputado] = ? AND Caja = 'Particular S'", C, fecha, importe)
            if not cur.fetchone():
                cur.execute("INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, [Importe imputado]) "
                            "VALUES (?, 1, 3, ?, 'White', 'Particular S', ?)", C, fecha, importe)
                cur.execute("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio, Tipo, Importe, Fecha, Medio, Motivo, Usuario, Anulada, ImporteUSD, ImporteKgCarne) "
                            "VALUES (1, 'Devolucion', ?, ?, 'efectivo', ?, ?, 0, 0, 0)", importe, fecha, motivo, U)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    from src.db.connection import fetch_all
    for t in (T39843, T68681):
        print(t, fetch_all("SELECT ImporteDocumento t FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda = ?", (t,))[0]["t"])
    print("Saldo al corte:", round(sum(r["Deuda"] - r["Credito"] for r in fetch_all(
        "SELECT Deuda, Credito FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ? AND Fecha <= '2026-09-30'", (C,))), 2))
