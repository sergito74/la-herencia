"""Cola de revisión de la migración de Cajas Giamigli (027). GET only —
100% solo lectura, mismo criterio que `cuentas_corrientes` (004)."""

from __future__ import annotations

from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from src.features.migracion_cajas_giamigli import repository
from src.features.migracion_cajas_giamigli.schemas import CasoARevisar, ListaCasosARevisarResponse

router = APIRouter(prefix="/api/migracion-cajas-giamigli", tags=["migracion-cajas-giamigli"])


@router.get("/revision", response_model=ListaCasosARevisarResponse)
async def listar_revision(resuelto: bool | None = Query(default=None)) -> ListaCasosARevisarResponse:
    items = await run_in_threadpool(repository.listar_casos_a_revisar, resuelto)
    return ListaCasosARevisarResponse(items=[CasoARevisar(**item) for item in items], total=len(items))
