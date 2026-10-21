"""Galicia 2658 (10/07/2025, crédito $20.174,34, "SERVICIO PAGO A PROVEEDORES GALICIA BROKER ASESO 30708099119"): NO es de
J y M de la Serna. Sergio 21/10/2026: es un reconocimiento comercial de Galicia Seguros por gastos bancarios generados en el
proceso de pago; no hay nota de crédito que lo avale.
El importador lo había asignado a J y M (47) por la leyenda (CUIT 33594092479), que ese día viene cruzada entre movimientos.
- Reasigna el crédito a Galicia Seguros (575) (ReasignacionesContacto).
- Nota de crédito interna en pesos "NCI575-250710" por $20.174,34 (rubro Gastos bancarios, centro 3, destino 1), que el
  cobro cancela: Galicia Seguros (cerrada) no cambia de saldo.
Idempotente.
"""
from datetime import datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

C, JYM, MOV, IMP = 575, 47, 2658, 20174.34
NRO = 'NCI575-250710'
USUARIO = 'Sergio (036, revisión 21/10/2026)'


def main():
    _assert_target_is_wc()
    antes = cargar_cuenta(C, refrescar=True)
    print(backup_verificado('galicia-seguros-reconocimiento-036'))
    with reconciliation_transaction():
        if fetch_all('SELECT 1 x FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=? AND IdContacto=?', (MOV, JYM)):
            execute_write_transaction([
                ('UPDATE dbo.[Movimientos Galicia] SET IdContacto=? WHERE IdMovimiento=? AND IdContacto=? AND [Créditos]=?', (C, MOV, JYM, IMP)),
                ("INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) "
                 "VALUES ('Galicia',?,?,?,?,?,SYSDATETIME())",
                 (MOV, JYM, C, 'Reconocimiento comercial de Galicia Seguros por gastos bancarios del proceso de pago (Galicia Broker); '
                  'la leyenda J y M venía cruzada en el extracto del 10/07/2025', USUARIO))])
        if not fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?', (C, NRO)):
            f = datetime(2025, 7, 10)
            cab = {'idContacto': C, 'fecha': f, 'tipoDocumento': 'Nota de Crédito', 'tipo': 'X', 'numeroDocumento': NRO,
                   'moneda': 'Pesos', 'tipoDeCambio': 1, 'ajustaTipoCambio': False}
            lin = {'productoServicio': 'Reconocimiento comercial gastos bancarios', 'cantidad': 1, 'precioUnitario': -IMP, 'iva': 0,
                   'ajusteFinanciero': False, 'idCentroCosto': 3, 'idDestino': 1, 'idRubro': 2047893509, 'campaña': 'No Aplica', 'idCampania': 20}
            i = execute_write_transaction([compras._cabecera_insert_statement(cab), compras._linea_insert_statement(lin),
                                           compras._vencimiento_insert_statement({'fechaVencimiento': f})])[0]
            g = fetch_all('SELECT GranTotal g FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda=?', (i,))[0]['g']
            assert abs(g + IMP) < 0.01, g
    invalidar()
    despues = cargar_cuenta(C, refrescar=True)
    print('575 pesos', antes['saldoPesos'], '->', despues['saldoPesos'], '| US$', antes['saldoDolares'], '->', despues['saldoDolares'])
    print('J y M', round(cargar_cuenta(JYM, refrescar=True)['saldoPesos'], 2))


if __name__ == '__main__': main()
