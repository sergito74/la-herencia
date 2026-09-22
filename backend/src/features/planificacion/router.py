"""Endpoints de Planificación Agrícola. Toda escritura va contra `WC`."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from src.features.planificacion import repository
from src.features.planificacion.schemas import PlanAgricolaIn

router = APIRouter(prefix="/api/planificacion", tags=["planificacion"])


async def _ejecutar(fn, *args, **kwargs):
    try:
        return await run_in_threadpool(fn, *args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc


@router.get("")
async def listar(idCampania: int | None = None) -> list[dict]:
    return await _ejecutar(repository.listar, idCampania)


@router.post("", status_code=201)
async def crear(body: PlanAgricolaIn) -> dict:
    idx = await _ejecutar(repository.crear, body.model_dump())
    return {"idPlanAgricola": idx}


@router.delete("/{id_plan_agricola}", status_code=204)
async def eliminar(id_plan_agricola: int) -> None:
    await _ejecutar(repository.eliminar, id_plan_agricola)
