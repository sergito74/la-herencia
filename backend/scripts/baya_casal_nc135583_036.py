"""NC135583 mixta: crédito maíz y cargo fertilizante, sin nuevos kilos."""
import json,re,hashlib
from pathlib import Path
from datetime import datetime
from decimal import Decimal,ROUND_DOWN
from src.db.connection import fetch_all,execute_write_transaction,reconciliation_transaction,_reconciliation_connection
from src.features.vinculos.backup import backup_verificado
from src.features.compras.repository import agregar_documento_relacionado
from src.features.auditoria_cuentas.bimonetaria import construir,cotizacion_bna
from scripts.baya_casal_nd134645_036 import state

ID=2143517488
ORIGINS=(2143515104,2143517472)
D=Decimal
ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
PDF=Path(r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2026 - 03 2027\20260629_BayaCasal.pdf')


def nc_costs():
    return fetch_all("SELECT v.IdCompra,SUM(v.Pesos) pesos,SUM(ABS(v.Pesos)*v.Signo) apiPesos,SUM(v.Dolares) dolares FROM dbo.vw_ResultadosCultivo_CostosBase v WHERE v.IdCompra<>? AND EXISTS (SELECT 1 FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda=d.IdCompra WHERE d.IdCompra=v.IdCompra AND d.[Ajuste financiero]=1 AND c.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Credito') GROUP BY v.IdCompra ORDER BY v.IdCompra",(ID,))


def main():
    before=state(ID);origins={i:state(i) for i in ORIGINS}
    assert before['cabecera'][0]['Nro Documento']=='0020-00135583' and not before['cabecera'][0]['Ajusta Tipo Cambio']
    assert len(before['lineas'])==3
    source=origins[ORIGINS[0]]['lineas']
    weights=[D(str(r['Cantidad']))*D(str(r['Precio Unitario'])) for r in source]
    raw=[D('760.95')*w/sum(weights) for w in weights];amounts=[v.quantize(D('.01'),rounding=ROUND_DOWN) for v in raw]
    for j in sorted(range(len(source)),key=lambda j:raw[j]-amounts[j],reverse=True)[:int((D('760.95')-sum(amounts))*100)]:amounts[j]+=D('.01')
    bykey={(r['Producto/Servicio'],r['IdDestino']):a for r,a in zip(source,amounts)}
    plan=[]
    for r in before['lineas']:
        amount=bykey.get((r['Producto/Servicio'],r['IdDestino']))
        if amount is None:
            assert r['Producto/Servicio']=='MAIZ LT 725 TRE - B2' and r['IdDestino']==8
            amount=D('-116663.06')
        plan.append((r,amount))
    assert sum(a for r,a in plan)==D('-115902.11')
    audit={'autorizacion':'Sergio20/10/2026: adelante NC135583','antes':before,'origenes':origins,'plan':plan,
           'criterio':'Componentes brutos+920.75 fertilizante y-141162.30 maiz, divididos por1.21: netos+760.95/-116663.06. Fertilizante prorrata por netosFC416539. IVA21 fiscal deNC, no IVA10.5 de compra original.',
           'pdf':str(PDF),'sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),'respaldo':backup_verificado('baya-nc135583-036')}
    path=ROOT/f'nc135583-correccion-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert state(ID)==before and all(state(i)==s for i,s in origins.items())
        prior=nc_costs()
        stmts=[('UPDATE dbo.Compras SET [Ajusta Tipo Cambio]=?,[Fecha Vto]=? WHERE IdDeuda=?',(True,datetime(2026,6,29),ID))]
        for r,a in plan:stmts.append(('UPDATE dbo.Det_Compras SET Cantidad=?,Unidad=?,[Precio Unitario]=?,[Ajuste financiero]=? WHERE IdDetalleCompra=? AND IdCompra=?',(1,'ARS',a,True,r['IdDetalleCompra'],ID)))
        execute_write_transaction(stmts)
        for i in ORIGINS:agregar_documento_relacionado(ID,i)
        name='dbo.vw_ResultadosCultivo_CostosBase'
        old=fetch_all('SELECT OBJECT_DEFINITION(OBJECT_ID(?)) d',(name,))[0]['d']
        pred="ISNULL(DC.[Ajuste financiero],0)=1 AND CP.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Credito'"
        find="THEN ISNULL(DC.Cantidad,0)*ISNULL(DC.[Precio Unitario],0) ELSE ABS(ISNULL(DC.Cantidad, 0) * ISNULL(DC.[Precio Unitario], 0)) END"
        replace="THEN ISNULL(DC.Cantidad,0)*ISNULL(DC.[Precio Unitario],0) WHEN "+pred+" THEN -(ISNULL(DC.Cantidad,0)*ISNULL(DC.[Precio Unitario],0)) ELSE ABS(ISNULL(DC.Cantidad, 0) * ISNULL(DC.[Precio Unitario], 0)) END"
        assert old.count(find)==4
        new=old.replace(find,replace)
        start="CASE WHEN CP.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Credito' THEN -1"
        assert new.count(start)==1
        new=new.replace(start,"CASE WHEN "+pred+" AND ISNULL(DC.Cantidad,0)*ISNULL(DC.[Precio Unitario],0)>0 THEN 1 WHEN CP.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Credito' THEN -1")
        new=re.sub(r'^\s*CREATE\s+(?:OR\s+ALTER\s+)?VIEW','ALTER VIEW',new,count=1,flags=re.I)
        _reconciliation_connection.get().cursor().execute(new)
        assert nc_costs()==prior
        after=state(ID)
        for r,s in zip(after['lineas'],before['lineas']):
            assert all(r[k]==s[k] for k in ['IdDetalleCompra','Producto/Servicio','IVA','IdRubro','IdCentroCostos','IdDestino','IdCampaña','Campaña','IdFormulado'])
            assert r['Cantidad']==1 and r['Unidad']=='ARS' and r['Ajuste financiero']
        total=fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(ID,))[0]['ImporteDocumento'];assert round(total,2)==-140241.55
        costs=fetch_all('SELECT IdDetalleCompra,Pesos,Dolares,Signo FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCompra=?',(ID,))
        assert len(costs)==3 and round(sum(r['Pesos'] for r in costs),2)==-115902.11
        assert round(sum(abs(r['Pesos'])*r['Signo'] for r in costs),2)==-115902.11 and all(r['Dolares']==0 for r in costs)
        assert sum(r['Signo']==1 for r in costs)==2 and sum(r['Signo']==-1 for r in costs)==1
        movements=fetch_all('SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE Origen=? AND IdOrigen=?',('Compras',ID))
        usd=construir(movements,{ID:{'moneda':'Pesos','tc':1,'ajusta':True}},cotizacion_bna());assert usd['saldoDolares']==0
        for i,s in origins.items():
            o=state(i);assert o['cabecera']==s['cabecera'] and o['lineas']==s['lineas']
        assert sorted(r['idCompra'] for r in after['relaciones'])==sorted(ORIGINS)
        audit.update(despues=after,total=total,costos=costs,efectoUSD=0,vistaAntes=old,vistaDespues=new,otrasNCAntes=prior,otrasNCDespues=nc_costs())
    assert state(ID)==after
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'credito':round(-total,2),'netoFertilizante':str(sum(a for r,a in plan if a>0)),'netoMaiz':'-116663.06','USD':0,'respaldo':audit['respaldo']},default=str))


if __name__=='__main__':main()
