"""Precisión de pedidos existentes y alta de soja con IVA explícito en imagen."""
import hashlib
import json
from datetime import date,datetime
from pathlib import Path
from src.db.connection import fetch_all,execute_write_transaction,reconciliation_transaction
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import invalidar
from scripts.baya_casal_nd134645_036 import state

ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
MAIL=Path(r'C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes\Baya Casal\20261019\Mails pedidos')
SOJA=MAIL/'2026-09-25-16-29/image.png'
PRECIOS={2143517489:{'GIRASOL SYN 3970 CL - B1':377.2467},
         2143517490:{'TRIGO DM AROMO C/SISTIVA - BIG BAG':.5706},
         2143517491:{'GLIFOSATO 54% POWER PLUS II x 20 L':5.4196,'2,4 D 102,5% EBC baja volatilidad x 20 L':5.4727,
                     'ATRAZINA 90% GOTEN x 10 KG':7.4918,'CARFENTRAZONE 40% AFFINITY x 1 L':106.2667,'DICAMBA 48% SIGMA x 10 L':7.4918}}


def candidatos():
    return fetch_all("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto=226 AND [Nro Documento]=?",('PENDIENTE 59111',))


def main():
    before={i:state(i) for i in PRECIOS}
    assert not candidatos()
    for i,s in before.items():
        assert s['cabecera'][0]['IdContacto']==226 and 'PENDIENTE' in s['cabecera'][0]['Nro Documento']
        assert set(r['Producto/Servicio'].strip() for r in s['lineas'])==set(PRECIOS[i])
        assert all(r['IVA']==21 for r in s['lineas'])
    audit={'antes':before,'autorizacion':'Sergio20/10/2026: completar pedidos/remitos de Bayá',
           'fuentes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOJA,MAIL/'2026-06-19-15-12/image004.png',MAIL/'2026-06-19-15-12/image005.png']},
           'criterio':'Precios4decimales originales sin cambiar IVA existente ni repartos. Soja6400kg/1.0357/21%/TC1519.5 conimagen ycorreo, vencejunio2027. Stock sin cultivo específico; campaña2026/27 explícita. No duplicar59111 por aparecer en dos secciones del portal.',
           'backup':backup_verificado('baya-pendientes-control-036')}
    path=ROOT/f'pendientes-control-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert not candidatos() and all(state(i)==s for i,s in before.items())
        assert fetch_all('SELECT Destino FROM dbo.DestinoCompras WHERE IdDestino=16')[0]['Destino']=='Stock'
        assert fetch_all('SELECT [Campaña] FROM dbo.[Campañas] WHERE [IdCampaña]=32')[0]['Campaña']=='2026/2027'
        stmts=[]
        for i,s in before.items():
            for r in s['lineas']:
                stmts.append(('UPDATE dbo.Det_Compras SET [Precio Unitario]=? WHERE IdDetalleCompra=? AND IdCompra=?',
                              (PRECIOS[i][r['Producto/Servicio'].strip()],r['IdDetalleCompra'],i)))
        execute_write_transaction(stmts)
        new=compras.create_compra({'idContacto':226,'fecha':date(2026,9,25),'tipoDocumento':'Factura','tipo':'A',
                                  'numeroDocumento':'PENDIENTE 59111','moneda':'Dolares','tipoDeCambio':1519.5,'documentoOriginal':str(SOJA)},
            [{'productoServicio':'SOJA DM 46 E 25 Trat. STANDAR - BIG BAG','cantidad':6400,'unidad':'KGS','precioUnitario':1.0357,'iva':21,
              'idCentroCosto':3,'idDestino':16,'idRubro':564800828,'campaña':'2026/2027'}],
            [{'fechaVencimiento':date(2027,6,30)}])
        execute_write_transaction([('UPDATE dbo.Compras SET [Fecha Vto]=? WHERE IdDeuda=?',(datetime(2027,6,30),new)),
                                   ('UPDATE dbo.Det_Compras SET [IdCampaña]=32 WHERE IdCompra=?',(new,))])
        after={i:state(i) for i in PRECIOS}
        for i,s in after.items():
            assert s['cabecera']==before[i]['cabecera'] and s['relaciones']==before[i]['relaciones']
            for old,r in zip(before[i]['lineas'],s['lineas']):
                for k in old:
                    if k not in ('Precio Unitario','SSMA_TimeStamp'):assert r[k]==old[k]
                assert r['Precio Unitario']==PRECIOS[i][r['Producto/Servicio'].strip()]
        total=fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?',(new,))[0]['ImporteDocumento']
        assert round(total,2)==8020.46 and len(candidatos())==1
        newstate=state(new);assert newstate['lineas'][0]['IdCampaña']==32 and newstate['lineas'][0]['IdDestino']==16
        audit.update(despues=after,soja=newstate,totalSoja=total,idSoja=new)
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8');invalidar()
    print(json.dumps({'pedidosExistentesCorregidos':3,'idSoja':new,'totalSoja':total,'backup':audit['backup']},default=str))


if __name__=='__main__':main()
