"""Remuneraciones endpoints. GET only — 100% read-only (FR-008).

Do not add POST/PUT/PATCH/DELETE routes to this router.
"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.remuneraciones import repository
from src.features.remuneraciones.schemas import (
    PagosRemuneracionListResponse,
    Remuneracion,
    RemuneracionesListResponse,
)

router = APIRouter(prefix="/api/remuneraciones", tags=["remuneraciones"])


@router.get("", response_model=RemuneracionesListResponse)
async def list_remuneraciones(
    empleado: str | None = Query(default=None),
    periodoLiquidado: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> RemuneracionesListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_remuneraciones,
        empleado,
        periodoLiquidado,
        norm_page,
        norm_page_size,
    )
    return RemuneracionesListResponse(
        items=[Remuneracion(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/pagos", response_model=PagosRemuneracionListResponse)
async def list_pagos_remuneracion(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> PagosRemuneracionListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_pagos_remuneracion, norm_page, norm_page_size
    )
    return PagosRemuneracionListResponse(
        items=rows,
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/{id_salario}/recibo")
async def abrir_recibo(id_salario: int) -> FileResponse:
    """Sirve el PDF del recibo de sueldo de una liquidación, si se puede
    ubicar sin ambigüedad en `repository.CARPETA_RECIBOS` (ver
    `buscar_archivo_recibo`). Lectura pura del filesystem local, no de una
    tabla nueva — mismo patrón que `/api/compras/documento-local`."""
    referencia = await run_in_threadpool(repository.get_recibo_referencia, id_salario)
    if referencia is None or referencia.get("fechaPago") is None or not referencia.get("empleado"):
        raise HTTPException(status_code=404, detail="Liquidación no encontrada o sin empleado/fecha.")
    path = await run_in_threadpool(
        repository.buscar_archivo_recibo, referencia["fechaPago"], referencia["empleado"]
    )
    if path is None:
        raise HTTPException(status_code=404, detail="No se encontró el recibo para esta liquidación.")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path=path,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )
