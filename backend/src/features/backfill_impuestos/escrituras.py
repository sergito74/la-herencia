"""Mutaciones 029: transacción común, auditoría y protección de datos previos."""
import json
from uuid import UUID
from src.db.connection import reconciliation_transaction,execute_write,execute_insert_returning_id
from . import repository as repo, propuesta, respaldo
from .diagnostico import digest,money

GENERIC='Sin identificar (generada desde el pago)'

def encoded(v): return json.dumps(v,default=str,sort_keys=True,ensure_ascii=False)

def event(lote,registro,tipo,usuario,antes,despues):
    execute_write('INSERT INTO dbo.BackfillImpuestosEventos (IdLote,IdRegistro,Tipo,Usuario,Antes,Despues) VALUES (?,?,?,?,?,?)',
                  (str(lote),registro,tipo,str(usuario),encoded(antes) if antes is not None else None,encoded(despues)))

def lotes(page=1,page_size=50):
    if not repo.schema_ready(): return dict(items=[],total=0,page=page,pageSize=page_size)
    items=repo.read('SELECT IdLote AS idLote,IdOrganismo AS idOrganismo,Estado AS estado,Cantidad AS cantidad,Total AS total,Fecha AS fecha FROM dbo.BackfillImpuestosLotes ORDER BY Fecha DESC,IdLote OFFSET ? ROWS FETCH NEXT ? ROWS ONLY',((page-1)*page_size,page_size))
    return dict(items=items,total=repo.read('SELECT COUNT(*) AS n FROM dbo.BackfillImpuestosLotes')[0]['n'],page=page,pageSize=page_size)

def lote(key):
    key=str(UUID(str(key)))
    rows=repo.read('SELECT * FROM dbo.BackfillImpuestosLotes WHERE IdLote=?',(key,))
    if not rows: raise LookupError('No existe el lote')
    result=rows[0]
    result['boletas']=repo.read('SELECT IdRegistro AS idRegistro,IdImpuesto AS idImpuesto,IdImpuestoHistorico AS idImpuestoHistorico,OrigenCreacion AS origenCreacion,TieneComprobante AS tieneComprobante,CONVERT(varchar(16),Version,2) AS version FROM dbo.BackfillImpuestosBoletas WHERE IdLote=? ORDER BY IdRegistro',(key,))
    result['eventos']=repo.read('SELECT Tipo AS tipo,Usuario AS usuario,Fecha AS fecha FROM dbo.BackfillImpuestosEventos WHERE IdLote=? ORDER BY IdEvento',(key,))
    return result

def imagen(id_impuesto):
    rows=repo.read('SELECT IdImpuesto,Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado] AS Periodo,[Numero de documento] AS Numero,Importe,[Documento Original] AS Archivo,IdOperacion FROM dbo.Impuestos WHERE IdImpuesto=?',(id_impuesto,))
    if not rows: raise LookupError('La boleta ya no existe')
    return json.loads(encoded(rows[0]))

