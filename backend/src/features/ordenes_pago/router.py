from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response

from src.features.boveda.router import exigir_admin, usuario_actual
from src.features.ordenes_pago import repository as repo
from src.features.ordenes_pago.schemas import (Estado, ExclusionInput, FacturaPendiente, ListaOrdenes, Movimiento, Orden, OrdenInput,
                                               PropuestaInput, RubroInput, VincularInput)
from src.features.retenciones_ganancias import mail, padron, repository as retenciones

router = APIRouter(prefix='/api/ordenes-pago', tags=['ordenes-pago'])


def llamar(fn, *args):
    try:
        return fn(*args)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ConnectionError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get('', response_model=ListaOrdenes)
def listar(idContacto: int | None = Query(None, gt=0), estado: Estado | None = None,
           page: int = Query(1, ge=1), pageSize: int = Query(50, ge=1, le=100)):
    return repo.listar(idContacto, estado, page, pageSize)


@router.get('/facturas', response_model=list[FacturaPendiente])
def facturas(idContacto: int = Query(...,gt=0), excluirOrden: int | None = Query(None,gt=0), incluirSaldadas: bool = False):
    return repo.facturas(idContacto, excluirOrden, incluirSaldadas)


@router.get('/movimientos', response_model=list[Movimiento])
def movimientos(idContacto: int = Query(...,gt=0)):
    return repo.movimientos(idContacto)


@router.get('/recibos')
def recibos(idContacto: int | None = Query(None,gt=0), revisados: bool = False,
            page: int = Query(1,ge=1), pageSize: int = Query(50,ge=1,le=100)):
    return repo.recibos(idContacto, revisados, page, pageSize)


@router.get('/recibos/{id_documento}/pdf')
def pdf(id_documento: int):
    path = llamar(repo.pdf_recibo, id_documento)
    return FileResponse(path, media_type='application/pdf', filename=path.name, content_disposition_type='inline')


@router.post('/recibos/{id_documento}/vincular', dependencies=[Depends(exigir_admin)])
def vincular(id_documento: int, body: VincularInput, request: Request):
    return llamar(repo.vincular,id_documento,body,usuario_actual(request))


@router.post('/retenciones/proponer')
def proponer_retencion(body: PropuestaInput):
    facturas = [{'idCompra': f.idCompra, 'importe': f.importe} for f in body.facturas]
    return llamar(retenciones.proponer, body.idContacto, body.fechaPago, facturas, body.excluirOrden)


@router.get('/retenciones/regimenes')
def regimenes():
    return llamar(retenciones.regimenes)


@router.get('/retenciones/rubros')
def rubros():
    return retenciones.rubros()


@router.put('/retenciones/rubros/{id_rubro}', dependencies=[Depends(exigir_admin)])
def guardar_rubro(id_rubro: int, body: RubroInput, request: Request):
    retenciones.guardar_rubro(id_rubro, body.codRegimen, body.estado, body.observaciones, usuario_actual(request))
    return {'ok': True}


@router.get('/retenciones/exclusiones')
def exclusiones(idContacto: int | None = Query(None, gt=0)):
    return retenciones.exclusiones(idContacto)


@router.post('/retenciones/exclusiones', dependencies=[Depends(exigir_admin)])
def agregar_exclusion(body: ExclusionInput, request: Request):
    if body.hasta < body.desde:
        raise HTTPException(422, 'La vigencia termina antes de empezar')
    retenciones.agregar_exclusion(body.idContacto, body.desde, body.hasta, body.observaciones, usuario_actual(request))
    return {'ok': True}


@router.delete('/retenciones/exclusiones/{id_exclusion}', dependencies=[Depends(exigir_admin)])
def borrar_exclusion(id_exclusion: int):
    retenciones.borrar_exclusion(id_exclusion)
    return {'ok': True}


@router.post('/retenciones/padron', dependencies=[Depends(exigir_admin)])
def actualizar_padron():
    return llamar(padron.actualizar)


@router.get('/{id_}/mail-estudio')
def mail_estudio(id_: int):
    orden = llamar(repo.obtener, id_)
    eml, _ = mail.armar(orden)
    nombre = f'OP{id_:06d}-retencion.eml'
    return Response(eml, media_type='message/rfc822', headers={'Content-Disposition': f'attachment; filename="{nombre}"'})


@router.get('/{id_}', response_model=Orden)
def obtener(id_: int):
    return llamar(repo.obtener,id_)


@router.post('', response_model=Orden, dependencies=[Depends(exigir_admin)])
def crear(body: OrdenInput, request: Request):
    return llamar(repo.guardar,body,usuario_actual(request))


@router.patch('/{id_}', response_model=Orden, dependencies=[Depends(exigir_admin)])
def editar(id_: int, body: OrdenInput, request: Request):
    return llamar(repo.guardar,body,usuario_actual(request),id_)


@router.post('/{id_}/emitir', response_model=Orden, dependencies=[Depends(exigir_admin)])
def emitir(id_: int, request: Request):
    return llamar(repo.cambiar_estado,id_,'Emitida',usuario_actual(request))


@router.post('/{id_}/anular', response_model=Orden, dependencies=[Depends(exigir_admin)])
def anular(id_: int, request: Request):
    return llamar(repo.cambiar_estado,id_,'Anulada',usuario_actual(request))
