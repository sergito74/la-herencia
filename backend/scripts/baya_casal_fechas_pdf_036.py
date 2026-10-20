"""Bayá: fechas y vencimientos según los PDF originales (Fecha de Registro / Vencimientos).

Revisados 115 comprobantes: TC coincide en todos; difieren solo estas fechas.
"""
from datetime import datetime
from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import invalidar

FECHAS = {2143514335: '2024-03-12', 2143514336: '2024-03-12', 2143514337: '2024-03-12'}  # FC357848/357850/357849
VTOS = {2143513254: '2021-06-11', 2143513401: '2021-10-05', 2143514335: '2024-05-30', 2143514876: '2025-05-30',
        2143514874: '2025-05-30', 2143515281: '2026-05-30', 2143515126: '2026-05-30'}


def main():
    for i in VTOS:
        assert len(fetch_all('SELECT 1 x FROM dbo.[Vencimiento Compras] WHERE IdCompra=?', (i,))) == 1, i
    print(backup_verificado('baya-fechas-pdf-036'))
    d = lambda s: datetime.strptime(s, '%Y-%m-%d')
    with reconciliation_transaction():
        execute_write_transaction(
            [('UPDATE dbo.Compras SET Fecha=? WHERE IdDeuda=? AND IdContacto=226', (d(f), i)) for i, f in FECHAS.items()] +
            [('UPDATE dbo.[Vencimiento Compras] SET [Fecha de vencimiento]=? WHERE IdCompra=?', (d(f), i)) for i, f in VTOS.items()])
    invalidar()
    for i in sorted(set(FECHAS) | set(VTOS)):
        print(fetch_all('SELECT c.[Nro Documento] n,c.Fecha f,v.[Fecha de vencimiento] v FROM dbo.Compras c JOIN dbo.[Vencimiento Compras] v ON v.IdCompra=c.IdDeuda WHERE c.IdDeuda=?', (i,)))


if __name__ == '__main__': main()
