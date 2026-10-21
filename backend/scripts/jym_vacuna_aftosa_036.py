"""J y M de la Serna (47): AJ 000000293 del 05/11/2025, "VACUNA AFTOSA APLICADA EN REMATE OCTUBRE 2025", $17.880,00.
Fuente: resumen de cuenta J y M 01/01/2025-30/06/2026 (mail 25/11/2025) y OP 000109105 del 13/11/2025, que lo descuenta junto
con el flete de Gutiérrez (AJ 254). Era el faltante de las ventas de octubre 2025 ($17.879,98).
Regla de descuentos de consignatarios (Ferias del Centro): documento del cargo, rubro Aranceles Vacunacion, centro Ganadería
(2), destino General. Compra tipo X "AJ 0000293" a J y M. Idempotente.
"""
from datetime import datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

C = 47
NRO = 'AJ 0000293'


def main():
    _assert_target_is_wc()
    if not fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?', (C, NRO)):
        print(backup_verificado('jym-vacuna-aftosa-036'))
        f = datetime(2025, 11, 5)
        cab = {'idContacto': C, 'fecha': f, 'tipoDocumento': 'Factura', 'tipo': 'X', 'numeroDocumento': NRO, 'moneda': 'Pesos',
               'tipoDeCambio': 1, 'ajustaTipoCambio': False}
        lin = {'productoServicio': 'Vacuna aftosa aplicada en remate octubre 2025', 'cantidad': 1, 'precioUnitario': 17880, 'iva': 0,
               'ajusteFinanciero': False, 'idCentroCosto': 2, 'idDestino': 1, 'idRubro': 2047893467, 'campaña': 'No Aplica', 'idCampania': 20}
        with reconciliation_transaction():
            execute_write_transaction([compras._cabecera_insert_statement(cab), compras._linea_insert_statement(lin),
                                       compras._vencimiento_insert_statement({'fechaVencimiento': f})])
    invalidar()
    print('saldo', round(cargar_cuenta(C, refrescar=True)['saldoPesos'], 2))


if __name__ == '__main__': main()
