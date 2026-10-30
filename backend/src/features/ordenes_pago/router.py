from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from src.features.boveda.router import exigir_admin, usuario_actual
from src.features.ordenes_pago import repository as repo
from src.features.ordenes_pago.schemas import Estado, FacturaPendiente, ListaOrdenes, Movimiento, Orden, OrdenInput, VincularInput

router = APIRouter(prefix='/api/ordenes-pago', tags=['ordenes-pago'])


def llamar(fn, *args):
    try:
        return fn(*args)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


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
