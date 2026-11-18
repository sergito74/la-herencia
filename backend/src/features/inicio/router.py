"""Inicio "Para hacer hoy" (spec 051): solo lectura."""
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from src.features.inicio import service

router = APIRouter(prefix="/api/inicio", tags=["inicio"])


@router.get("")
async def resumen(actualizar: bool = False) -> dict:
    return await run_in_threadpool(service.resumen, actualizar)
