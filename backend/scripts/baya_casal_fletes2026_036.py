"""Fletes en pesos: costo económicoUSD distinto del saldo proveedorUSD."""
import json,re
from pathlib import Path
from decimal import Decimal,ROUND_DOWN
from datetime import datetime
from src.db.connection import fetch_all,execute_write_transaction,reconciliation_transaction,_reconciliation_connection
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import construir,cotizacion_bna,invalidar
from scripts.baya_casal_nd134645_036 import state
from scripts.baya_casal_precision_iva_036 import VIEWS,previous_totals

IDS=(2143515345,2143515343)
KEYS=(('Compras',IDS[0]),('Compras',IDS[1]),('Galicia',3034),('Retenciones',222))
ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
D=Decimal


def apps():
    return fetch_all("SELECT * FROM dbo.AplicacionesPago WHERE Anulada=0 AND ((OrigenMovimiento='galicia' AND IdMovimientoOrigen=3034) OR (OrigenMovimiento='retenciones' AND IdMovimientoOrigen=222) OR (TipoDocumento='CompraDeuda' AND IdDocumentoAplicado IN (?,?))) ORDER BY IdAplicacion",IDS)


def vals():
    return fetch_all('SELECT * FROM dbo.ValuacionProveedor WHERE (Origen=? AND IdOrigen IN (?,?)) OR (Origen=? AND IdOrigen=?) OR (Origen=? AND IdOrigen=?) ORDER BY Origen,IdOrigen',('Compras',*IDS,'Galicia',3034,'Retenciones',222))


