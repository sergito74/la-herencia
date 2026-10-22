"""Ventas de granos 2 (12/02/2011, avena 10.300 kg, $7.004) y 3 (04/08/2011, maíz 4.000 kg) cobradas en efectivo: el comprador
es Luis Albo (contacto 99, tipo Comprador; la caja del cobro figura como "Luis Albo"), no Giamigli de Bolívar (386 = la propia
empresa). Ya venían así de Access. Pasan venta y cobro (Pagos efectivo 106, 107) a Luis Albo. Sergio 21/10/2026. Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuentas, invalidar
from src.features.vinculos.backup import backup_verificado


def main():
    _assert_target_is_wc()
    print(backup_verificado('giamigli-ventas-luis-albo-036'))
    with reconciliation_transaction():
        execute_write_transaction([
            ('UPDATE dbo.[Venta Granos] SET IdConsignatario=99 WHERE IdVenta IN (2,3) AND IdConsignatario=386', ()),
            ('UPDATE dbo.[Pagos efectivo] SET IdContacto=99 WHERE IdPagoEfectivo IN (106,107) AND IdContacto=386', ()),
        ])
    invalidar()
    for c, x in cargar_cuentas([99, 386]).items():
        print(c, x['saldoPesos'], [(str(f['fecha']), f['origenTipo'], f['deudaPesos'], f['creditoPesos']) for f in x['filas']])


if __name__ == '__main__': main()
