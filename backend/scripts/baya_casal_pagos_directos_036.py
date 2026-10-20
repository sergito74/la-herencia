"""RI7384/9194/24763: corrige destino y crédito USD, no importe bancario."""
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from scripts.baya_casal_nd134645_036 import state

ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
PLAN=[(219,49413.87,499.13,2143513401,'00007384',date(2021,10,4)),
      (260,66458.04,667.92,2143513399,'00009194',date(2021,11,16)),
      (988,224866.40,1222.10,2143513950,'00024763',date(2023,1,23))]


def apps():
    return fetch_all("SELECT * FROM dbo.AplicacionesPago WHERE Anulada=0 AND OrigenMovimiento='galicia' AND IdMovimientoOrigen IN (219,260,988) ORDER BY IdAplicacion")


def bancos():
    return fetch_all('SELECT * FROM dbo.[Movimientos Galicia] WHERE IdMovimiento IN (219,260,988) ORDER BY IdMovimiento')


def vals():
    return fetch_all("SELECT * FROM dbo.ValuacionProveedor WHERE Origen='Galicia' AND IdOrigen IN (219,260,988) ORDER BY IdOrigen")


def main():
    oldapps=apps();bank=bancos();docs={p[3]:state(p[3]) for p in PLAN}
    if vals():
        assert len(vals())==3 and len(oldapps)==3
        for i,pesos,usd,doc,ri,fecha in PLAN:
            assert any(a['IdMovimientoOrigen']==i and a['IdDocumentoAplicado']==doc and a['ImporteAplicado']==pesos for a in oldapps)
            assert any(v['IdOrigen']==i and v['Dolares']==usd for v in vals())
        print('Pagos directos ya corregidos; sin cambios.');return
    assert len(oldapps)==3
    for i,pesos,usd,doc,ri,fecha in PLAN:
        assert next(r for r in bank if r['IdMovimiento']==i)['Débitos']==pesos
        assert docs[doc]['cabecera'][0]['IdContacto']==226
    audit={'antes':{'bancos':bank,'aplicaciones':oldapps,'documentos':docs},'plan':PLAN,
           'fuentes':{p[4]:hashlib.sha256((ROOT/f'RI_0006_{p[4]}.pdf').read_bytes()).hexdigest() for p in PLAN},
           'autorizacion':'Sergio20/10/2026: completar puntos1/2/3 deBayá','backup':backup_verificado('baya-pagos-directos-036')}
    path=ROOT/f'pagos-directos-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert apps()==oldapps and bancos()==bank and not vals() and all(state(i)==s for i,s in docs.items())
        stmts=[('UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion=?,FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=? AND Anulada=0',
                ('Reemplazada por factura literal RI7384/9194/24763 Bayá','sergio',a['IdAplicacion'])) for a in oldapps]
        for i,pesos,usd,doc,ri,fecha in PLAN:
            stmts.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,Origen,NotaConciliacion) VALUES ('galicia',?,'CompraDeuda',?,?,?,'sergio',0,'manual',?)",(i,doc,pesos,fecha,f'RI0006-{ri} original: factura y pesos íntegros.')))
            stmts.append(('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,FechaEfectoUSD,DocumentoEfectoUSD) VALUES (?,?,226,?,?,?,?,?,?)',
                          ('Galicia',i,usd,f'RI0006-{ri}', 'CréditoUSD enfecha recibo; banco real yfecha original intactos.','sergio',fecha,f'RI0006-{ri}')))
        execute_write_transaction(stmts)
        assert bancos()==bank and all(state(i)==s for i,s in docs.items()) and len(apps())==3
        audit.update(aplicacionesDespues=apps(),valuacionesDespues=vals())
    invalidar();result=cargar_cuenta(226,refrescar=True)
    for i,pesos,usd,doc,ri,fecha in PLAN:
        assert any(r['origenTipo']=='Aplicacion proveedor' and r['numeroDocumento']==f'RI0006-{ri}' and r['fecha']==fecha and r['creditoOriginal']==usd and r['creditoPesos']==0 for r in result['filas'])
    audit['cuentaDespues']=result
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'pagos':3,'imputacionesCorregidas':3,'bancosIntactos':True,'backup':audit['backup']},default=str))


if __name__=='__main__':main()
