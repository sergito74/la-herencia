"""Redondeo fiscal de FC401514 sin alterar productos ni crear otro cargo."""
import json,re
from pathlib import Path
from datetime import datetime
from src.db.connection import fetch_all,reconciliation_transaction,_reconciliation_connection
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import invalidar
from scripts.baya_casal_nd134645_036 import state

ID=2143514851
ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
VIEWS=('dbo.vw_Compras_ImporteDocumento','dbo.vw_Cns_Total_Det_Compras')
MARKER='/* fiscal FC401514 036 */'


def totals():
    return fetch_all('SELECT v.IdDeuda,v.ImporteDocumento,t.GranTotal FROM dbo.vw_Compras_ImporteDocumento v LEFT JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=v.IdDeuda ORDER BY v.IdDeuda')


def main():
    before=state(ID)
    assert before['cabecera'][0]['Nro Documento']=='0020-00401514'
    assert before['cabecera'][0]['Ingresos Brutos']==1.64 and all(r['IVA']==21 for r in before['lineas'])
    changes=[]
    for name in VIEWS:
        old=fetch_all('SELECT OBJECT_DEFINITION(OBJECT_ID(?)) d',(name,))[0]['d']
        assert MARKER not in old
        alias='dc' if name==VIEWS[0] else 'd'
        label='TotalDetalle' if alias=='dc' else 'TotalDetalleCompra'
        start=old.index('SUM(') if alias=='dc' else old.index('SUM(d.Cantidad * d.[Precio Unitario] * (')
        end_match=re.search(r'\)\s+AS '+label+r'\b',old[start:],re.S);assert end_match
        end=start+end_match.end()
        aggregate=old[start:start+end_match.start()+1]
        # El PDF expresa base eIVA a2decimales, no impuesto sobre base
        # fraccionaria de cantidades distribuidas almacenadas comoREAL.
        replacement=(f'{MARKER} CASE WHEN {alias}.IdCompra={ID} THEN '
                     f'ROUND(ROUND(SUM(CONVERT(float,{alias}.Cantidad)*{alias}.[Precio Unitario]),2)*1.21,2) '
                     f'ELSE {aggregate} END AS {label}')
        new=old[:start]+replacement+old[end:]
        new=re.sub(r'^\s*CREATE\s+(?:OR\s+ALTER\s+)?VIEW','ALTER VIEW',new,count=1,flags=re.I)
        changes.append({'vista':name,'antes':old,'despues':new})
    previous=totals()
    audit={'autorizacion':'Sergio20/10/2026: corregir redondeo FC401514','antes':before,'vistas':changes,
           'criterio':'SoloFC401514: base fiscal821.18 eIVA172.45 redondeados, IIBB1.64; no alterar datos de productos ni otros documentos.',
           'backup':backup_verificado('baya-fc401514-redondeo-036')}
    path=ROOT/f'fc401514-redondeo-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert state(ID)==before and totals()==previous
        for change in changes:_reconciliation_connection.get().cursor().execute(change['despues'])
        after=totals();assert len(after)==len(previous)
        for new,old in zip(after,previous):
            assert new['IdDeuda']==old['IdDeuda']
            if new['IdDeuda']==ID:
                assert round(new['ImporteDocumento'],2)==995.27 and round(new['GranTotal'],2)==995.27
            else:assert new==old
        assert state(ID)==before
        audit.update(totalAntes=next(r for r in previous if r['IdDeuda']==ID),totalDespues=next(r for r in after if r['IdDeuda']==ID),otrosDocumentosSinCambio=len(after)-1)
    assert state(ID)==before and totals()==after
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8');invalidar()
    print(json.dumps({'total':audit['totalDespues'],'otrosDocumentosSinCambio':len(after)-1,'backup':audit['backup']},default=str))


if __name__=='__main__':main()
