"""Banco Nación (369): intereses de préstamos por cuota, para el flujo de caja por período (Sergio 22/10/2026).

Reemplaza el comprobante único INT369-PREST por un comprobante interno por cada cuota pagada (fecha = débito de la cuota),
con la parte no capital separada según el cronograma del banco:
  - renglón "Intereses y cargos" y renglón "IVA RI diferencial y percepción IVA RG 2408" (rubro Financiamiento, centro 3).
Fuentes (Dropbox\\Giamigli de Bolivar SA\\Bancos\\BNA\\Prestamos):
  - Giamigli_20220412155716.pdf: informe de deuda del préstamo de $895.000 (2021, pagado a Edecán), 8 cuotas de $111.875.
  - Giamigli_20230322113651.pdf: informe de deuda del préstamo 0019136529 ($1.100.000, 03/2023, Garantizar), 8 cuotas de $137.500.
  - Giamigli_20230905095833.pdf: liquidación del préstamo 22021399 ($6.000.000, 08/2023), 4 cuotas de $1.500.000, TEM 9,01%.
  - Préstamo de $62.447,50 (28/09/2017): sin cronograma; capital en dos cuotas iguales, el resto como interés.
Si el pago difiere del cronograma (ajuste de tasa), la diferencia se reparte en proporción entre intereses e impuestos.
Capital pendiente: cuota 8 del 0019136529 ($137.500, vence 22/02/2027). Idempotente.
"""
from datetime import datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

C = 369
RUBRO = 2047893443
# IdMovimientoBNA: (préstamo, cuota, capital, interés+cargos según cronograma, IVA+percepción según cronograma)
CUOTAS = {
    17635: ('2017', 1, 31223.75, None, None), 17697: ('2017', 2, 31223.75, None, None),
    17988: ('895k', 1, 111875, 101515.07, 12181.81), 16849: ('895k', 2, 111875, 88825.68, 10659.09),
    16876: ('895k', 3, 111875, 76982.26, 9237.87), 16910: ('895k', 4, 111875, 62741.95, 7529.03),
    16932: ('895k', 5, 111875, 50757.53, 6090.90), 16764: ('895k', 6, 111875, 38279.64, 4593.55),
    16785: ('895k', 7, 111875, 25237.77, 3028.54), 16806: ('895k', 8, 111875, 12689.38, 1522.72),
    16909: ('0019136529', 1, 137500, 351834.25, 42220.11), 16931: ('0019136529', 2, 137500, 309555.82, 37146.70),
    16763: ('0019136529', 3, 137500, 259502.05, 31140.25), 16784: ('0019136529', 4, 137500, 219896.40, 26387.57),
    16805: ('0019136529', 5, 137500, 174945.21, 20993.43), 18647: ('0019136529', 6, 137500, 130479.97, 15657.60),
    18711: ('0019136529', 7, 137500, 87472.60, 10496.71),
    16917: ('22021399', 1, 1500000, 1774417.81 + 26616.27, 186313.87), 16927: ('22021399', 2, 1500000, 1330813.36 + 19962.20, 139735.40),
    16939: ('22021399', 3, 1500000, 897066.78 + 13456.00, 94192.01), 16759: ('22021399', 4, 1500000, 448533.39 + 6728.00, 47096.01),
}


def _linea(texto, importe):
    return {'productoServicio': texto[:50], 'cantidad': 1, 'precioUnitario': round(importe, 2), 'iva': 0, 'ajusteFinanciero': False,
            'idCentroCosto': 3, 'idDestino': 1, 'idRubro': RUBRO, 'campaña': 'No Aplica', 'idCampania': 20}


def main():
    _assert_target_is_wc()
    print(backup_verificado('banco-nacion-intereses-cuotas-036'))
    pagos = {r['i']: r for r in fetch_all('SELECT IdMovimientoBNA i,[Fecha / Hora Mov#] f,-Importe m FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA IN ('
                                          + ','.join(map(str, CUOTAS)) + ')')}
    viejo = fetch_all("SELECT IdDeuda i FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]='INT369-PREST'", (C,))
    with reconciliation_transaction():
        for v in viejo:
            execute_write_transaction([('DELETE FROM dbo.Det_Compras WHERE IdCompra=?', (v['i'],)),
                                       ('DELETE FROM dbo.[Vencimiento Compras] WHERE IdCompra=?', (v['i'],)),
                                       ('DELETE FROM dbo.Compras WHERE IdDeuda=?', (v['i'],))])
        total = 0.0
        for i, (prest, n, capital, interes, impuesto) in CUOTAS.items():
            p = pagos[i]
            f = p['f'] if isinstance(p['f'], datetime) else datetime.fromisoformat(str(p['f']))
            nro = f'INT369-{f:%y%m%d}'
            no_capital = round(float(p['m']) - capital, 2)
            if interes is None:
                lineas = [_linea(f'Intereses préstamo {prest} cuota {n}', no_capital)]
            else:
                imp = round(no_capital * impuesto / (interes + impuesto), 2)
                lineas = [_linea(f'Intereses y cargos préstamo {prest} cuota {n}', no_capital - imp),
                          _linea(f'IVA y percepción s/intereses {prest} cuota {n}', imp)]
            total += no_capital
            if fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?', (C, nro)):
                continue
            cab = {'idContacto': C, 'fecha': f, 'tipoDocumento': 'Factura', 'tipo': 'X', 'numeroDocumento': nro, 'moneda': 'Pesos',
                   'tipoDeCambio': 1, 'ajustaTipoCambio': False}
            execute_write_transaction([compras._cabecera_insert_statement(cab)] + [compras._linea_insert_statement(l) for l in lineas]
                                      + [compras._vencimiento_insert_statement({'fechaVencimiento': f})])
    invalidar()
    print('intereses+IVA total', round(total, 2), '| saldo BNA', cargar_cuenta(C, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
