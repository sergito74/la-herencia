"""eCheq 00008092 (Jorge y Martín de la Serna SRL -> Giamigli -> Bayá), 09/06/2026, $5.797.560,71.

Fuente: Listado de ECHEQs recibidos BNA (Documents/La Herencia/Bancos y finanzas/BNA/Cheques).
Cobra las liquidaciones 0003-00017092 y 0003-00017137 (remate 13/05/2026): $5.996.744,06
- IVA transferido 29/05 ($137.473,35) - efectivo 18/05 ($61.710,00). Bayá: RI77444 anticipo,
CA145717 a TC 1.446,50 = USD 3.931,99.
"""
from datetime import date
from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar

LISTADO = r'C:\Users\Sergio\Documents\La Herencia\Bancos y finanzas\BNA\Cheques\Listado de ECHEQs recibidos.xls'
JYM, BAYA, F = 47, 226, date(2026, 6, 9)


def main():
    assert not fetch_all('SELECT 1 x FROM dbo.[Valores Recibidos] WHERE [Numero Valor]=8092')
    antes = {c: cargar_cuenta(c, refrescar=True) for c in (JYM, BAYA)}
    print(backup_verificado('baya-cheque8092-036'))
    ident = fetch_all("SELECT COLUMNPROPERTY(OBJECT_ID('dbo.[Valores Recibidos]'),'IdValor','IsIdentity') i")[0]['i']
    with reconciliation_transaction():
        cols = '[Numero Valor],Banco,[Fecha Emision],[Fecha Vencimiento],[Fecha Endoso],IdEmisor,IdReceptor,Importe,Destino,Imagen'
        vals = [8092, 'Galicia', F, F, F, JYM, BAYA, 5797560.71, 'Endoso a tercero', LISTADO]
        if not ident:
            cols = 'IdValor,' + cols
            vals = [fetch_all('SELECT MAX(IdValor)+1 n FROM dbo.[Valores Recibidos]')[0]['n']] + vals
        execute_write_transaction([(f'INSERT INTO dbo.[Valores Recibidos] ({cols}) VALUES ({",".join("?"*len(vals))})', tuple(vals))])
        idv = fetch_all('SELECT IdValor FROM dbo.[Valores Recibidos] WHERE [Numero Valor]=8092')[0]['IdValor']
        execute_write_transaction([('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,FechaEfectoUSD,DocumentoEfectoUSD) VALUES (?,?,?,?,?,?,?,?,?)',
                                    ('Pagos Valores Recibidos', idv, BAYA, 3931.99, 'Bayá RI77444/CA145717',
                                     'eCheq 8092 de J y M de la Serna; aplicado a ND130997, ND134486 y RD136157/FC416539 a TC 1.446,50.', 'sergio', F, 'CA0006-00145717'))])
    invalidar()
    for c in (JYM, BAYA):
        d = cargar_cuenta(c, refrescar=True)
        print(c, 'pesos', antes[c]['saldoPesos'], '->', d['saldoPesos'], '| USD', antes[c]['saldoDolares'], '->', d['saldoDolares'])


if __name__ == '__main__': main()
