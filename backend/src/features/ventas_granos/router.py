"""Ventas de Granos endpoints (007-ventas-hacienda-granos) — dominio 100%
nuevo, lectura + alta/edición/eliminación desde el arranque. Escribe
exclusivamente contra `WC` vía `execute_write_transaction`.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Header, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.ventas_granos import repository, repository_locks
from src.features.ventas_granos.schemas import (
    FiltrosVentaGranosResponse,
    LockRequest,
    LockResponse,
    VentaGranos,
    VentaGranosAltaRequest,
    VentaGranosDetalleResponse,
    VentaGranosEditRequest,
    VentaGranosListResponse,
)

router = APIRouter(prefix="/api/ventas-granos", tags=["ventas-granos"])


@router.get("", response_model=VentaGranosListResponse)
async def list_ventas_granos(
    consignatario: str | None = Query(default=None),
    numeroDocumento: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    campania: str | None = Query(default=None),
    sortBy: str | None = Query(default=None),
    sortDir: str = Query(default="asc"),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> VentaGranosListResponse:
    """FR-010: sin ningún filtro, no muestra ningún resultado (mismo
    criterio que Compras/Contactos — con volumen alto, un listado vacío
    por defecto es más claro que uno paginado sin filtrar)."""
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    items, total = await run_in_threadpool(
        repository.search_ventas,
        consignatario,
        numeroDocumento,
        fechaDesde,
        fechaHasta,
        campania,
        norm_page,
        norm_page_size,
        sortBy,
        sortDir,
    )
    return VentaGranosListResponse(
        items=[VentaGranos(**item) for item in items],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/filtros", response_model=FiltrosVentaGranosResponse)
async def get_filtros_venta_granos() -> FiltrosVentaGranosResponse:
    return FiltrosVentaGranosResponse(**await run_in_threadpool(repository.get_filtros))


def _cabecera_dict(body: VentaGranosAltaRequest) -> dict:
    return body.model_dump(exclude={"ajustes", "deducciones"})


def _to_detalle_response(id_venta: int, cabecera: dict, totales: dict, ajustes: list[dict], deducciones: list[dict], warnings: list[str]) -> VentaGranosDetalleResponse:
    cabecera_sin_id = {k: v for k, v in cabecera.items() if k != "idVenta"}
    return VentaGranosDetalleResponse(
        idVenta=id_venta,
        **cabecera_sin_id,
        ajustes=ajustes,
        deducciones=deducciones,
        precioKg=totales["precioKg"],
        subTotal=totales["subTotal"],
        iva=totales["iva"],
        importeConIVA=totales["importeConIVA"],
        totalOperacion=totales["totalOperacion"],
        totalRetenciones=totales["totalRetenciones"],
        totalDeducciones=totales["totalDeducciones"],
        importeNetoAPercibir=totales["importeNetoAPercibir"],
        warnings=warnings,
    )


async def _warnings_duplicado(id_consignatario: int, numero_documento: str, excluir_id_venta: int | None = None) -> list[str]:
    """FR-012a: advertencia no bloqueante (decisión Q3)."""
    duplicado = await run_in_threadpool(
        repository.hay_documento_duplicado, id_consignatario, numero_documento, excluir_id_venta
    )
    if duplicado:
        return ["Ya existe una venta de granos con este número de documento para este consignatario."]
    return []


@router.post("", response_model=VentaGranosDetalleResponse, status_code=201)
async def crear_venta_granos(body: VentaGranosAltaRequest) -> VentaGranosDetalleResponse:
    cabecera = _cabecera_dict(body)
    ajustes = [a.model_dump() for a in body.ajustes]
    deducciones = [d.model_dump() for d in body.deducciones]

    try:
        id_venta = await run_in_threadpool(repository.create_venta, cabecera, ajustes, deducciones)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    totales = repository.calcular_totales(cabecera, ajustes, deducciones)
    ajustes_out = await run_in_threadpool(repository.get_ajustes, id_venta)
    deducciones_out = await run_in_threadpool(repository.get_deducciones, id_venta)
    warnings = await _warnings_duplicado(body.idConsignatario, body.numeroDocumento)

    return _to_detalle_response(id_venta, cabecera, totales, ajustes_out, deducciones_out, warnings)


@router.get("/{id_venta}", response_model=VentaGranosDetalleResponse)
async def get_venta_granos_detalle(id_venta: int) -> VentaGranosDetalleResponse:
    cabecera = await run_in_threadpool(repository.get_venta_cabecera, id_venta)
    if cabecera is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    ajustes = await run_in_threadpool(repository.get_ajustes, id_venta)
    deducciones = await run_in_threadpool(repository.get_deducciones, id_venta)
    totales = repository.calcular_totales(cabecera, ajustes, deducciones)
    return _to_detalle_response(id_venta, cabecera, totales, ajustes, deducciones, [])


@router.post("/{id_venta}/lock", response_model=LockResponse)
async def adquirir_lock_venta_granos(id_venta: int, body: LockRequest) -> LockResponse:
    try:
        lock = await run_in_threadpool(
            repository_locks.adquirir_lock, id_venta, body.lockToken, body.force
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if lock is None:
        raise HTTPException(status_code=409, detail="La venta está siendo editada.")
    return LockResponse(idVenta=lock.id_venta, lockToken=lock.lock_token, expiresAt=lock.expires_at)


@router.delete("/{id_venta}/lock", status_code=204)
async def liberar_lock_venta_granos(id_venta: int, x_lock_token: str = Header(...)) -> None:
    liberado = await run_in_threadpool(repository_locks.liberar_lock, id_venta, x_lock_token)
    if not liberado:
        raise HTTPException(status_code=409, detail="El bloqueo pertenece a otra sesión de edición.")


@router.put("/{id_venta}", response_model=VentaGranosDetalleResponse)
async def editar_venta_granos(
    id_venta: int, body: VentaGranosEditRequest, x_lock_token: str = Header(...)
) -> VentaGranosDetalleResponse:
    if await run_in_threadpool(repository.get_venta_cabecera, id_venta) is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_venta, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="La venta está siendo editada por otra sesión.")

    cabecera = _cabecera_dict(body)
    ajustes = [a.model_dump() for a in body.ajustes]
    deducciones = [d.model_dump() for d in body.deducciones]

    try:
        await run_in_threadpool(repository.update_venta, id_venta, cabecera, ajustes, deducciones)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    totales = repository.calcular_totales(cabecera, ajustes, deducciones)
    ajustes_out = await run_in_threadpool(repository.get_ajustes, id_venta)
    deducciones_out = await run_in_threadpool(repository.get_deducciones, id_venta)
    warnings = await _warnings_duplicado(body.idConsignatario, body.numeroDocumento, id_venta)

    return _to_detalle_response(id_venta, cabecera, totales, ajustes_out, deducciones_out, warnings)


@router.delete("/{id_venta}", status_code=204)
async def eliminar_venta_granos(id_venta: int, x_lock_token: str = Header(...)) -> None:
    if await run_in_threadpool(repository.get_venta_cabecera, id_venta) is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_venta, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="La venta está siendo editada por otra sesión.")

    await run_in_threadpool(repository.delete_venta, id_venta)
