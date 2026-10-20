"""Reimputación documental del pago17/07/2025, sin forzar residuos históricos."""
from pathlib import Path
from datetime import datetime
from decimal import Decimal,ROUND_HALF_UP
import json,hashlib
from src.db.connection import fetch_all,execute_write_transaction,reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import construir,cotizacion_bna,invalidar
from scripts.baya_casal_nd134645_036 import state

INVOICES=(2143514851,2143514876,2143514993,2143514874,2143514994,2143514995,2143515043)
ND=2143515121
IDS=INVOICES+(ND,)
ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
D=Decimal


def apps():
    return fetch_all("SELECT * FROM dbo.AplicacionesPago WHERE Anulada=0 AND ((OrigenMovimiento='galicia' AND IdMovimientoOrigen=2682) OR (OrigenMovimiento='retenciones' AND IdMovimientoOrigen=204) OR (TipoDocumento='CompraDeuda' AND IdDocumentoAplicado IN ("+','.join('?' for i in IDS)+"))) ORDER BY IdAplicacion",IDS)


def vals():
    return fetch_all("SELECT * FROM dbo.ValuacionProveedor WHERE (Origen='Galicia' AND IdOrigen=2682) OR (Origen='Retenciones' AND IdOrigen=204) ORDER BY Origen")


def main():
    before={i:state(i) for i in IDS};oldapps=apps();oldvals=vals()
    assert len(oldapps)==21 and not oldvals
    assert before[ND]['cabecera'][0]['Ajusta Tipo Cambio']
    def cents(v):return D(str(v)).quantize(D('.01'),rounding=ROUND_HALF_UP)
    caps={}
    for i in INVOICES:
        h=before[i]['cabecera'][0]
        assert h['IdContacto']==226 and h['Moneda']=='Dolares'
        total=fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(i,))[0]['ImporteDocumento']
        caps[i]=cents(D(str(total))*D(str(h['Tipo de Cambio'])))
    # RI y ND124811 especifican saldoUSD3131.20 deFC401515, tras crédito previoUSD83.17.
    caps[2143514876]=D('3506944.00')
    bank=D('21177819.22');ret=D('305920.52')
    bank_nd=bank-sum(caps.values())
    nd_total=cents(fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(ND,))[0]['ImporteDocumento'])
    assert bank_nd>0 and bank_nd+ret<nd_total
    plan=[('galicia',2682,i,a) for i,a in caps.items()]+[('galicia',2682,ND,bank_nd),('retenciones',204,ND,ret)]
    receipt=ROOT/'RI_0006_00061767.pdf'
    assert receipt.is_file()
    audit={'autorizacion':'Sergio20/10/2026: adelante con reimputacion pago17/07/2025','antes':before,'aplicacionesAntes':oldapps,'valuacionesAntes':oldvals,
           'plan':plan,'recibo':str(receipt),'hashRecibo':hashlib.sha256(receipt.read_bytes()).hexdigest(),
           'criterio':'Aplicaciones expresadas en pesos de origen de cada factura; diferencia de cambio asignada aND124811. FC401515 solo saldo confirmadoUSD3131.20. Capacidades de las otras seis al total vigenteSQL para no sobreimputar. No forzar correccion de sus redondeos ni del importe incorrecto deND en este paso.',
           'respaldo':backup_verificado('baya-pago20250717-036')}
    path=ROOT/f'pago20250717-correccion-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert all(state(i)==s for i,s in before.items()) and apps()==oldapps and vals()==oldvals
        stmts=[]
        for a in oldapps:stmts.append(('UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion=?,FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=? AND Anulada=0',('Reemplazada por imputacion documental RI61767 Bayá (036)','sergio',a['IdAplicacion'])))
        for medio,origin,doc,amount in plan:stmts.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,Origen,NotaConciliacion) VALUES (?,?,'CompraDeuda',?,?,SYSDATETIME(),'sergio',0,'manual',?)",(medio,origin,doc,amount,'RI61767 TC1261. Principal aTCoriginal; cambio aND124811. Credito previoFC401515 pendiente imputacion propia.')))
        for origin,i,usd in [('Galicia',2682,D('16656.29')),('Retenciones',204,D('0'))]:
            stmts.append(('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,Fecha) VALUES (?,?,226,?,?,?, ?,SYSDATETIME())',(origin,i,usd,'Bayá RI61767 y libro17/07/2025','USD16656.29 de principal en transferencia; retencion305920.52 y componente banco174237.53 quedan en pesos contraIVA deND124811.','sergio')))
        execute_write_transaction(stmts)
        afterapps=apps();assert len(afterapps)==9
        assert sum(D(str(a['ImporteAplicado'])) for a in afterapps if a['OrigenMovimiento']=='galicia')==bank
        assert sum(D(str(a['ImporteAplicado'])) for a in afterapps if a['OrigenMovimiento']=='retenciones')==ret
        assert all(a['IdDocumentoAplicado'] in IDS for a in afterapps)
        assert all(state(i)==s for i,s in before.items())
        moves=fetch_all("SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE (Origen='Galicia' AND IdOrigen=2682) OR (Origen='Retenciones' AND IdOrigen=204) ORDER BY Fecha,Origen,IdOrigen")
        assert len(moves)==2 and all(m['IdContacto']==226 for m in moves)
        usd=construir(moves,{},cotizacion_bna(),valuaciones={('Galicia',2682):16656.29,('Retenciones',204):0})
        assert usd['saldoDolares']==16656.29 and usd['saldoPesos']==21483739.74
        # No redondear USD previamente: auditar capacidad en pesos de origen.
        residuals={i:cents(D(str(fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(i,))[0]['ImporteDocumento']))*D(str(before[i]['cabecera'][0]['Tipo de Cambio'])))-sum(D(str(a['ImporteAplicado'])) for a in afterapps if a['IdDocumentoAplicado']==i) for i in INVOICES}
        assert all(v>=0 for v in residuals.values())
        audit.update(aplicacionesDespues=afterapps,valuacionesDespues=vals(),efectoProveedor=usd,
                     residuoFacturasPesos=residuals,residuoND=nd_total-bank_nd-ret,
                     hallazgoND={'SQL':nd_total,'fiscalPDF':D('2766624.94'),'excesoSQL':nd_total-D('2766624.94'),'saldoSiCorrigeND':D('2766624.94')-bank_nd-ret})
    assert apps()==afterapps
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8');invalidar()
    print(json.dumps({'imputaciones':9,'bancoAplicado':bank,'retencionAplicada':ret,'creditoUSD':usd['saldoDolares'],'residuoND':audit['residuoND'],'residuoFC401515':residuals[2143514876],'respaldo':audit['respaldo']},default=str))


if __name__=='__main__':main()