def confirmar(body,usuario):
    if not repo.schema_ready(): raise ValueError('Falta preparar el esquema 029')
    key=str(body.idLote)
    solicitud=digest(dict(organismoId=body.organismoId,huellaPropuesta=body.huellaPropuesta,
                         decisiones=[d.model_dump() for d in body.decisiones]))
    def existente():
        rows=repo.read('SELECT HashSolicitud FROM dbo.BackfillImpuestosLotes WHERE IdLote=?',(key,))
        if not rows: return None
        if rows[0]['HashSolicitud']!=solicitud: raise ValueError('El identificador de lote ya fue usado para otra selección')
        return dict(repetido=True,lote=lote(key))
    previous=existente()
    if previous: return previous
    respaldo.check_preparacion(body.preparacion,'confirmar',body.huellaPropuesta,usuario)
    respaldo.verificar(body.backupId,body.preparacion)
    with reconciliation_transaction():
        previous=existente()
        if previous: return previous
        s=propuesta.full(body.organismoId);v=propuesta.validar(body,s)
        if v['huellaPropuesta']!=body.huellaPropuesta: raise ValueError('La selección cambió; revisá otra vez')
        execute_write('INSERT INTO dbo.BackfillImpuestosLotes (IdLote,IdOrganismo,Estado,HuellaPropuesta,HashSolicitud,Usuario,BackupId,Cantidad,Total) VALUES (?,?,?,?,?,?,?,?,?)',
                      (key,body.organismoId,'confirmado',body.huellaPropuesta,solicitud,str(usuario),str(body.backupId),v['cantidad'],v['total']))
        for selected in v['seleccion']:
            p,d,f=selected['pago'],selected['decision'],selected['archivo']
            if d['tipoImpuesto']['modo']=='generico':
                types=repo.read('SELECT IdTipoImpuesto FROM dbo.[Tipo Impuesto] WHERE IdOrganismo=? AND [Nombre Impuesto]=?',(body.organismoId,GENERIC))
                if len(types)>1: raise ValueError('Catálogo genérico duplicado: revisar antes de cargar')
                tipo=types[0]['IdTipoImpuesto'] if types else execute_insert_returning_id('INSERT INTO dbo.[Tipo Impuesto] (IdOrganismo,[Nombre Impuesto]) OUTPUT INSERTED.IdTipoImpuesto VALUES (?,?)',(body.organismoId,GENERIC))
            else: tipo=d['tipoImpuesto']['idTipoImpuesto']
            # La boleta se carga solo por lo que ningún otro documento cubre
            # (importeAGenerar); el vínculo, más abajo, registra el pago
            # completo para que el pago quede respaldado en la próxima corrida.
            impuesto=execute_insert_returning_id('INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) OUTPUT INSERTED.IdImpuesto VALUES (?,?,?,?,?,?,?)',
                (p['fecha'],body.organismoId,tipo,d['periodoLiquidado'],d['numeroDocumento'],money(p['importeAGenerar']),f['ruta'] if f else None))
            snap=imagen(impuesto)
            reg=execute_insert_returning_id('INSERT INTO dbo.BackfillImpuestosBoletas (IdLote,IdImpuesto,IdImpuestoHistorico,OrigenCreacion,TieneComprobante,ArchivoHash,SnapshotCreacion) OUTPUT INSERTED.IdRegistro VALUES (?,?,?,?,?,?,?)',
                (key,impuesto,impuesto,d['fuente'],bool(f),f['hash'] if f else None,encoded(snap)))
            execute_write('INSERT INTO dbo.BackfillImpuestosVinculos (IdLote,Medio,IdMovimiento,IdOrganismo,IdImpuesto,Importe,HuellaPago) VALUES (?,?,?,?,?,?,?)',
                (key,p['medio'],p['idMovimiento'],body.organismoId,impuesto,money(p['importe']),p['huella']))
            event(key,reg,'confirmar',usuario,None,dict(boleta=snap,pago=p,decision=d))
        result=lote(key)
    return dict(repetido=False,lote=result)

def metadata(ids):
    if not ids or not repo.schema_ready(): return {}
    result={}
    for start in range(0,len(ids),100):
        chunk=ids[start:start+100];marks=','.join('?' for _ in chunk)
        rows=repo.read(f'SELECT IdImpuesto AS idImpuesto,IdLote AS idLote,OrigenCreacion AS origenCreacion,TieneComprobante AS tieneComprobante,CONVERT(varchar(16),Version,2) AS version FROM dbo.BackfillImpuestosBoletas WHERE IdImpuesto IN ({marks})',tuple(chunk))
        for row in rows:
            row['generadaDesdePago']=row['origenCreacion']=='generada' and not row['tieneComprobante']
            result[row['idImpuesto']]=row
    return result

def propio(i,version):
    rows=repo.read('SELECT IdRegistro,IdLote,SnapshotCreacion,CONVERT(varchar(16),Version,2) AS version FROM dbo.BackfillImpuestosBoletas WHERE IdImpuesto=?',(i,))
    if not rows: raise LookupError('La boleta no fue creada por 029')
    if rows[0]['version'].lower()!=version.lower(): raise ValueError('La boleta cambió. Refrescá antes de editar.')
    return rows[0]

def cambiar_tipo(i,body,usuario):
    with reconciliation_transaction():
        b=propio(i,body.version);before=imagen(i)
        if not any(t['idTipoImpuesto']==body.idTipoImpuesto for t in repo.tipos_del_organismo(before['IdOrganismo'])):
            raise ValueError('Tipo de impuesto ajeno al organismo')
        if execute_write('UPDATE dbo.Impuestos SET IdTipoImpuesto=? WHERE IdImpuesto=?',(body.idTipoImpuesto,i))!=1: raise ValueError('La boleta cambió')
        execute_write('UPDATE dbo.BackfillImpuestosBoletas SET TieneComprobante=TieneComprobante WHERE IdImpuesto=?',(i,))
        event(b['IdLote'],b['IdRegistro'],'cambiar_tipo',usuario,before,imagen(i))
        return metadata([i])[i]

