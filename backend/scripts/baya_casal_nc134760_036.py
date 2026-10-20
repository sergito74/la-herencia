"""NC134760: reconstrucción por seis diferencias fiscales y sus facturas."""
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
import json
import hashlib

from src.db.connection import fetch_all,execute_write_transaction,reconciliation_transaction,_reconciliation_connection
from src.features.compras.repository import agregar_documento_relacionado
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import construir,cotizacion_bna
from scripts.baya_casal_nd134645_036 import state
from scripts.baya_casal_precision_iva_036 import previous_totals,VIEWS

ID=2143517449
TARGETS={2143515126:'45070.47',2143515202:'50320.53',2143515204:'61753.05',2143515280:'15414.03',2143515281:'39503.52',2143516380:'22984.29'}
ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
PDF=Path(r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2026 - 03 2027\20260610_BayaCasal 001.pdf')
D=Decimal


def main():
    before=state(ID);origins={i:state(i) for i in TARGETS}
    if before['cabecera'][0]['Ajusta Tipo Cambio']:
        assert round(fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(ID,))[0]['ImporteDocumento'],2)==-284405.53
        print('Ya corregida; sin cambios.');return
    assert len(before['lineas'])==137 and before['cabecera'][0]['Nro Documento']=='0020-00134760'
    camps={r['Campaña']:r['IdCampaña'] for r in fetch_all('SELECT * FROM dbo.[Campañas]')}
    plan=[]
    for i,target in TARGETS.items():
        rows=origins[i]['lineas'];weights=[D(str(r['Cantidad']))*D(str(r['Precio Unitario'])) for r in rows]
        assert all(w>0 for w in weights)
        raw=[D(target)*w/sum(weights) for w in weights];amounts=[v.quantize(D('.01'),rounding=ROUND_DOWN) for v in raw]
        for j in sorted(range(len(rows)),key=lambda j:(raw[j]-amounts[j],-rows[j]['IdDetalleCompra']),reverse=True)[:int((D(target)-sum(amounts))*100)]:amounts[j]+=D('.01')
        for r,a in zip(rows,amounts):
            assert r['Campaña'] in camps
            plan.append({'factura':i,'origen':r,'creditoNeto':a,'idCampania':camps[r['Campaña']]})
    assert len(plan)==139 and sum(p['creditoNeto'] for p in plan)==D('235045.89')
    audit={'autorizacion':'Sergio: adelante con correccion NC134760,20/10/2026','antes':before,'origenes':origins,'plan':plan,
           'pdf':str(PDF),'sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),'backup':backup_verificado('baya-nc134760-036')}
    path=ROOT/f'nc134760-correccion-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert state(ID)==before and all(state(i)==s for i,s in origins.items())
        stmts=[('UPDATE dbo.Compras SET [Ajusta Tipo Cambio]=?,[Fecha Vto]=? WHERE IdDeuda=?',(True,datetime(2026,6,10),ID)),
               ('DELETE FROM dbo.Det_Compras WHERE IdCompra=?',(ID,))]
        for p in plan:
            r=p['origen']
            stmts.append(('INSERT INTO dbo.Det_Compras (IdCompra,Cantidad,Unidad,[Producto/Servicio],IdFormulado,IdCentroCostos,IdDestino,IdRubro,IdCampaña,Campaña,[Precio Unitario],IVA,[Ajuste financiero]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          (ID,1,'ARS',r['Producto/Servicio'],r['IdFormulado'],r['IdCentroCostos'],r['IdDestino'],r['IdRubro'],p['idCampania'],r['Campaña'],-p['creditoNeto'],21,True)))
        execute_write_transaction(stmts)
        for i in TARGETS:agregar_documento_relacionado(ID,i)
        # El IVA REAL requiere el mismo coeficiente doble ya usado para ND.
        # Ampliar a NC financieras solo si no cambia a centavos otras notas.
        totals_before=previous_totals();view_changes=[]
        for name in VIEWS:
            old=fetch_all('SELECT OBJECT_DEFINITION(OBJECT_ID(?)) d',(name,))[0]['d']
            old_pred="COLLATE Latin1_General_CI_AI='Nota de Debito'"
            new=old.replace(old_pred,"COLLATE Latin1_General_CI_AI IN ('Nota de Debito','Nota de Credito')")
            assert new!=old or "IN ('Nota de Debito','Nota de Credito')" in old
            if new!=old:
                import re
                new=re.sub(r'^\s*CREATE\s+(?:OR\s+ALTER\s+)?VIEW','ALTER VIEW',new,count=1,flags=re.I)
                _reconciliation_connection.get().cursor().execute(new)
                view_changes.append({'nombre':name,'antes':old,'despues':new})
        totals_after=previous_totals();by_id={r['IdDeuda']:r for r in totals_before}
        for r in totals_after:
            if r['IdDeuda']!=ID:
                for k in ['ImporteDocumento','GranTotal']:assert round(r[k],2)==round(by_id[r['IdDeuda']][k],2)
        after=state(ID)
        total=fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(ID,))[0]['ImporteDocumento']
        assert round(total,2)==-284405.53
        assert len(after['lineas'])==139
        assert sorted(r['idCompra'] for r in after['relaciones'])==sorted(TARGETS)
        for i,s in origins.items():
            now=state(i);assert now['cabecera']==s['cabecera'] and now['lineas']==s['lineas']
        costs=fetch_all('SELECT IdDetalleCompra,IdDestino,IdCampaña,Pesos,Dolares,Signo FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCompra=?',(ID,))
        assert len(costs)==139 and round(sum(abs(r['Pesos'])*r['Signo'] for r in costs),2)==-235045.89 and all(r['Dolares']==0 for r in costs)
        movements=fetch_all('SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE Origen=? AND IdOrigen=?',('Compras',ID))
        usd=construir(movements,{ID:{'moneda':'Pesos','tc':1,'ajusta':True}},cotizacion_bna());assert usd['saldoDolares']==0
        audit.update(despues=after,total=total,costos=costs,efectoUSD=0,vistas=view_changes,totalesAntes=totals_before,totalesDespues=totals_after)
    assert state(ID)==after
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'IdDeuda':ID,'credito':round(-total,2),'lineas':139,'USD':0,'respaldo':audit['backup']},default=str))


if __name__=='__main__':main()
