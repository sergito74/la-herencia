"""Breccia (5665), FC C 00002-00000023 del 11/05/2026, $120.000: NO es un flete pagado por J y M de la Serna (Sergio
21/10/2026: "es una factura que me mandó un plomero que hizo trabajos de mantenimiento en el campo; no tiene nada que ver").
Deshace lo cargado por fletes_jym_aroca_breccia_036 (19/10/2026) solo para Breccia: anula la aplicación del pago y borra el
pago en caja "J y M de La Serna" (Breccia) y su contrapartida "Pago proveedor" en J y M (47). La factura queda impaga hasta
saber cómo se pagó. Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

FILTRO = "Fecha='2026-05-11' AND Caja='J y M de La Serna' AND ABS([Importe imputado])=120000"


def main():
    _assert_target_is_wc()
    pagos = fetch_all(f"SELECT IdPagoEfectivo i, IdContacto c FROM dbo.[Pagos efectivo] WHERE IdContacto IN (5665,47) AND {FILTRO}")
    if pagos:
        print(backup_verificado('breccia-fuera-jym-036'))
        ids = [p['i'] for p in pagos]
        with reconciliation_transaction():
            execute_write_transaction(
                [("UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion=?,FechaAnulacion=SYSDATETIME() "
                  "WHERE OrigenMovimiento='efectivo' AND IdMovimientoOrigen=? AND Anulada=0",
                  ('Breccia no es flete de J y M (plomero, mantenimiento campo). Sergio 21/10/2026', 'Sergio (036, revisión 21/10/2026)', i)) for i in ids]
                + [(f"DELETE FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=? AND {FILTRO}", (i,)) for i in ids])
        print('borrados', pagos)
    invalidar()
    for c in (5665, 47):
        print(c, round(cargar_cuenta(c, refrescar=True)['saldoPesos'], 2))


if __name__ == '__main__': main()
