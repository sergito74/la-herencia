"""NERA33178 yRG36: aplicaciones, monedas e importes del proveedor."""
from datetime import datetime,date
from pathlib import Path
from decimal import Decimal
import json
from src.db.connection import fetch_all,execute_write_transaction,reconciliation_transaction,_reconciliation_connection
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import invalidar,cargar_cuenta
from scripts.baya_casal_nd134645_036 import state

ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
IDS=(2143514032,2143514033,2143514218,2143523738,2143523744)
D=Decimal


def apps():
    return fetch_all("SELECT * FROM dbo.AplicacionesPago WHERE Anulada=0 AND ((OrigenMovimiento='galicia' AND IdMovimientoOrigen=1375) OR (OrigenMovimiento='retenciones' AND IdMovimientoOrigen=109)) ORDER BY IdAplicacion")


def vals():
    return fetch_all("SELECT * FROM dbo.ValuacionProveedor WHERE (Origen='Galicia' AND IdOrigen=1375) OR (Origen='Retenciones' AND IdOrigen=109)")


def main():
    oldapps=apps();assert len(oldapps)==9 and not vals()
    bank=fetch_all('SELECT * FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=?',(1375,))
    ret=fetch_all('SELECT * FROM dbo.Retenciones WHERE IdRetencionSQL=?',(109,))
    assert bank[0]['Débitos']==9880148 and bank[0]['IdContacto']==226 and ret[0]['Importe']==95267.22
    docs={i:state(i) for i in IDS}
    aug=datetime(2023,8,29);jan=datetime(2024,1,11)
    # Importe de aplicaciones en pesos de origen: no duplicar la diferencia
    # de cambio incluida en los importes de factura del RI.
    plan=[('galicia',1375,IDS[0],D('1249385.78'),aug),
          ('galicia',1375,IDS[1],D('3868981.71'),aug),
          ('galicia',1375,IDS[2],D('147396.75'),aug),
          ('galicia',1375,IDS[3],D('229028.28'),aug),
          ('galicia',1375,IDS[4],D('4385355.23'),aug),
          ('retenciones',109,IDS[2],D('95267.22'),jan)]
    assert sum(a for m,o,i,a,f in plan if m=='galicia')==D('9880147.75')
    audit={'autorizacion':'Sergio20/10/2026: replicar cuenta corriente del proveedor, corregir NERA',
           'bancoAntes':bank,'retencionAntes':ret,'documentosAntes':docs,'aplicacionesAntes':oldapps,'plan':plan,
           'criterio':'RI33178 yND96887: principal aTCoriginal masNDcompleta, sin duplicar cambio. Banco real9880148 intacto; proveedor reconoce9880147.75. RG36 aplicadoenero2024 aFC336203.',
           'diferenciaBancoRecibo':'0.25, pendiente explicacion de tesoreria, no saldo externo',
           'backup':backup_verificado('baya-nera2023-036')}
    path=ROOT/f'nera2023-correccion-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert apps()==oldapps and not vals() and all(state(i)==s for i,s in docs.items())
        if fetch_all("SELECT COL_LENGTH('dbo.ValuacionProveedor','ImporteReconocidoPesos') n")[0]['n'] is None:
            _reconciliation_connection.get().cursor().execute('ALTER TABLE dbo.ValuacionProveedor ADD ImporteReconocidoPesos money NULL')
        stmts=[]
        for a in oldapps:stmts.append(('UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion=?,FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=? AND Anulada=0',('Reemplazada por RI33178/RG36 originales Bayá (036)','sergio',a['IdAplicacion'])))
        for medio,origin,doc,amount,fecha in plan:stmts.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,Origen,NotaConciliacion) VALUES (?,?,'CompraDeuda',?,?,?,'sergio',0,'manual',?)",(medio,origin,doc,amount,fecha,'NERA: RI33178 29/08/2023; RG36/RI37632 11/01/2024. Manda resumen.')))
        for origin,i,usd,pesos,fecha,doc in [
            ('Galicia',1375,D('26786.96'),D('9880147.75'),aug,'RI0006-00033178'),
            ('Retenciones',109,D('322.94'),None,jan,'RG0001-00000036')]:
            stmts.append(('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,FechaEfectoUSD,DocumentoEfectoUSD,ImporteReconocidoPesos) VALUES (?,?,226,?,?,?, ?,?,?,?)',
                (origin,i,usd,'Bayá RI33178 yRG36/RI37632 originales','SepararUSDdelproveedor ypesos; diferencia0.25 bancaria documentada sin alterar banco ni crear otro pago.','sergio',fecha,doc,pesos)))
        execute_write_transaction(stmts)
        newapps=apps();assert len(newapps)==6
        assert sum(D(str(a['ImporteAplicado'])) for a in newapps if a['OrigenMovimiento']=='galicia')==D('9880147.75')
        assert sum(D(str(a['ImporteAplicado'])) for a in newapps if a['OrigenMovimiento']=='retenciones')==D('95267.22')
        assert all(state(i)==s for i,s in docs.items())
        assert fetch_all('SELECT * FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=?',(1375,))==bank
        assert fetch_all('SELECT * FROM dbo.Retenciones WHERE IdRetencionSQL=?',(109,))==ret
        audit.update(aplicacionesDespues=newapps,valuacionesDespues=vals())
    invalidar();result=cargar_cuenta(226,refrescar=True)
    source=next(r for r in result['filas'] if r['origenTipo']=='Galicia' and r['idOrigen']==1375)
    assert source['creditoPesos']==9880147.75 and source['fecha']==date(2023,8,29)
    events=[r for r in result['filas'] if r['origenTipo']=='Aplicacion proveedor']
    assert any(r['numeroDocumento']=='RI0006-00033178' and r['fecha']==date(2023,8,29) and r['creditoOriginal']==26786.96 and r['creditoPesos']==0 for r in events)
    assert any(r['numeroDocumento']=='RG0001-00000036' and r['fecha']==date(2024,1,11) and r['creditoOriginal']==322.94 for r in events)
    audit.update(origenProveedorVerificado=source,eventosVerificados=events)
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'aplicaciones':6,'pagoReconocidoPesos':9880147.75,'pagoUSD':26786.96,'retencionUSD':322.94,'diferenciaBancaria':0.25,'backup':audit['backup']},default=str))


if __name__=='__main__':main()
