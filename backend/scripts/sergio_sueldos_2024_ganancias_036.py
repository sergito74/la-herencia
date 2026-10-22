"""Cuenta 375 (Sergio), sueldos 2024: devolución de Ganancias de julio y redondeos según los recibos (Sergio 22/10/2026, punto 6).

Recibo julio 2024: sueldo $950.000, Ganancias 4ta −$63.326,76 (devolución = retenciones feb–jun: 9.248,64 + 12.944,86 +
13.122,83 + 13.877,85 + 14.132,58), redondeo $0,24 → neto $1.013.327, pagado en dos transferencias ($896.826 + $116.501).
El sistema tenía las retenciones como crédito (tabla Retenciones) pero no la devolución: se agrega como Ajuste No Remunerativo
en la liquidación de julio. Redondeos del recibo: febrero $0,64 y julio $0,24. Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

JULIO, FEBRERO = 1829633170, 1829633137


def main():
    _assert_target_is_wc()
    if fetch_all('SELECT 1 x FROM dbo.Remuneraciones WHERE IdSalario=? AND ISNULL([Ajuste No Remunerativo],0)=63326.76', (JULIO,)):
        print('ya aplicado'); return
    print(backup_verificado('sergio-sueldos-2024-ganancias-036'))
    with reconciliation_transaction():
        execute_write_transaction([
            ('UPDATE dbo.Remuneraciones SET [Ajuste No Remunerativo]=63326.76, Redondeo=0.24 WHERE IdSalario=? AND IdContacto=375', (JULIO,)),
            ('UPDATE dbo.Remuneraciones SET Redondeo=0.64 WHERE IdSalario=? AND IdContacto=375', (FEBRERO,))])
    invalidar()
    print('375', cargar_cuenta(375, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
