"""Impuestos endpoints. GET only — 100% read-only (FR-008).

Do not add POST/PUT/PATCH/DELETE routes to this router.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.impuestos import repository
from src.features.impuestos.schemas import (
    Impuesto,
    ImpuestosListResponse,
    Retencion,
    RetencionesListResponse,
)

router = APIRouter(prefix="/api/impuestos", tags=["impuestos"])


@router.get("", response_model=ImpuestosListResponse)
async def list_impuestos(
    organismo: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> ImpuestosListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_impuestos, organismo, fechaDesde, fechaHasta, norm_page, norm_page_size
    )
    return ImpuestosListResponse(
        items=[Impuesto(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/retenciones", response_model=RetencionesListResponse)
async def list_retenciones(
    contacto: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> RetencionesListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_retenciones, contacto, fechaDesde, fechaHasta, norm_page, norm_page_size
    )
    return RetencionesListResponse(
        items=[Retencion(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )
