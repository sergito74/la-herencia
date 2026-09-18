"""Resúmenes de tarjeta endpoints (Historia 1, 008-tarjetas). Todo
`POST`/`PUT`/`DELETE` escribe exclusivamente contra `WC`."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Header, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.tarjetas_resumenes import repository, repository_locks
from src.features.tarjetas_resumenes.schemas import (
    LockRequest,
    LockResponse,
    ResumenAltaRequest,
    ResumenDetalleResponse,
    ResumenEditRequest,
    ResumenesListResponse,
    ResumenListItem,
)

router = APIRouter(prefix="/api/tarjetas-resumenes", tags=["tarjetas-resumenes"])


@router.get("", response_model=ResumenesListResponse)
async def list_resumenes(
    idTarjeta: int | None = Query(default=None),
    fechaCierreDesde: date | None = Query(default=None),
    fechaCierreHasta: date | None = Query(default=None),
    fechaVencimientoDesde: date | None = Query(default=None),
    fechaVencimientoHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> ResumenesListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_resumenes,
        idTarjeta,
        fechaCierreDesde,
        fechaCierreHasta,
        fechaVencimientoDesde,
        fechaVencimientoHasta,
        norm_page,
        norm_page_size,
    )
    return ResumenesListResponse(
        items=[ResumenListItem(**row) for row in rows], page=norm_page, pageSize=norm_page_size, total=total
    )


def _cabecera_dict(body: ResumenAltaRequest) -> dict:
    return body.model_dump(exclude={"lineas"})


def _to_detalle_response(id_resumen: int, cabecera: dict, lineas_out: list[dict], warnings: list[str]) -> ResumenDetalleResponse:
    total = repository.calcular_total(cabecera, lineas_out)
    cabecera_sin_id = {k: v for k, v in cabecera.items() if k != "idResumen"}
    return ResumenDetalleResponse(
        idResumen=id_resumen,
        **cabecera_sin_id,
        totalCalculado=total,
        lineas=lineas_out,
        warnings=warnings,
    )


async def _warnings_duplicado(id_tarjeta: int, codigo: str, excluir_id_resumen: int | None = None) -> list[str]:
    """FR-012: advertencia no bloqueante — nunca rechaza el guardado."""
    duplicado = await run_in_threadpool(repository.hay_resumen_duplicado, id_tarjeta, codigo, excluir_id_resumen)
    if duplicado:
        return ["Ya existe un resumen con este código para esta tarjeta."]
    return []


@router.post("", response_model=ResumenDetalleResponse, status_code=201)
async def crear_resumen(body: ResumenAltaRequest) -> ResumenDetalleResponse:
    cabecera = _cabecera_dict(body)
    lineas = [linea.model_dump() for linea in body.lineas]

    # FR-012: chequear duplicado ANTES de insertar — después de crear, la
    # fila recién insertada calzaría con su propia búsqueda y el aviso se
    # dispararía siempre, incluso en la primera carga de un código nuevo.
    warnings = await _warnings_duplicado(body.idTarjeta, body.codigo)

    try:
        id_resumen = await run_in_threadpool(repository.create_resumen, cabecera, lineas)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    lineas_out = await run_in_threadpool(repository.get_lineas, id_resumen)
    return _to_detalle_response(id_resumen, cabecera, lineas_out, warnings)


@router.post("/{id_resumen}/lock", response_model=LockResponse)
async def adquirir_lock_resumen(id_resumen: int, body: LockRequest) -> LockResponse:
    try:
        lock = await run_in_threadpool(repository_locks.adquirir_lock, id_resumen, body.lockToken, body.force)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if lock is None:
        raise HTTPException(status_code=409, detail="El resumen está siendo editado.")
    return LockResponse(idResumen=lock.id_resumen, lockToken=lock.lock_token, expiresAt=lock.expires_at)


@router.delete("/{id_resumen}/lock", status_code=204)
async def liberar_lock_resumen(id_resumen: int, x_lock_token: str = Header(...)) -> None:
    liberado = await run_in_threadpool(repository_locks.liberar_lock, id_resumen, x_lock_token)
    if not liberado:
        raise HTTPException(status_code=409, detail="El bloqueo pertenece a otra sesión de edición.")


@router.put("/{id_resumen}", response_model=ResumenDetalleResponse)
async def editar_resumen(id_resumen: int, body: ResumenEditRequest, x_lock_token: str = Header(...)) -> ResumenDetalleResponse:
    if await run_in_threadpool(repository.get_resumen_detalle, id_resumen) is None:
        raise HTTPException(status_code=404, detail="Resumen no encontrado")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_resumen, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="El resumen está siendo editado por otra sesión.")

    cabecera = _cabecera_dict(body)
    lineas = [linea.model_dump() for linea in body.lineas]

    try:
        await run_in_threadpool(repository.update_resumen, id_resumen, cabecera, lineas)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    lineas_out = await run_in_threadpool(repository.get_lineas, id_resumen)
    warnings = await _warnings_duplicado(body.idTarjeta, body.codigo, id_resumen)
    return _to_detalle_response(id_resumen, cabecera, lineas_out, warnings)


@router.delete("/{id_resumen}", status_code=204)
async def eliminar_resumen(id_resumen: int, x_lock_token: str = Header(...)) -> None:
    if await run_in_threadpool(repository.get_resumen_detalle, id_resumen) is None:
        raise HTTPException(status_code=404, detail="Resumen no encontrado")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_resumen, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="El resumen está siendo editado por otra sesión.")

    await run_in_threadpool(repository.delete_resumen, id_resumen)


@router.get("/{id_resumen}", response_model=ResumenDetalleResponse)
async def get_resumen_detalle(id_resumen: int) -> ResumenDetalleResponse:
    cabecera = await run_in_threadpool(repository.get_resumen_detalle, id_resumen)
    if cabecera is None:
        raise HTTPException(status_code=404, detail="Resumen no encontrado")
    lineas_out = await run_in_threadpool(repository.get_lineas, id_resumen)
    return _to_detalle_response(id_resumen, cabecera, lineas_out, warnings=[])
