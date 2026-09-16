"""Arrendamientos endpoints.

Todos los endpoints son GET salvo `PATCH .../cuotas/{id}/estado`, la
primera funcionalidad de escritura real de la app (2026-09-17, decisión
explícita del usuario) — corre exclusivamente contra `WC` ("Working
Copy"), nunca contra `LaHerencia` (ver `src/db/connection.py`,
`execute_write`/`_assert_target_is_wc`). No agregar otras rutas de
escritura sin el mismo mecanismo de protección.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
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


class ActualizarEstadoCuotaRequest(BaseModel):
    estado: Literal["Pendiente", "Cobrado"]


class ActualizarEstadoCuotaResponse(BaseModel):
    idCobroAlquiler: int
    estado: str


@router.patch("/cuotas/{id_cobro_alquiler}/estado", response_model=ActualizarEstadoCuotaResponse)
async def actualizar_estado_cuota(
    id_cobro_alquiler: int, body: ActualizarEstadoCuotaRequest
) -> ActualizarEstadoCuotaResponse:
    updated = await run_in_threadpool(
        repository.set_estado_cuota, id_cobro_alquiler, body.estado
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")
    return ActualizarEstadoCuotaResponse(idCobroAlquiler=id_cobro_alquiler, estado=body.estado)
