"""Vista vw_Cns_Total_Det_Compras: FC 00003-00004511 de Ricardo Criado (IdDeuda 2143523746) usa IVA en doble
precisión, como las de la lista 'precision fletes036' (el IVA real de simple precisión desvía $0,16 en $5,1 M)."""
from src.db.connection import _assert_target_is_wc, _reconciliation_connection, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

VIEJO, NUEVO = 'IN (2143515345,2143515343)', 'IN (2143515345,2143515343,2143523746)'


def main():
    _assert_target_is_wc()
    d = fetch_all("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_Cns_Total_Det_Compras')) AS d")[0]['d']
    if NUEVO in d:
        print('Ya aplicado.'); return
    assert d.count(VIEJO) == 1
    print(backup_verificado('precision-iva-criado-036'))
    with reconciliation_transaction():
        _reconciliation_connection.get().cursor().execute(d.replace(VIEJO, NUEVO).replace('CREATE VIEW', 'ALTER VIEW', 1))
    print(fetch_all('SELECT GranTotal FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda=2143523746'))


if __name__ == '__main__': main()
