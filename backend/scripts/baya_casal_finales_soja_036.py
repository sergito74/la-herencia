"""Finales DRC0kg y aplicaciones reales de enero/mayo, con originales."""
from pathlib import Path
from datetime import date,datetime
from decimal import Decimal
import json,shutil,hashlib
from src.db.connection import fetch_all,execute_write_transaction,reconciliation_transaction,_reconciliation_connection
from src.features.vinculos.backup import backup_verificado
from src.features.ventas_granos.repository import create_venta,get_venta_cabecera,get_ajustes,get_deducciones,calcular_totales
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta,invalidar

ROOT=Path(__file__).resolve().parents[2]/'backups/baya-conciliacion-20261019'
DEST=Path(r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\04 2024 - 03 2025')
NUMBERS=('330226576206','330226576221')
D=Decimal


def apps():
    return fetch_all("SELECT * FROM dbo.AplicacionesPago WHERE Anulada=0 AND ((OrigenMovimiento='valores-recibidos' AND IdMovimientoOrigen=18) OR (OrigenMovimiento='comp-compra' AND IdMovimientoOrigen IN (?,?)) OR (TipoDocumento='CompraDeuda' AND IdDocumentoAplicado IN (?,?))) ORDER BY IdAplicacion",(2143515173,2143515167,2143514757,2143514758))


def granos(i):
    return {'cabecera':get_venta_cabecera(i),'ajustes':get_ajustes(i),'deducciones':get_deducciones(i)}


def main():
    assert not fetch_all('SELECT IdVenta FROM dbo.[Venta Granos] WHERE [Nro Documento] IN (?,?)',NUMBERS)
    oldapps=apps();assert len(oldapps)==9
    oldgranos={i:granos(i) for i in (177,1230)}
    cheque=fetch_all('SELECT * FROM dbo.[Valores Recibidos] WHERE IdValor=?',(18,))[0]
    assert cheque['Importe']==8137687.2 and cheque['IdReceptor']==226
    assert not fetch_all("SELECT * FROM dbo.ValuacionProveedor WHERE Origen='Pagos Valores Recibidos' AND IdOrigen=18")
    files=[]
    for number,short in zip(NUMBERS,('26576206','26576221')):
        source=ROOT/f'canje-conjunto-{short}.pdf';target=DEST/f'20240904_BayaCasal_LC{number}.pdf'
        assert source.is_file()
        if target.exists():assert target.read_bytes()==source.read_bytes()
        else:shutil.copy2(source,target)
        files.append(target)
    audit={'autorizacion':'Sergio20/10/2026: cargar finales y reproducir aplicaciones del proveedor',
           'granosOriginales':oldgranos,'chequeAntes':cheque,'aplicacionesAntes':oldapps,'pdfs':[{ 'archivo':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
           'respaldo':backup_verificado('baya-finales-soja-036')}
    path=ROOT/f'finales-soja-alta-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    with reconciliation_transaction():
        assert apps()==oldapps and all(granos(i)==s for i,s in oldgranos.items())
        conn=_reconciliation_connection.get()
        for name,definition in [('FechaEfectoUSD','date NULL'),('DocumentoEfectoUSD','varchar(50) NULL')]:
            assert name in ('FechaEfectoUSD','DocumentoEfectoUSD')
            if fetch_all('SELECT COL_LENGTH(?,?) n',('dbo.ValuacionProveedor',name))[0]['n'] is None:
                conn.cursor().execute(f'ALTER TABLE dbo.ValuacionProveedor ADD {name} {definition}')
        new_ids=[]
        for n,amount,original,pdf in zip(NUMBERS,(75227.5,4502.5),('330223253060','330223253039'),files):
            cab={'idConsignatario':226,'idTipoDocumento':6,'idProducto':8,'numeroDocumento':n,'fecha':date(2024,9,4),
                 'precioUnitario':100000,'tipoCambio':None,'campania':'2022/2023','factor':100,'flete':0,
                 'cantidadEntregada':0,'cantidadVendida':0,'alicuotaIVA':0,'documentoOriginal':str(pdf)}
            new_id=create_venta(cab,[{'concepto':f'Pago a Cuenta (DRC). COE original {original}','importe':amount,'alicuotaIVA':0}],[])
            assert round(calcular_totales(get_venta_cabecera(new_id),get_ajustes(new_id),[])['importeNetoAPercibir'],2)==amount
            new_ids.append(new_id)
        lc206,lc221=new_ids
        # Enero: aplicar la NC de cambio a las facturas que cita; crédito
        # bruto por factura=neto de diferencia más IVA21%, mayores restos.
        jan=datetime(2025,1,9);may=datetime(2025,5,22)
        plan=[('comp-compra',2143515173,2143514757,D('20770.93'),jan),
              ('comp-compra',2143515173,2143514758,D('108498.88'),jan),
              ('valores-recibidos',18,2143514757,D('1308009.27'),jan),
              ('valores-recibidos',18,2143514758,D('6829677.93'),jan),
              ('comp-venta-granos',lc221,2143514758,D('2828.14'),jan),
              ('comp-venta-granos',lc206,2143514876,D('75227.50'),may),
              ('comp-venta-granos',lc221,2143514876,D('1674.36'),may),
              ('comp-compra',2143515167,2143514876,D('16248.54'),may)]
        # En mayo el proveedor aplica13427.83+IVA2820.71 de NC120722,
        # no los16252.67 del fiscal: quedan4.13 sin reconocimiento.
        assert sum(a for m,i,t,a,f in plan if t==2143514757)==D('1328780.20')
        assert sum(a for m,i,t,a,f in plan if t==2143514758)==D('6941004.95')
        assert sum(a for m,i,t,a,f in plan if f==may)==D('93150.40')
        stmts=[]
        for a in oldapps:stmts.append(('UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion=?,FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=? AND Anulada=0',('Reemplazada por CA115924/CA123088 originales de Bayá (036)','sergio',a['IdAplicacion'])))
        for medio,origin,doc,amount,fecha in plan:stmts.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,Origen,NotaConciliacion) VALUES (?,?,'CompraDeuda',?,?,?,'sergio',0,'manual',?)",(medio,origin,doc,amount,fecha,'CA115924 enero / CA123088 mayo. Importes libro proveedor; NC120722 fiscal difiere4.13, no imputados.')))
        stmts.append(('UPDATE dbo.[Valores Recibidos] SET [Fecha Endoso]=? WHERE IdValor=?',(datetime(2024,12,30),18)))
        for origin,i,usd,fecha,doc,note in [
            ('Venta Granos',lc206,D('81.36'),may,'CA0006-00123088','Parte proporcional a LC206 del creditoUSD83.17 sobre76901.86; original enpesos. Total externo yfecha exactos, reparto interno por pesos.'),
            ('Venta Granos',lc221,D('1.81'),may,'CA0006-00123088','Parte proporcional al remanenteLC221 de1674.36;2828.14 ya usados enenero sinUSDadicional.'),
            ('Pagos Valores Recibidos',18,D('7913.67'),jan,'CA0006-00115924','Cheque recibido30/12/2024 enpesos y aplicado09/01/2025. USD7913.67 reconocidos por proveedor.')]:
            stmts.append(('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,FechaEfectoUSD,DocumentoEfectoUSD) VALUES (?,?,226,?,?,?, ?,?,?)',(origin,i,usd,'Bayá: originales CA115924/123088 y LC26576206/221',note,'sergio',fecha,doc)))
        execute_write_transaction(stmts)
        for key,expected in [(lc206,D('75227.50')),(lc221,D('4502.50'))]:
            applied=fetch_all("SELECT SUM(ImporteAplicado) s FROM dbo.AplicacionesPago WHERE Anulada=0 AND OrigenMovimiento='comp-venta-granos' AND IdMovimientoOrigen=?",(key,))[0]['s']
            assert D(str(applied))==expected
        assert all(granos(i)==s for i,s in oldgranos.items())
        cash=fetch_all("SELECT SUM(ImporteAplicado) s FROM dbo.AplicacionesPago WHERE Anulada=0 AND OrigenMovimiento='valores-recibidos' AND IdMovimientoOrigen=18")[0]['s'];assert cash==8137687.2
        audit.update(IdVentas=new_ids,planAplicacion=plan,finalesDespues={i:granos(i) for i in new_ids},NC120722DiferenciaNoAplicada='4.13',
                     valuaciones=fetch_all('SELECT * FROM dbo.ValuacionProveedor WHERE (Origen=? AND IdOrigen IN (?,?)) OR (Origen=? AND IdOrigen=18)',('Venta Granos',lc206,lc221,'Pagos Valores Recibidos')))
    invalidar();result=cargar_cuenta(226,refrescar=True)
    events=[r for r in result['filas'] if r['origenTipo']=='Aplicacion proveedor']
    assert any(r['numeroDocumento']=='CA0006-00123088' and r['fecha']==date(2025,5,22) and r['creditoOriginal']==83.17 and r['creditoPesos']==0 for r in events)
    assert any(r['numeroDocumento']=='CA0006-00115924' and r['fecha']==date(2025,1,9) and r['creditoOriginal']==7913.67 and r['creditoPesos']==0 for r in events)
    original_final_rows=[r for r in result['filas'] if r['origenTipo']=='Venta Granos' and r['idOrigen'] in new_ids]
    assert len(original_final_rows)==2 and all(r['fecha']==date(2024,9,4) for r in original_final_rows)
    audit.update(eventosUSDVerificados=events)
    path.write_text(json.dumps(audit,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'IdVentas':new_ids,'totalPesos':79730,'kilosNuevos':0,'creditoMayoUSD':83.17,'aplicaciones':len(plan),'diferenciaFiscalNC120722':4.13,'respaldo':audit['respaldo']},default=str))


if __name__=='__main__':main()
