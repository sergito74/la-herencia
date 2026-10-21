"""Cargill (258): vencimientos de 6 facturas en US$ según el libro del portal (dueDate). Se usan para valuar la
cuenta en dólares (regla usd-tc-comprobante: los pesos cancelan solo comprobantes vencidos). Idempotente.
"""
from datetime import date

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

VTO = {'5850-00007633': date(2024, 5, 30), '7028-00092643': date(2024, 7, 4), '5850-00009175': date(2025, 1, 15),
       '5850-00009422': date(2025, 2, 26), '5850-00009578': date(2025, 3, 17), '5850-00010778': date(2025, 7, 30)}


def main():
    _assert_target_is_wc()
    pend = {}
    for n, v in VTO.items():
        c = fetch_all("SELECT c.IdDeuda i,(SELECT MAX([Fecha de vencimiento]) FROM dbo.[Vencimiento Compras] WHERE IdCompra=c.IdDeuda) vto "
                      "FROM dbo.Compras c WHERE c.IdContacto=258 AND c.[Nro Documento]=?", (n,))[0]
        if not c['vto'] or c['vto'].date() != v:
            pend[c['i']] = v
    if not pend:
        print('Nada pendiente.'); return
    print(backup_verificado('cargill-vencimientos-036'))
    with reconciliation_transaction():
        execute_write_transaction([s for i, v in pend.items() for s in (('DELETE FROM dbo.[Vencimiento Compras] WHERE IdCompra=?', (i,)),
                                   ('INSERT INTO dbo.[Vencimiento Compras] (IdCompra,[Fecha de vencimiento]) VALUES (?,?)', (i, v)))])
    print(len(pend), 'vencimientos')


if __name__ == '__main__': main()