def main():
    before={i:state(i) for i in IDS};oldapps=apps();oldvals=vals()
    assert {a['IdAplicacion'] for a in oldapps}=={15696,15697,15700,15737}
    assert not oldvals
    cost_sql='SELECT IdDetalleCompra,IdDestino,IdCampaña,Pesos,Dolares,Signo FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCompra IN (?,?) ORDER BY IdDetalleCompra'
    oldcosts=fetch_all(cost_sql,IDS)
    plan=[]
    for i,target in zip(IDS,('280100.00','640393.00')):
        rows=before[i]['lineas'];weights=[D(str(r['Cantidad']))*D(str(r['Precio Unitario'])) for r in rows]
        raw=[D(target)*w/sum(weights) for w in weights];net=[v.quantize(D('.01'),rounding=ROUND_DOWN) for v in raw]
        for j in sorted(range(len(rows)),key=lambda j:raw[j]-net[j],reverse=True)[:int((D(target)-sum(net))*100)]:net[j]+=D('.01')
        for r,a in zip(rows,net):plan.append({'idCompra':i,'origen':r,'neto':a,'precio':a/D(str(r['Cantidad']))})
    audit={'autorizacion':'Sergio20/10/2026: correccion e imputacion fletes; costoUSD si, proveedorUSD no',
           'antes':before,'aplicacionesAntes':oldapps,'valuacionesAntes':oldvals,'costosAntes':oldcosts,'plan':plan,
           'backup':backup_verificado('baya-fletes2026-036')}
    path=ROOT/f'fletes2026-correccion-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert all(state(i)==s for i,s in before.items()) and apps()==oldapps and vals()==oldvals
        financial_before=previous_totals();changes=[]
        # Opt-in a precisión fiscal de IVA para solo estas dos facturas;
        # conserva los demás coeficientes y nunca marca un flete como financiero.
        for name in VIEWS:
            old=fetch_all('SELECT OBJECT_DEFINITION(OBJECT_ID(?)) d',(name,))[0]['d']
            header='cfx' if name==VIEWS[0] else 'c'
            pattern=r'(\/\* precision IVA financiero 036 \*\/ CASE WHEN )(.*?)( THEN 1\.0\+CONVERT)'
            new,count=re.subn(pattern,lambda m:m[1]+'('+m[2]+') OR '+header+'.IdDeuda IN (2143515345,2143515343) /* precision fletes036 */'+m[3],old,count=1,flags=re.S)
            assert count==1
            new=re.sub(r'^\s*CREATE\s+(?:OR\s+ALTER\s+)?VIEW','ALTER VIEW',new,count=1,flags=re.I)
            _reconciliation_connection.get().cursor().execute(new)
            changes.append({'vista':name,'antes':old,'despues':new})
        stmts=[]
        for p in plan:stmts.append(('UPDATE dbo.Det_Compras SET [Precio Unitario]=? WHERE IdDetalleCompra=? AND IdCompra=?',(p['precio'],p['origen']['IdDetalleCompra'],p['idCompra'])))
        for i,dt in zip(IDS,(datetime(2026,2,1),datetime(2026,2,6))):stmts.append(('UPDATE dbo.Compras SET [Fecha Vto]=? WHERE IdDeuda=?',(dt,i)))
        for a in oldapps:stmts.append(('UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion=?,FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=? AND Anulada=0',('Reemplazada por aplicacion documental de fletes RI70854 (036)','sergio',a['IdAplicacion'])))
        app_plan=[('galicia',3034,IDS[0],D('338921.00')),('galicia',3034,IDS[1],D('772742.22')),('retenciones',222,IDS[1],D('2133.31'))]
        for medio,origin,invoice,amount in app_plan:
            stmts.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,Origen,NotaConciliacion) VALUES (?,?,'CompraDeuda',?,?,SYSDATETIME(),'sergio',0,'manual',?)",(medio,origin,invoice,amount,'Fletes pesos RI70854; transferencia LR24GE9610 y certificado2026-1')))
        for origin,i in KEYS:
            stmts.append(('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,Fecha) VALUES (?,?,226,0,?,?,?,SYSDATETIME())',(origin,i,'Baya Casal: FC437731/438310 y RI70854','Subcuenta pesos. CostoUSD de cultivo se conserva; efectoUSD proveedor cero por decision de Sergio20/10/2026.','sergio')))
        execute_write_transaction(stmts)
        after={i:state(i) for i in IDS}
        for i,s in before.items():
            assert after[i]['cabecera'][0]['Ajusta Tipo Cambio']==False
            for r,o in zip(after[i]['lineas'],s['lineas']):assert all(r[k]==v for k,v in o.items() if k not in ('Precio Unitario','SSMA_TimeStamp'))
        totals=fetch_all('SELECT IdDeuda,ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda IN (?,?)',IDS)
        target={IDS[0]:338921,IDS[1]:774875.53}
        assert all(round(r['ImporteDocumento'],2)==target[r['IdDeuda']] for r in totals)
        assert sum(target.values())==1113796.53
        newapps=apps();assert len(newapps)==3
        assert {a['IdDocumentoAplicado'] for a in newapps}==set(IDS)
        for i in IDS:assert round(sum(a['ImporteAplicado'] for a in newapps if a['IdDocumentoAplicado']==i),2)==target[i]
        assert round(sum(a['ImporteAplicado'] for a in newapps if a['OrigenMovimiento']=='galicia'),2)==1111663.22
        costs=fetch_all(cost_sql,IDS)
        assert len(costs)==11 and round(sum(c['Pesos'] for c in costs),2)==920493 and all(c['Dolares']>0 for c in costs)
        financial_after=previous_totals();assert financial_after==financial_before
        moves=fetch_all("SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE (Origen='Compras' AND IdOrigen IN (?,?)) OR (Origen='Galicia' AND IdOrigen=3034) OR (Origen='Retenciones' AND IdOrigen=222) ORDER BY Fecha,Origen,IdOrigen",IDS)
        assert len(moves)==4 and all(m['IdContacto']==226 for m in moves)
        result=construir(moves,{i:{'moneda':'Pesos','tc':1,'ajusta':False} for i in IDS},cotizacion_bna(),valuaciones={k:0 for k in KEYS})
        assert result['saldoPesos']==0 and result['saldoDolares']==0
        audit.update(despues=after,aplicacionesDespues=newapps,valuacionesDespues=vals(),costosDespues=costs,grupoBimonetario=result,vistas=changes,totales=totals,planImputacion=app_plan,
                     pago2025Liberado={'origen':'Galicia','id':2682,'importeDesimputado':1113796.55,'nota':'Se conservan las demas aplicaciones del pago2025; pendiente revisar contra sus comprobantes, sin nueva asignacion inferida.'})
    assert all(state(i)==s for i,s in after.items())
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8');invalidar()
    print(json.dumps({'totalPesos':1113796.53,'saldoGrupoPesos':result['saldoPesos'],'efectoProveedorUSD':result['saldoDolares'],'costoNetoPesos':round(sum(c['Pesos'] for c in costs),2),'costoUSD':round(sum(c['Dolares'] for c in costs),2),'aplicaciones':3,'backup':audit['backup']},default=str))


if __name__=='__main__':main()
