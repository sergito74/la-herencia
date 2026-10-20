"""Corrige cabeceras y cantidad documentada; conserva el resto con foto y respaldo."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from scripts.baya_casal_nd134645_036 import state
from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import invalidar

ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
TCS={2143514335:(349.95,848.),2143514336:(349.95,848.),2143514337:(366.45,848.),2143515123:(1191.5,1480.)}
IIBB=2143515205
QTY=2143514192


def main():
    before={i:state(i) for i in [*TCS,IIBB,QTY]}
    assert all(s['cabecera'][0]['IdContacto']==226 for s in before.values())
    for i,(old,new) in TCS.items():assert before[i]['cabecera'][0]['Tipo de Cambio']==old
    assert before[IIBB]['cabecera'][0]['Ingresos Brutos']==0
    target=[r for r in before[QTY]['lineas'] if r['Producto/Servicio']=='Lts. Siliconado ARN EBC']
    total=sum(r['Cantidad'] for r in target)
    assert abs(total-12.00569935142994)<1e-8
    refs={}
    for i,s in before.items():
        ref=s['cabecera'][0]['Documento Original'].split('#')[0].replace('\\\\','\\')
        p=Path(ref) if ':' in ref else Path(r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras')/ref
        refs[i]={'pdf':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    audit={'antes':before,'fuentes':refs,'autorizacion':'Sergio20/10/2026: completar auditoría y correcciones de Bayá',
           'criterio':'TC fiscal848/1480 de originales; percepción0.95 omitida; siliconado12L originales repartidos proporcionalmente a mismos destinos. Sin alterar otros productos.',
           'backup':backup_verificado('baya-control-documental-036')}
    path=ROOT/f'control-documental-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert all(state(i)==s for i,s in before.items())
        stmts=[('UPDATE dbo.Compras SET [Tipo de Cambio]=? WHERE IdDeuda=?',(new,i)) for i,(old,new) in TCS.items()]
        stmts.append(('UPDATE dbo.Compras SET [Ingresos Brutos]=? WHERE IdDeuda=?',(.95,IIBB)))
        stmts.extend(('UPDATE dbo.Det_Compras SET Cantidad=? WHERE IdDetalleCompra=? AND IdCompra=?',
                      (r['Cantidad']*12/total,r['IdDetalleCompra'],QTY)) for r in target)
        execute_write_transaction(stmts)
        after={i:state(i) for i in before}
        for i,s in after.items():
            for k,v in before[i]['cabecera'][0].items():
                if k not in ('Tipo de Cambio','Ingresos Brutos','SSMA_TimeStamp'):assert s['cabecera'][0][k]==v
            assert s['relaciones']==before[i]['relaciones']
            if i!=QTY:assert s['lineas']==before[i]['lineas']
            else:
                for new,old in zip(s['lineas'],before[i]['lineas']):
                    for k in old:
                        if k not in ('Cantidad','SSMA_TimeStamp'):assert new[k]==old[k]
                    if old not in target:assert new['Cantidad']==old['Cantidad']
        amount=sum(r['Cantidad'] for r in after[QTY]['lineas'] if r['Producto/Servicio']=='Lts. Siliconado ARN EBC')
        assert abs(amount-12)<1e-5
        totals=fetch_all('SELECT IdDeuda,ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda IN (?,?)',(IIBB,QTY))
        assert round(next(r['ImporteDocumento'] for r in totals if r['IdDeuda']==QTY),2)==919.86
        # 348.075 +0.95 es348.025? No: total348.075 +0.95=349.025;
        # original fiscal349.02, diferencia de medio centavo queda identificada.
        assert abs(next(r['ImporteDocumento'] for r in totals if r['IdDeuda']==IIBB)-349.025)<.0002
        audit.update(despues=after,totales=totals)
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8');invalidar()
    print(json.dumps({'tiposCambioCorregidos':4,'percepcionAgregada':.95,'siliconadoLitros':amount,'totales':totals,'backup':audit['backup']},default=str))


if __name__=='__main__':main()
