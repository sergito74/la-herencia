"""Cargill (258): ajustes de liquidaciones de granos cargados sin IVA 10,5% (PDF/portal los incluyen).
IdAjuste 151 (LPG 330118426339, $44.695,89 -> $49.388,96), 150 (330118440853, $7.307,84 -> $8.075,16),
191 (330124774457, bonif. flete $235.922,27 -> $260.694,10). Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

AJUSTES = {151: 148, 150: 147, 191: 187}


def main():
    _assert_target_is_wc()
    m = ','.join(map(str, AJUSTES))
    filas = fetch_all(f'SELECT a.IdAjuste,a.IdVenta,a.AlicuotaIVA,v.IdConsignatario FROM dbo.[Venta Granos_Ajustes] a JOIN dbo.[Venta Granos] v ON v.IdVenta=a.IdVenta WHERE a.IdAjuste IN ({m})')
    assert all(AJUSTES[f['IdAjuste']] == f['IdVenta'] and f['IdConsignatario'] == 258 for f in filas) and len(filas) == 3
    if all(f['AlicuotaIVA'] == 10.5 for f in filas):
        print('Nada pendiente.'); return
    backup = backup_verificado('cargill-ajustes-iva-036')
    with reconciliation_transaction():
        execute_write_transaction([(f'UPDATE dbo.[Venta Granos_Ajustes] SET AlicuotaIVA=10.5 WHERE IdAjuste IN ({m})', ())])
    print(fetch_all(f"SELECT IdOrigen,Credito FROM dbo.vw_MovimientosCuenta_Base WHERE Origen='Venta Granos' AND IdOrigen IN (147,148,187)"), backup)


if __name__ == '__main__': main()
