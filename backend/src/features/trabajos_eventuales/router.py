from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from src.features.trabajos_eventuales import repository as repo
from src.features.trabajos_eventuales.schemas import TrabajoInput, VinculoInput, Trabajo, Lista, Liquidacion

router = APIRouter(prefix="/api/trabajos-eventuales", tags=["trabajos-eventuales"])


def usuario(request):
    return str(getattr(request.state, "usuario", {}).get("idUsuario", "sistema"))


async def ejecutar(fn, *args):
    try:
        resultado = await run_in_threadpool(fn, *args)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if resultado is None:
        raise HTTPException(404, "No se encontró el registro")
    return resultado


@router.get("", response_model=Lista)
async def listar(idContacto: int | None = Query(None, gt=0), desde: date | None = None, hasta: date | None = None,
                 estadoPago: Literal["Pendiente", "Pagado"] | None = None,
                 vinculacion: Literal["sin", "parcial", "completo"] | None = None,
                 idSalario: int | None = Query(None, gt=0), page: int = Query(1, ge=1), pageSize: int = Query(50, ge=1, le=100)):
    if desde and hasta and desde > hasta:
        raise HTTPException(400, "La fecha desde debe ser anterior a la fecha hasta")
    return await ejecutar(repo.listar, idContacto, desde, hasta, estadoPago, vinculacion, idSalario, page, pageSize)


@router.post("", status_code=201, response_model=Trabajo)
async def crear(body: TrabajoInput, request: Request):
    return await ejecutar(repo.guardar, body, usuario(request))


@router.get("/{id_trabajo}", response_model=Trabajo)
async def detalle(id_trabajo: int):
    return await ejecutar(repo.obtener, id_trabajo)


@router.patch("/{id_trabajo}", response_model=Trabajo)
async def editar(id_trabajo: int, body: TrabajoInput, request: Request):
    return await ejecutar(repo.guardar, body, usuario(request), id_trabajo)


@router.get("/{id_trabajo}/liquidaciones", response_model=list[Liquidacion])
async def liquidaciones(id_trabajo: int):
    return await ejecutar(repo.liquidaciones, id_trabajo)


@router.post("/{id_trabajo}/vinculos", status_code=201, response_model=Trabajo)
async def vincular(id_trabajo: int, body: VinculoInput, request: Request):
    return await ejecutar(repo.vincular, id_trabajo, body.idSalario, body.importe, usuario(request))


@router.delete("/{id_trabajo}/vinculos/{id_salario}", response_model=Trabajo)
async def desvincular(id_trabajo: int, id_salario: int, request: Request):
    return await ejecutar(repo.desvincular, id_trabajo, id_salario, usuario(request))
