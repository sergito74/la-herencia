"""Cargill (258): cola del sistema viejo de Cargill (no está en el portal) al centavo, según los mails de Luciano
Martiarena 03/06/2020 y Mónica Galván 28/07/2020 (FC 1125-2786 saldo $65.153,84; FC 1125-3153 $10.336,87):
- FC 1125-2786: US$ 1.399,86 exacto (PDF) x 60,07 = $84.089,59.
- NC 1126-6320: aplicada por Cargill a la FC 2786 por $18.935,75 (84.089,59 - 65.153,84).
- FC 1125-3153: $10.336,87.
Escala precios de renglones. Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

OBJETIVO = {'1125-00002786': 84089.59, '1126-00006320': -18935.75, '1125-00003153': 10336.87}  # en pesos


def estado():
    return {n: fetch_all("SELECT c.IdDeuda i,c.Moneda m,c.[Tipo de Cambio] tc,t.GranTotal g,t.TotalDetalleCompra d FROM dbo.Compras c "
                         "JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda WHERE c.IdContacto=258 AND c.[Nro Documento]=?", (n,))[0] for n in OBJETIVO}


def pesos(x):
    return x['g'] * (x['tc'] if x['m'] == 'Dolares' else 1)


def main():
    _assert_target_is_wc()
    E = estado()
    pend = {n: x for n, x in E.items() if abs(pesos(x) - OBJETIVO[n]) >= 0.005}
    if not pend:
        print('Nada pendiente.'); return
    print(backup_verificado('cargill-cola-2020-036'))
    with reconciliation_transaction():
        for n, x in pend.items():
            k = x['tc'] if x['m'] == 'Dolares' else 1
            obj = OBJETIVO[n] / k - (x['g'] - x['d'])
            execute_write_transaction([('UPDATE dbo.Det_Compras SET [Precio Unitario]=[Precio Unitario]*? WHERE IdCompra=?', (obj / x['d'], x['i']))])
        assert all(abs(pesos(x) - OBJETIVO[n]) < 0.005 for n, x in estado().items())
    print('ok')


if __name__ == '__main__': main()
