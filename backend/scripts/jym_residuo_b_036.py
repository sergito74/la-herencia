"""J y M de la Serna (47): residuo histórico −$5.033,94 (ventas 2015-2020), Sergio 21/10/2026.

La vista descuenta comisión (3% + IVA) también sobre la parte B; J y M no la descontó del efectivo B (cobrado completo).
Sergio: la comisión sobre B queda fuera del sistema; no se registra. La cuenta debe cerrar en cero: un ajuste por venta
(AjustesCuentaCorriente, lado Crédito) por la diferencia de cada ciclo, no un ajuste general.
Evidencia: resumen de cuenta J y M 01/04/2016-30/06/2017 (saldo 0), liquidación 0001-20833 y NC 0002-33 (mails).
Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

C = 47
USUARIO = 'Sergio (036, revisión 21/10/2026)'
# (fecha, venta, parte B, diferencia del ciclo)
AJUSTES = [('2015-11-25', '0001-00020833', 69973.17, 2319.42), ('2017-04-05', '0003-00000025', 7672.98, 254.38),
           ('2018-07-23', '0003-00001762', 26350.84, 872.69), ('2019-05-08', '0003-00003456', 20070.12, 665.21),
           ('2020-03-10', '0003-00005302', 27786.98, 922.24)]


def main():
    _assert_target_is_wc()
    st = []
    for f, venta, b, imp in AJUSTES:
        motivo = f'J y M venta {venta}: comisión sobre parte B (${b:,.2f}) fuera de sistema; J y M no la descontó del efectivo B'
        if not fetch_all('SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=? AND Motivo LIKE ?', (C, f'J y M venta {venta}:%')):
            st.append(('INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario,FechaAlta) VALUES (?,?,?,?,?,?,SYSDATETIME())',
                       (C, f, 'Credito', imp, motivo, USUARIO)))
    if st:
        print(backup_verificado('jym-residuo-b-036'))
        with reconciliation_transaction():
            execute_write_transaction(st)
    invalidar()
    print('saldo', round(cargar_cuenta(C, refrescar=True)['saldoPesos'], 2))


if __name__ == '__main__': main()
