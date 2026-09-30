from collections import Counter
from datetime import date
from . import repository,documentos
from .diagnostico import digest,money,ZERO

def emparejar(pagos,files,org,complete):
    candidates={}
    for p in pagos:
        key=(p['medio'],p['idMovimiento'])
        candidates[key]=[f for f in files if not f['usado'] and f['idOrganismo']==org and f['fecha'] and p['fecha'] and abs((date.fromisoformat(p['fecha'])-date.fromisoformat(f['fecha'])).days)<=7]
    counts=Counter(f['archivoId'] for values in candidates.values() for f in values)
    result=[]
    for p in pagos:
        fs=candidates[(p['medio'],p['idMovimiento'])]
        source='pendiente'
        if p['estado']=='faltante' and complete:
            if not fs: source='generada'
            elif len(fs)==1 and counts[fs[0]['archivoId']]==1: source='comprobante'
        result.append(dict(**p,fuente=source,candidatos=[{k:v for k,v in f.items() if k!='ruta'} for f in fs],
                           tipoImpuesto={'modo':'generico'}))
    return result

def full(org):
    s=repository.snapshot(org)
    usados=repository.read("SELECT [Documento Original] AS ruta FROM dbo.Impuestos WHERE [Documento Original] IS NOT NULL UNION ALL SELECT [Documento Original] FROM dbo.Compras WHERE [Documento Original] IS NOT NULL")
    files=documentos.inventario(repository.organismos(),[x['ruta'] for x in usados])
    s['items']=emparejar(s['items'],files['items'],org,files['completo'])
    s['coberturaBusqueda']=files['completo'];s['advertencias']+=files['advertencias']
    s['archivos']=files['items']
    s['huellaFuente']=digest(dict(datos=s['huellaFuente'],archivos=files,politica=1))
    return s

def public(s,page=1,page_size=50):
    s=dict(s);s.pop('boletas',None)
    s['archivos']=[{k:v for k,v in f.items() if k!='ruta'} for f in s['archivos']]
    s['items']=s['items'][(page-1)*page_size:page*page_size]
    return dict(s,page=page,pageSize=page_size)

def validar(body,s):
    if body.huellaFuente!=s['huellaFuente']: raise ValueError('La propuesta cambió. Volvé a revisarla.')
    by_key={(p['medio'],p['idMovimiento']):p for p in s['items']}
    files={f['archivoId']:f for f in s['archivos']}
    selected=[];seen=set()
    for d in body.decisiones:
        if d.accion=='excluir': continue
        p=by_key.get((d.medio,d.idMovimiento))
        if not p or p['estado']!='faltante' or not s['coberturaBusqueda']:
            raise ValueError('Pago pendiente o búsqueda incompleta: no puede confirmarse')
        if d.tipoImpuesto.modo=='existente' and not any(t['idTipoImpuesto']==d.tipoImpuesto.idTipoImpuesto for t in s['tipos']):
            raise ValueError('Tipo de impuesto ajeno al organismo')
        f=None
        if d.fuente=='comprobante':
            if d.archivoId not in [c['archivoId'] for c in p['candidatos']]: raise ValueError('El archivo no es un candidato vigente')
            f=files[d.archivoId]
            if f['hash'] in seen or f['usado']: raise ValueError('El comprobante ya está usado')
            seen.add(f['hash'])
        elif p['candidatos']: raise ValueError('Hay comprobantes pendientes de revisión; no generar')
        selected.append(dict(pago=p,decision=d.model_dump(),archivo=f))
    if not selected: raise ValueError('Elegí al menos un pago confirmable')
    total=sum((money(x['pago']['importeAGenerar']) for x in selected),ZERO)
    fingerprint=digest(dict(fuente=body.huellaFuente,decisiones=[d.model_dump() for d in body.decisiones]))
    return dict(seleccion=selected,huellaPropuesta=fingerprint,total=total,cantidad=len(selected),saldoProyectado=money(s['saldoActual'])+total)
