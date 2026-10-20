"""Cargill (258): el 28/07/2020 Cargill pidió $88.840,10 (FC 1125-2786 $65.153,84 + reajuste $13.349,39 + FC 1125-3153
$10.336,87) y se transfirieron $88.410,10 (comprobante mails/20200728_1437_Transferencia Cargill 20200728.pdf).
Cargill no reclamó la diferencia (estados de cuenta 03/09 y 01/10/2020 sin pendientes en pesos). Sergio 20/10/2026:
registrar el ajuste. NC "AJ 2" por $430 con el reparto de la FC 1125-2786. Idempotente.
"""
from datetime import datetime

from scripts.cargill_comprobantes_faltantes_036 import repartir
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

NRO = 'AJ 2'


def main():
    _assert_target_is_wc()
    if fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=258 AND [Nro Documento]=?', (NRO,)):
        print('Nada pendiente.'); return
    backup = backup_verificado('cargill-ajuste-pago-2020-036')
    cab = {'idContacto': 258, 'fecha': datetime(2020, 7, 28), 'tipoDocumento': 'Nota de Crédito', 'tipo': 'A', 'numeroDocumento': NRO,
           'moneda': 'Pesos', 'tipoDeCambio': 1}
    lineas = repartir('Dif. no reclamada pago 28/07/2020', -430.0, 0, 'ref:1125-00002786', False)
    st = [compras._cabecera_insert_statement(cab)] + [compras._linea_insert_statement(l) for l in lineas] + \
         [compras._vencimiento_insert_statement({'fechaVencimiento': cab['fecha']})]
    with reconciliation_transaction():
        i = execute_write_transaction(st)[0]
        g = fetch_all('SELECT GranTotal g FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda=?', (i,))[0]['g']
        assert abs(g + 430) < 0.01, g
    print(i, g, backup)


if __name__ == '__main__': main()
