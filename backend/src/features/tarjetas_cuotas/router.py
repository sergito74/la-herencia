"""Compras en cuotas endpoints (Historia 3, 008-tarjetas). Todo
`POST`/`PUT`/`DELETE`/`PATCH` escribe exclusivamente contra `WC`."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Header, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.tarjetas_cuotas import repository, repository_locks
from src.features.tarjetas_cuotas.schemas import (
    CompraCuotasAltaRequest,
    CompraCuotasDetalleResponse,
    CompraCuotasEditRequest,
    CompraCuotasListItem,
    ComprasCuotasListResponse,
    CuotaResponse,
    LockRequest,
    LockResponse,
    MarcarCobradaRequest,
)

router = APIRouter(prefix="/api/tarjetas-cuotas", tags=["tarjetas-cuotas"])


@router.get("", response_model=ComprasCuotasListResponse)
async def list_compras(
    idContacto: int | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> ComprasCuotasListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_compras, idContacto, fechaDesde, fechaHasta, norm_page, norm_page_size
    )
    return ComprasCuotasListResponse(
        items=[CompraCuotasListItem(**row) for row in rows], page=norm_page, pageSize=norm_page_size, total=total
    )


def _to_detalle_response(id_pago_tarjeta: int, cabecera: dict, cuotas: list[dict]) -> CompraCuotasDetalleResponse:
    importe_total = sum(c["importe"] for c in cuotas)
    cabecera_sin_id = {k: v for k, v in cabecera.items() if k != "idPagoTarjeta"}
    return CompraCuotasDetalleResponse(
        idPagoTarjeta=id_pago_tarjeta,
        **cabecera_sin_id,
        importeTotal=importe_total,
        cuotas=[CuotaResponse(**c) for c in cuotas],
    )


@router.get("/{id_pago_tarjeta}", response_model=CompraCuotasDetalleResponse)
async def get_compra_detalle(id_pago_tarjeta: int) -> CompraCuotasDetalleResponse:
    cabecera = await run_in_threadpool(repository.get_detalle, id_pago_tarjeta)
    if cabecera is None:
        raise HTTPException(status_code=404, detail="Compra en cuotas no encontrada")
    cuotas = await run_in_threadpool(repository.get_cuotas, id_pago_tarjeta)
    return _to_detalle_response(id_pago_tarjeta, cabecera, cuotas)


@router.post("", response_model=CompraCuotasDetalleResponse, status_code=201)
async def crear_compra(body: CompraCuotasAltaRequest) -> CompraCuotasDetalleResponse:
    cabecera = body.model_dump()
    try:
        id_pago_tarjeta = await run_in_threadpool(repository.create_compra, cabecera)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    detalle = await run_in_threadpool(repository.get_detalle, id_pago_tarjeta)
    cuotas = await run_in_threadpool(repository.get_cuotas, id_pago_tarjeta)
    return _to_detalle_response(id_pago_tarjeta, detalle, cuotas)


@router.patch("/{id_pago_tarjeta}/cuotas/{id_cuota}", response_model=CuotaResponse)
async def marcar_cobrada(id_pago_tarjeta: int, id_cuota: int, body: MarcarCobradaRequest) -> CuotaResponse:
    await run_in_threadpool(repository.marcar_cobrada, id_cuota, body.cobrado)
    cuotas = await run_in_threadpool(repository.get_cuotas, id_pago_tarjeta)
    for cuota in cuotas:
        if cuota["idCuota"] == id_cuota:
            return CuotaResponse(**cuota)
    raise HTTPException(status_code=404, detail="Cuota no encontrada")


@router.post("/{id_pago_tarjeta}/lock", response_model=LockResponse)
async def adquirir_lock_compra(id_pago_tarjeta: int, body: LockRequest) -> LockResponse:
    try:
        lock = await run_in_threadpool(repository_locks.adquirir_lock, id_pago_tarjeta, body.lockToken, body.force)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if lock is None:
        raise HTTPException(status_code=409, detail="La compra en cuotas está siendo editada.")
    return LockResponse(idPagoTarjeta=lock.id_pago_tarjeta, lockToken=lock.lock_token, expiresAt=lock.expires_at)


@router.delete("/{id_pago_tarjeta}/lock", status_code=204)
async def liberar_lock_compra(id_pago_tarjeta: int, x_lock_token: str = Header(...)) -> None:
    liberado = await run_in_threadpool(repository_locks.liberar_lock, id_pago_tarjeta, x_lock_token)
    if not liberado:
        raise HTTPException(status_code=409, detail="El bloqueo pertenece a otra sesión de edición.")


@router.put("/{id_pago_tarjeta}", response_model=CompraCuotasDetalleResponse)
async def editar_compra(
    id_pago_tarjeta: int, body: CompraCuotasEditRequest, x_lock_token: str = Header(...)
) -> CompraCuotasDetalleResponse:
    if await run_in_threadpool(repository.get_detalle, id_pago_tarjeta) is None:
        raise HTTPException(status_code=404, detail="Compra en cuotas no encontrada")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_pago_tarjeta, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="La compra en cuotas está siendo editada por otra sesión.")

    cabecera = body.model_dump()
    try:
        await run_in_threadpool(repository.update_compra, id_pago_tarjeta, cabecera)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    detalle = await run_in_threadpool(repository.get_detalle, id_pago_tarjeta)
    cuotas = await run_in_threadpool(repository.get_cuotas, id_pago_tarjeta)
    return _to_detalle_response(id_pago_tarjeta, detalle, cuotas)


@router.delete("/{id_pago_tarjeta}", status_code=204)
async def eliminar_compra(id_pago_tarjeta: int, x_lock_token: str = Header(...)) -> None:
    if await run_in_threadpool(repository.get_detalle, id_pago_tarjeta) is None:
        raise HTTPException(status_code=404, detail="Compra en cuotas no encontrada")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_pago_tarjeta, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="La compra en cuotas está siendo editada por otra sesión.")

    await run_in_threadpool(repository.delete_compra, id_pago_tarjeta)
