"""ND124811 y pago61767 según resumen; conserva documentos originales."""
from datetime import datetime
from decimal import Decimal,ROUND_DOWN
from pathlib import Path
import json,hashlib
from src.db.connection import fetch_all,execute_write_transaction,reconciliation_transaction
from src.features.compras.repository import agregar_documento_relacionado
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import construir,cotizacion_bna,invalidar
from scripts.baya_casal_nd134645_036 import state

ID=2143515121
# (Factura, diferencia neta fiscal, principal pesos previo al cambio)
TARGETS={2143514851:('140333.07','1114702.40'),2143514876:('441499.20','3506944.00'),
2143514993:('265560.81','2109419.20'),2143514874:('927534.66','7367651.20'),
2143514994:('407083.92','3233574.40'),2143514995:('20660.73','164113.60'),2143515043:('83794.50','1220710.00')}
ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
PDF=Path(r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2025 - 03 2026\20250717_BayaCasal.pdf')
D=Decimal


def apps():
    return fetch_all("SELECT * FROM dbo.AplicacionesPago WHERE Anulada=0 AND ((OrigenMovimiento='galicia' AND IdMovimientoOrigen=2682) OR (OrigenMovimiento='retenciones' AND IdMovimientoOrigen=204)) ORDER BY IdAplicacion")


def main():
    before=state(ID);origins={i:state(i) for i in TARGETS};oldapps=apps()
    assert len(oldapps)==9 and len(before['lineas'])==62
    assert before['cabecera'][0]['Nro Documento']=='0020-00124811'
    assert sum(D(v[0]) for v in TARGETS.values())==D('2286466.89')
    camps={r['Campaña']:r['IdCampaña'] for r in fetch_all('SELECT * FROM dbo.[Campañas]')}
    plan=[]
    for i,(target,principal) in TARGETS.items():
        rows=origins[i]['lineas'];weights=[D(str(r['Cantidad']))*D(str(r['Precio Unitario'])) for r in rows]
        assert all(w>0 for w in weights)
        raw=[D(target)*w/sum(weights) for w in weights];amounts=[v.quantize(D('.01'),rounding=ROUND_DOWN) for v in raw]
        for j in sorted(range(len(rows)),key=lambda j:raw[j]-amounts[j],reverse=True)[:int((D(target)-sum(amounts))*100)]:amounts[j]+=D('.01')
        for r,a in zip(rows,amounts):plan.append({'factura':i,'origen':r,'neto':a,'idCampania':camps[r['Campaña']]})
    bank=D('21177819.22');ret=D('305920.52');ndbank=D('2766624.94')-ret
    app_plan=[('galicia',2682,i,D(v[1])) for i,v in TARGETS.items()]+[('galicia',2682,ID,ndbank),('retenciones',204,ID,ret)]
    assert sum(a for m,o,i,a in app_plan if m=='galicia')==bank
    audit={'autorizacion':'Sergio20/10/2026: seguir resumen proveedor y corregir diferencias identificadas',
           'antes':before,'origenes':origins,'plan':plan,'aplicacionesAntes':oldapps,'aplicacionesPlan':app_plan,
           'pdf':str(PDF),'sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),
           'criterio':'Diferencia fiscal por factura y prorrata de netos. Principal de aplicaciones toma ND/RI literal, no capacidadSQL con precision incompleta. No inventar un ajuste de2.28: la suma documental cierra exactamente.',
           'backup':backup_verificado('baya-nd124811-036')}
    path=ROOT/f'nd124811-correccion-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert state(ID)==before and apps()==oldapps and all(state(i)==s for i,s in origins.items())
        stmts=[('DELETE FROM dbo.Det_Compras WHERE IdCompra=?',(ID,)),('UPDATE dbo.Compras SET [Fecha Vto]=?,[Ajusta Tipo Cambio]=1 WHERE IdDeuda=?',(datetime(2025,7,17),ID))]
        for p in plan:
            r=p['origen'];stmts.append(('INSERT INTO dbo.Det_Compras (IdCompra,Cantidad,Unidad,[Producto/Servicio],IdFormulado,IdCentroCostos,IdDestino,IdRubro,IdCampaña,Campaña,[Precio Unitario],IVA,[Ajuste financiero]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (ID,1,'ARS',r['Producto/Servicio'],r['IdFormulado'],r['IdCentroCostos'],r['IdDestino'],r['IdRubro'],p['idCampania'],r['Campaña'],p['neto'],21,True)))
        for a in oldapps:stmts.append(('UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion=?,FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=? AND Anulada=0',('Reemplazada por importes literales RI61767/ND124811; manda resumen proveedor','sergio',a['IdAplicacion'])))
        for medio,origin,doc,amount in app_plan:
            stmts.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,Origen,NotaConciliacion) VALUES (?,?,'CompraDeuda',?,?,SYSDATETIME(),'sergio',0,'manual',?)",(medio,origin,doc,amount,'RI61767/ND124811: principal aTCoriginal exacto del proveedor; cambio eIVA aND. Diferencias contra capacidadSQL no son deuda externa.')))
        execute_write_transaction(stmts)
        for i in TARGETS:agregar_documento_relacionado(ID,i)
        after=state(ID);newapps=apps()
        assert len(after['lineas'])==len(plan) and len(newapps)==9
        for r,p in zip(after['lineas'],plan):
            o=p['origen'];assert all(r[k]==o[k] for k in ['Producto/Servicio','IdFormulado','IdRubro','IdCentroCostos','IdDestino','Campaña'])
            assert r['IdCampaña']==p['idCampania'] and r['Cantidad']==1 and r['Unidad']=='ARS' and r['Ajuste financiero'] and r['IVA']==21
            assert abs(D(str(r['Precio Unitario']))-p['neto'])<D('.000001')
        total=fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(ID,))[0]['ImporteDocumento'];assert round(total,2)==2766624.94
        assert sum(D(str(a['ImporteAplicado'])) for a in newapps if a['IdDocumentoAplicado']==ID)==D('2766624.94')
        assert sum(D(str(a['ImporteAplicado'])) for a in newapps if a['OrigenMovimiento']=='galicia')==bank
        assert sum(D(str(a['ImporteAplicado'])) for a in newapps if a['OrigenMovimiento']=='retenciones')==ret
        for i,s in origins.items():
            now=state(i);assert now['cabecera']==s['cabecera'] and now['lineas']==s['lineas']
        costs=fetch_all('SELECT IdDetalleCompra,IdDestino,IdCampaña,Pesos,Dolares,Signo FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCompra=?',(ID,))
        assert len(costs)==len(plan) and round(sum(abs(r['Pesos'])*r['Signo'] for r in costs),2)==2286466.89 and all(r['Dolares']==0 for r in costs)
        moves=fetch_all("SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE Origen='Compras' AND IdOrigen=?",(ID,))
        assert construir(moves,{ID:{'moneda':'Pesos','tc':1,'ajusta':True}},cotizacion_bna())['saldoDolares']==0
        assert sorted(r['idCompra'] for r in after['relaciones'])==sorted(TARGETS)
        audit.update(despues=after,aplicacionesDespues=newapps,total=total,costos=costs,efectoUSD=0)
    assert state(ID)==after and apps()==newapps
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8');invalidar()
    print(json.dumps({'total':round(total,2),'lineas':len(plan),'imputacionND':2766624.94,'banco':str(bank),'retencion':str(ret),'backup':audit['backup']},default=str))


if __name__=='__main__':main()
