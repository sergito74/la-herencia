"""Cargill (258): la ficha pasa a dólares (regla usd-tc-comprobante, Sergio 21/10/2026): saldo US$ -60.000,10 =
anticipos US$ 60.000 + US$ 0,10 de la FC 7028-146283 (los $145,15 internos de Cargill) ; en pesos quedan las ND
7050-76972/77233 ($10.993,02). Estados en US$ de Cargill 18/10/2019 a 01/10/2020 iguales al centavo. Idempotente.
"""
from datetime import date

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction

NOTA = ('Cuenta en US$ (regla usd-tc-comprobante): saldo US$ -60.000,10 = anticipos 901517036A US$ 24.000 (vto 31/03/2027, girasol 26/27) '
        'y 901517055A US$ 36.000 (vto 30/06/2027, soja 26/27) + US$ 0,10 FC 7028-146283; en pesos ND 7050-76972/77233 $10.993,02. '
        'Pesos iguales al libro de Cargill al centavo (-$83.951.138,17); estados en US$ de Cargill oct-2019 a oct-2020 iguales al centavo.')


def main():
    _assert_target_is_wc()
    f = fetch_all('SELECT Moneda,SaldoAlCierre FROM dbo.RevisionFichas WHERE IdContacto=258')[0]
    if f['Moneda'] == 'Dolares':
        print('Nada pendiente.'); return
    with reconciliation_transaction():
        execute_write_transaction([("UPDATE dbo.RevisionFichas SET Moneda='Dolares',SaldoAlCierre=-60000.10,Nota=?,Corte=?,UsuarioActualiza='sergio',"
                                    "FechaActualiza=SYSDATETIME() WHERE IdContacto=258", (NOTA, date(2026, 10, 21)))])
    print('ok')


if __name__ == '__main__': main()
