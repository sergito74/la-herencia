"""Arrendamientos endpoints. GET only — 100% read-only (FR-008).

Do not add POST/PUT/PATCH/DELETE routes to this router.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.arrendamientos import repository
from src.features.arrendamientos.schemas import Arrendamiento, ArrendamientosListResponse

router = APIRouter(prefix="/api/arrendamientos", tags=["arrendamientos"])


@router.get("", response_model=ArrendamientosListResponse)
async def list_arrendamientos(
    contacto: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> ArrendamientosListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_arrendamientos, contacto, norm_page, norm_page_size
    )
    return ArrendamientosListResponse(
        items=[Arrendamiento(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )
