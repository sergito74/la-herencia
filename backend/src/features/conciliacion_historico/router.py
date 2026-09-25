"""Revisión de la conciliación histórica (020, US2) — GET de solo lectura,
ver contracts/api.md. Lee de `ConciliacionHistoricoLog` (poblado por
`scripts/conciliar_historico_cuentas_corrientes.py`), no reprocesa el
histórico en vivo."""

from __future__ import annotations

from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from src.features.conciliacion_historico import repository
from src.features.conciliacion_historico.schemas import DetalleContactoResponse, ResumenResponse

router = APIRouter(prefix="/api/conciliacion-historico", tags=["conciliacion-historico"])


@router.get("/resumen", response_model=ResumenResponse)
async def resumen_endpoint(soloConDudas: bool = Query(default=False)) -> ResumenResponse:
    filas = await run_in_threadpool(repository.resumen_por_contacto, soloConDudas)
    return ResumenResponse(contactos=filas)


@router.get("/{idContacto}/detalle", response_model=DetalleContactoResponse)
async def detalle_endpoint(idContacto: int) -> DetalleContactoResponse:
    detalle = await run_in_threadpool(repository.detalle_contacto, idContacto)
    return DetalleContactoResponse(**detalle)
