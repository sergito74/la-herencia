"""Banco Nación (369): préstamos (Sergio 22/10/2026).

Home banking BNA al 22/10/2026 (captura de Sergio): un solo préstamo vigente, 0019136529 "REG 750 INV MIPY A7140 SGR"
(el de Garantizar, acreditado 14/03/2023 por $1.100.000), saldo de capital $137.500, próxima cuota 22/02/2027. Los demás
préstamos están cancelados. Capital recibido en los extractos: $62.447,50 (28/09/2017, BNA 12490, estaba sin contacto),
$1.100.000 (03/2023) y $6.000.000 (08/2023). El de $895.000 (01/10/2021) se pagó directo a Edecán (cuenta cerrada) y no pasa
por esta cuenta.
Sin cronograma por préstamo: los intereses = cuotas pagadas − capital recibido + capital pendiente, en un comprobante interno
"INT369-PREST" (rubro Financiamiento, centro Administración General). La cuenta queda en −$137.500 (capital adeudado).
Idempotente.
"""
from datetime import datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

C = 369
CAPITAL_PENDIENTE = 137500.00
NRO = 'INT369-PREST'


def main():
    _assert_target_is_wc()
    print(backup_verificado('banco-nacion-prestamos-036'))
    with reconciliation_transaction():
        execute_write_transaction([('UPDATE dbo.[Movimientos BNA] SET IdContacto=? WHERE IdMovimientoBNA=12490 AND ISNULL(IdContacto,0)=0', (C,))])
    invalidar()
    if not fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?', (C, NRO)):
        saldo = cargar_cuenta(C, refrescar=True)['saldoPesos']
        intereses = round(saldo + CAPITAL_PENDIENTE, 2)
        f = datetime(2026, 8, 27)
        cab = {'idContacto': C, 'fecha': f, 'tipoDocumento': 'Factura', 'tipo': 'X', 'numeroDocumento': NRO, 'moneda': 'Pesos',
               'tipoDeCambio': 1, 'ajustaTipoCambio': False}
        lin = {'productoServicio': 'Intereses préstamos BNA 2017-2026', 'cantidad': 1, 'precioUnitario': intereses, 'iva': 0,
               'ajusteFinanciero': False, 'idCentroCosto': 3, 'idDestino': 1, 'idRubro': 2047893443, 'campaña': 'No Aplica', 'idCampania': 20}
        with reconciliation_transaction():
            execute_write_transaction([compras._cabecera_insert_statement(cab), compras._linea_insert_statement(lin),
                                       compras._vencimiento_insert_statement({'fechaVencimiento': f})])
        print('intereses', intereses)
        invalidar()
    print('saldo BNA', cargar_cuenta(C, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