def adjuntar(i,body,usuario):
    from . import documentos
    with reconciliation_transaction():
        b=propio(i,body.version);before=imagen(i)
        s=propuesta.full(before['IdOrganismo'])
        f=next((f for f in s['archivos'] if f['archivoId']==body.archivoId),None)
        if not f: raise LookupError('El archivo no está disponible')
        if not s['coberturaBusqueda'] or f['usado'] or f['idOrganismo']!=before['IdOrganismo']: raise ValueError('Archivo usado, no reconocido o búsqueda incompleta')
        if execute_write('UPDATE dbo.Impuestos SET [Documento Original]=? WHERE IdImpuesto=?',(f['ruta'],i))!=1: raise ValueError('La boleta cambió')
        execute_write('UPDATE dbo.BackfillImpuestosBoletas SET TieneComprobante=1,ArchivoHash=? WHERE IdImpuesto=?',(f['hash'],i))
        event(b['IdLote'],b['IdRegistro'],'adjuntar',usuario,before,imagen(i))
        return metadata([i])[i]

def revisar_reversion(key):
    l=lote(key)
    if l['Estado']=='revertido': return dict(revertido=True,huellaReversion=digest(str(key)),bloqueos=[])
    rows=repo.read('SELECT IdRegistro,IdImpuesto,SnapshotCreacion FROM dbo.BackfillImpuestosBoletas WHERE IdLote=? ORDER BY IdRegistro',(str(key),))
    bloqueos=[];snapshots=[]
    if any(e['tipo']!='confirmar' for e in l['eventos']): bloqueos.append('El lote tiene ediciones posteriores')
    for row in rows:
        i=row['IdImpuesto']
        current=imagen(i);snapshots.append(current)
        if current!=json.loads(row['SnapshotCreacion']): bloqueos.append(f'Boleta {i} modificada')
        refs=repo.read("SELECT COUNT(*) AS n FROM dbo.ConciliacionesTesoreria WHERE TipoOrigenDocumento='Impuestos' AND IdOrigenDocumento=?",(i,))[0]['n']
        refs+=repo.read('SELECT COUNT(*) AS n FROM dbo.Tarjetas_Resumenes_Lineas_Compras WHERE IdImpuesto=?',(i,))[0]['n']
        if refs: bloqueos.append(f'Boleta {i} tiene nuevos vínculos')
    links=repo.read('SELECT * FROM dbo.BackfillImpuestosVinculos WHERE IdLote=? ORDER BY IdVinculo',(str(key),))
    if len(links)!=len(rows): bloqueos.append('Los vínculos del lote cambiaron')
    return dict(revertido=False,bloqueos=bloqueos,huellaReversion=digest(dict(lote=l,boletas=snapshots,vinculos=links)),boletas=rows,vinculos=links)

def revertir(key,body,usuario):
    if lote(key)['Estado']=='revertido': return lote(key)
    respaldo.check_preparacion(body.preparacion,'revertir',body.huellaReversion,usuario)
    respaldo.verificar(body.backupId,body.preparacion)
    with reconciliation_transaction():
        report=revisar_reversion(key)
        if report['revertido']: return lote(key)
        if report['bloqueos'] or report['huellaReversion']!=body.huellaReversion: raise ValueError('El lote tiene cambios o dependencias posteriores; no se revirtió ninguna fila')
        execute_write('DELETE FROM dbo.BackfillImpuestosVinculos WHERE IdLote=?',(str(key),))
        for b in report['boletas']:
            execute_write('UPDATE dbo.BackfillImpuestosBoletas SET IdImpuesto=NULL WHERE IdRegistro=?',(b['IdRegistro'],))
            if execute_write('DELETE FROM dbo.Impuestos WHERE IdImpuesto=?',(b['IdImpuesto'],))!=1: raise ValueError('La boleta cambió')
        execute_write("UPDATE dbo.BackfillImpuestosLotes SET Estado='revertido',FechaReversion=SYSUTCDATETIME(),UsuarioReversion=? WHERE IdLote=?",(str(usuario),str(key)))
        event(key,None,'revertir',usuario,report,dict(backupId=str(body.backupId)))
        return lote(key)
