"""Endpoints del Módulo Ganadero (052). Contrato: specs/052-modulo-ganadero/contracts/api-ganaderia.md."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.features.boveda.router import exigir_admin
from src.features.ganaderia import costos, periodos, resultado, superficie

router = APIRouter(prefix="/api/ganaderia", tags=["ganaderia"])


def _anio(clave: str | None, defecto: int) -> int:
    if not clave:
        return defecto
    try:
        return periodos.anio_de_etiqueta(clave)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Período inválido") from exc


def _vista(v: str) -> str:
    if v not in ("ejercicio", "campania"):
        raise HTTPException(status_code=422, detail="Vista inválida")
    return v


@router.get("/resultado")
async def get_resultado(vista: str = "ejercicio", moneda: str = "USD", desde: str | None = None,
                        hasta: str | None = None, establecimiento: int | None = None) -> dict:
    vista = _vista(vista)
    actual = periodos.anio_inicio(date.today(), vista)
    a1 = _anio(hasta, actual)
    a0 = _anio(desde, a1 - 4)
    if a0 > a1 or a1 - a0 > 15:
        raise HTTPException(status_code=422, detail="Rango de períodos inválido (máximo 16)")
    if moneda not in ("USD", "ARS"):
        raise HTTPException(status_code=422, detail="Moneda inválida")
    return await run_in_threadpool(resultado.resultado, a0, a1, vista, moneda, establecimiento)


@router.get("/resultado/detalle")
async def get_detalle(grupo: str, rubro: str, periodo: str, vista: str = "ejercicio",
                      establecimiento: int | None = None) -> dict:
    return {"items": await run_in_threadpool(resultado.detalle, grupo, rubro, _anio(periodo, 0), _vista(vista),
                                             establecimiento)}


@router.get("/superficie")
async def get_superficie(periodo: str | None = Query(None), vista: str = "ejercicio") -> dict:
    vista = _vista(vista)
    return await run_in_threadpool(superficie.superficie, _anio(periodo, periodos.anio_inicio(date.today(), vista)), vista)


@router.post("/resultado/recalcular", dependencies=[Depends(exigir_admin)])
async def recalcular() -> dict:
    """Vacía el cálculo guardado de forrajes (cuando se cargaron órdenes o compras de cultivos ganaderos)."""
    costos.invalidar()
    return {"ok": True}
