"""036 — Aroca (4662) y Breccia (5665), 19/10/2026: fletes de hacienda pagados por J y M de la Serna desde nuestra cuenta.

Dato de Sergio: Aroca (FC 00004-81, $61.710, 18/05/2026, "flete a feria de La Serna") y Breccia (FC C 00002-23, $120.000,
11/05/2026) son fletes de hacienda que pagó J y M de la Serna desde la cuenta corriente de Giamigli (práctica habitual; no hay
detalle actualizado de esa cuenta). Mismo patrón que los fletes anteriores (Transporte Don Miguel, HL, Ballesteros): pago en
la cuenta del proveedor con Caja 'J y M de La Serna' y, en la cuenta de J y M (47), "Pago proveedor" (tipo 3, forma 19) negativo.
Fecha = la de la factura (no hay fecha del pago de J y M). Idempotente.

Uso (desde backend/): python -m scripts.fletes_jym_aroca_breccia_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

JYM = 47
FLETES = [(4662, "2026-05-18", 61710.00, 2143521583), (5665, "2026-05-11", 120000.00, 2143522639)]

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("fletes-jym-036"))
    st = []
    for c, f, imp, deuda in FLETES:
        if fetch_all("SELECT 1 AS x FROM dbo.[Pagos efectivo] WHERE IdContacto = ? AND Fecha = ? AND [Importe imputado] = ? AND Caja = 'J y M de La Serna'", (c, f, imp)):
            continue
        st += [("INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, [Importe imputado]) "
                "VALUES (?, 1, 3, ?, 'White', 'J y M de La Serna', ?)", (c, f, imp)),
               ("INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, [Importe imputado]) "
                "VALUES (?, 3, 19, ?, 'White', 'J y M de La Serna', ?)", (JYM, f, -imp)),
               ("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, Fecha, "
                "Usuario, Anulada, Origen, NotaConciliacion) SELECT 'efectivo', MAX(IdPagoEfectivo), 'CompraDeuda', ?, ?, SYSDATETIME(), "
                "'Sergio (barrida 036)', 0, 'manual', 'Flete pagado por J y M de la Serna desde la cuenta de Giamigli' FROM dbo.[Pagos efectivo] "
                "WHERE IdContacto = ? AND Fecha = ? AND [Importe imputado] = ? AND Caja = 'J y M de La Serna'", (deuda, imp, c, f, imp))]
    if st:
        execute_write_transaction(st)
    for c in (4662, 5665, JYM):
        print(c, round(sum(r["Deuda"] - r["Credito"] for r in fetch_all("SELECT Deuda, Credito FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (c,))), 2))
