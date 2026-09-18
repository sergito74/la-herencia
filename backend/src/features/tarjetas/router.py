"""Catálogo de tarjetas (Historia 4) y cuenta corriente por tarjeta
(Historia 2) — 008-tarjetas. Ambos endpoints son de solo lectura."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.features.tarjetas import repository
from src.features.tarjetas.schemas import MovimientoPagoCandidato, MovimientosTarjetaResponse, Tarjeta

router = APIRouter(prefix="/api/tarjetas", tags=["tarjetas"])


@router.get("", response_model=list[Tarjeta])
async def list_tarjetas(soloActivas: bool = Query(default=False)) -> list[Tarjeta]:
    rows = await run_in_threadpool(repository.get_tarjetas, soloActivas)
    return [Tarjeta(**row) for row in rows]


@router.get("/{id_tarjeta}/movimientos", response_model=MovimientosTarjetaResponse)
async def get_movimientos_tarjeta(id_tarjeta: int) -> MovimientosTarjetaResponse:
    tarjeta = await run_in_threadpool(repository.get_tarjeta, id_tarjeta)
    if tarjeta is None:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    movimientos = await run_in_threadpool(repository.get_movimientos, id_tarjeta)
    return MovimientosTarjetaResponse(
        idTarjeta=id_tarjeta, tarjeta=tarjeta["nombre"], movimientos=movimientos
    )


@router.get("/{id_tarjeta}/pagos-candidatos", response_model=list[MovimientoPagoCandidato])
async def get_pagos_candidatos(id_tarjeta: int) -> list[MovimientoPagoCandidato]:
    tarjeta = await run_in_threadpool(repository.get_tarjeta, id_tarjeta)
    if tarjeta is None:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    rows = await run_in_threadpool(repository.get_pagos_candidatos, id_tarjeta)
    return [MovimientoPagoCandidato(**row) for row in rows]
