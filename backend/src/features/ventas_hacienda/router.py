"""Ventas de Hacienda endpoints. GET only — 100% read-only (FR-008).

Do not add POST/PUT/PATCH/DELETE routes to this router.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.ventas_hacienda import repository
from src.features.ventas_hacienda.schemas import (
    RetencionesVentaHaciendaListResponse,
    RetencionVentaHacienda,
    VentaHacienda,
    VentasHaciendaListResponse,
)

router = APIRouter(prefix="/api/ventas-hacienda", tags=["ventas-hacienda"])


@router.get("", response_model=VentasHaciendaListResponse)
async def list_ventas_hacienda(
    consignatario: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> VentasHaciendaListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_ventas_hacienda,
        consignatario,
        fechaDesde,
        fechaHasta,
        norm_page,
        norm_page_size,
    )
    return VentasHaciendaListResponse(
        items=[VentaHacienda(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/retenciones", response_model=RetencionesVentaHaciendaListResponse)
async def list_retenciones_venta_hacienda(
    contacto: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> RetencionesVentaHaciendaListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_retenciones_venta_hacienda,
        contacto,
        fechaDesde,
        fechaHasta,
        norm_page,
        norm_page_size,
    )
    return RetencionesVentaHaciendaListResponse(
        items=[RetencionVentaHacienda(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )
