"""Cargill (258): baja de incobrables de $1.713,76 (nota de recepción de valores 0000120784 del 26/02/2025,
"Instrumento de pago: Baja incobrables", cancela el saldo de FC 5850-00009422). No hubo fondos: se registra como
NC de ajuste "AJ 1" con el reparto de la factura. Comprobante: mails/20250305_2358_Documentos Fiscales.zip. Idempotente.
"""
from datetime import datetime

from scripts.cargill_comprobantes_faltantes_036 import repartir
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

NRO = 'AJ 1'


def main():
    _assert_target_is_wc()
    if fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=258 AND [Nro Documento]=?', (NRO,)):
        print('Nada pendiente.'); return
    backup = backup_verificado('cargill-baja-incobrable-036')
    cab = {'idContacto': 258, 'fecha': datetime(2025, 2, 26), 'tipoDocumento': 'Nota de Crédito', 'tipo': 'A', 'numeroDocumento': NRO,
           'moneda': 'Pesos', 'tipoDeCambio': 1}
    lineas = repartir('Baja incobrables rec 120784 FC 5850-9422', -1713.76, 0, 'ref:5850-00009422', False)
    st = [compras._cabecera_insert_statement(cab)] + [compras._linea_insert_statement(l) for l in lineas] + \
         [compras._vencimiento_insert_statement({'fechaVencimiento': cab['fecha']})]
    with reconciliation_transaction():
        i = execute_write_transaction(st)[0]
        g = fetch_all('SELECT GranTotal g FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda=?', (i,))[0]['g']
        assert abs(g + 1713.76) < 0.01, g
    print(i, g, backup)


if __name__ == '__main__': main()
