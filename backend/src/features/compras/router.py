"""Compras endpoints. GET only — this module is 100% read-only (FR-010).

Do not add POST/PUT/PATCH/DELETE routes to this router.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.compras import repository
from src.features.compras.schemas import (
    Compra,
    CompraDetalle,
    ComprasListResponse,
    FiltrosComprasResponse,
    TrazabilidadCompra,
)

router = APIRouter(prefix="/api/compras", tags=["compras"])


@router.get("", response_model=ComprasListResponse)
async def list_compras(
    proveedor: str | None = Query(default=None),
    numeroDocumento: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    idCentroCosto: int | None = Query(default=None),
    idRubro: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> ComprasListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    items, total = await run_in_threadpool(
        repository.search_compras,
        proveedor,
        numeroDocumento,
        fechaDesde,
        fechaHasta,
        idCentroCosto,
        idRubro,
        norm_page,
        norm_page_size,
    )
    return ComprasListResponse(
        items=[Compra(**item) for item in items],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/filtros", response_model=FiltrosComprasResponse)
async def get_filtros_compras() -> FiltrosComprasResponse:
    return FiltrosComprasResponse(**await run_in_threadpool(repository.get_filtros))


@router.get("/{id_compra}", response_model=CompraDetalle)
async def get_compra_detalle(id_compra: int) -> CompraDetalle:
    cabecera = await run_in_threadpool(repository.get_compra_cabecera, id_compra)
    if cabecera is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    lineas = await run_in_threadpool(repository.get_lineas_compra, id_compra)
    return CompraDetalle(**cabecera, lineas=lineas)


@router.get("/{id_compra}/trazabilidad", response_model=TrazabilidadCompra)
async def get_compra_trazabilidad(id_compra: int) -> TrazabilidadCompra:
    movimientos = await run_in_threadpool(repository.get_trazabilidad_compra, id_compra)
    return TrazabilidadCompra(idCompra=id_compra, movimientos=movimientos)
