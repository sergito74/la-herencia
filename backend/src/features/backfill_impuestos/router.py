from decimal import Decimal
from fastapi import APIRouter, Query, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
import pyodbc
from . import repository

router=APIRouter(prefix='/api/impuestos/backfill',tags=['backfill-impuestos'])

async def call(fn,*args):
    try:
        result=await run_in_threadpool(fn,*args)
        return JSONResponse(jsonable_encoder(result,custom_encoder={Decimal:lambda v:format(v,'.2f')}))
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc
    except ValueError as exc: raise HTTPException(409,str(exc)) from exc
    except (pyodbc.Error,OSError) as exc: raise HTTPException(503,'No se pudo leer la fuente; no se emitió un resultado parcial.') from exc

@router.get('/diagnostico')
async def diagnostico(organismoId:int|None=Query(None,gt=0),page:int=Query(1,ge=1),pageSize:int=Query(50,ge=1,le=200)):
    return await call(repository.diagnostico,organismoId,page,pageSize)

from fastapi import Request, Header
from fastapi.responses import FileResponse
from uuid import UUID
from . import propuesta,respaldo,escrituras
from .schemas import Validar,Confirmar,TipoPatch,ArchivoPatch,Revertir

def usuario(request): return str(request.state.usuario['idUsuario'])

def propuesta_pagina(org,page,size): return propuesta.public(propuesta.full(org),page,size)

@router.get('/propuesta')
async def proponer(organismoId:int=Query(gt=0),page:int=Query(1,ge=1),pageSize:int=Query(50,ge=1,le=200)):
    return await call(propuesta_pagina,organismoId,page,pageSize)

@router.get('/comprobantes/{archivoId}')
async def archivo(archivoId:str,organismoId:int=Query(gt=0)):
    try:
        s=await run_in_threadpool(propuesta.full,organismoId)
        f=next((f for f in s['archivos'] if f['archivoId']==archivoId),None)
        if not f: raise HTTPException(404,'No se encontró el archivo o cambió desde la revisión')
        return FileResponse(f['ruta'],filename=f['nombre'],content_disposition_type='inline')
    except (pyodbc.Error,OSError) as exc: raise HTTPException(503,'No se pudo leer el comprobante') from exc

def validar_preparar(body,user):
    s=propuesta.full(body.organismoId);v=propuesta.validar(body,s)
    v.pop('seleccion')
    v['preparacion']=respaldo.preparar('confirmar',v['huellaPropuesta'],user)
    return v

@router.post('/validar')
async def validar(body:Validar,request:Request):
    return await call(validar_preparar,body,usuario(request))

@router.get('/respaldo')
async def backup(request:Request,x_backfill_preparacion:str=Header(max_length=4096)):
    return await call(respaldo.estado,x_backfill_preparacion,usuario(request))

def crear_respaldo(token,user):
    p=respaldo.decode(token)
    respaldo.check_preparacion(token,p.get('finalidad'),p.get('huella'),user)
    e=respaldo.crear(token)
    return dict(estado='verificado',backupId=e['backupId'],verificadoEn=e['verificadoEn'])

# App de un solo usuario en su propia PC: el backup verificado se dispara
# desde la pantalla en vez de exigir copiar un comando a una terminal.
@router.post('/respaldo')
async def backup_crear(request:Request,x_backfill_preparacion:str=Header(max_length=4096)):
    return await call(crear_respaldo,x_backfill_preparacion,usuario(request))

@router.post('/confirmar')
async def confirmar(body:Confirmar,request:Request):
    response=await call(escrituras.confirmar,body,usuario(request))
    import json
    if response.status_code==200 and not json.loads(response.body).get('repetido'): response.status_code=201
    return response

@router.get('/lotes')
async def lotes(page:int=Query(1,ge=1),pageSize:int=Query(50,ge=1,le=200)):
    return await call(escrituras.lotes,page,pageSize)

@router.get('/lotes/{idLote}')
async def lote(idLote:UUID): return await call(escrituras.lote,idLote)

@router.patch('/boletas/{idImpuesto}/tipo')
async def tipo(idImpuesto:int,body:TipoPatch,request:Request):
    return await call(escrituras.cambiar_tipo,idImpuesto,body,usuario(request))

@router.patch('/boletas/{idImpuesto}/comprobante')
async def adjuntar(idImpuesto:int,body:ArchivoPatch,request:Request):
    return await call(escrituras.adjuntar,idImpuesto,body,usuario(request))

def preparar_reversion(key,user):
    r=escrituras.revisar_reversion(key)
    r.pop('boletas',None);r.pop('vinculos',None)
    if not r['bloqueos']: r['preparacion']=respaldo.preparar('revertir',r['huellaReversion'],user)
    return r

@router.post('/lotes/{idLote}/reversion/validar')
async def reversion_validar(idLote:UUID,request:Request):
    return await call(preparar_reversion,idLote,usuario(request))

@router.post('/lotes/{idLote}/revertir')
async def revertir(idLote:UUID,body:Revertir,request:Request):
    return await call(escrituras.revertir,idLote,body,usuario(request))
