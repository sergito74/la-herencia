"""Cargill (258): diferencias de tipo de cambio de anticipos financieros (libro del portal, 20/10/2026).

Los anticipos financieros de Cargill son deuda en US$: entregan pesos al TC del día y, al cancelarlos con granos,
cobran (X& TIPO CAMBIO ANTICIPO DEBITO) o reconocen (X@ ... CREDITO) la diferencia de cambio. No son comprobantes
fiscales (sin IVA); figuran en los avisos PAGO_COBRO que Cargill manda por mail. Nunca estaban en el sistema.
Se cargan como ND/NC tipo X "Ajusta Tipo Cambio", clasificadas como las facturas de intereses de Cargill
(centro 3, destino 1, Financiamiento, No Aplica). Idempotente.
"""
from datetime import datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

FINANCIAMIENTO = 2047893443
# número, fecha, contrato, importe (+ débito / - crédito)
DIFS = [
    ('X&-00051107', '2022-05-05', '901134772A', 56648.00),
    ('X&-00099053', '2024-01-03', '901248781A', 4616000.00),
    ('X&-00118194', '2024-06-27', '901248784A', 4490567.32),
    ('X&-00119167', '2024-07-03', '901248784A', 3924836.54),
    ('X&-00119168', '2024-07-03', '901260711A', 4464714.07),
    ('X&-00119492', '2024-07-05', '901260711A', 39862.14),
    ('X&-00131268', '2024-12-30', '901344122A', 142891.00),
    ('X@-00005239', '2026-04-01', '901482705A', -739500.00),
    ('X@-00008658', '2026-05-28', '901455631A', -182597.11),
    ('X@-00008852', '2026-05-30', '901455631A', -54341.29),
]


def main():
    _assert_target_is_wc()
    pend = [d for d in DIFS if not fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=258 AND [Nro Documento]=?', (d[0],))]
    if not pend:
        print('Nada pendiente.'); return
    backup = backup_verificado('cargill-dif-cambio-anticipos-036')
    creados = {}
    with reconciliation_transaction():
        for nro, fecha, contrato, imp in pend:
            f = datetime.fromisoformat(fecha)
            cab = {'idContacto': 258, 'fecha': f, 'tipoDocumento': 'Nota de Débito' if imp > 0 else 'Nota de Crédito', 'tipo': 'X',
                   'numeroDocumento': nro, 'moneda': 'Pesos', 'tipoDeCambio': 1, 'ajustaTipoCambio': True}
            linea = {'productoServicio': f'Dif. TC anticipo financiero {contrato}', 'cantidad': 1, 'precioUnitario': imp, 'iva': 0,
                     'idCentroCosto': 3, 'idDestino': 1, 'idRubro': FINANCIAMIENTO, 'campaña': 'No Aplica',
                     'idCampania': compras.get_id_campania_por_nombre('No Aplica'), 'ajusteFinanciero': True}
            i = execute_write_transaction([compras._cabecera_insert_statement(cab), compras._linea_insert_statement(linea),
                                           compras._vencimiento_insert_statement({'fechaVencimiento': f})])[0]
            g = fetch_all('SELECT GranTotal g FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda=?', (i,))[0]['g']
            assert abs(g - imp) < 0.01, (nro, g, imp)
            creados[nro] = i
    print(creados, backup)


if __name__ == '__main__': main()
