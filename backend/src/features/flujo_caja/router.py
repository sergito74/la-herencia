"""Flujo de caja real: GET only (FR-006) — ver contracts/api-flujo-caja.md."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.features.flujo_caja import repository
from src.features.flujo_caja.repository import FECHA_PRIMER_SALDO_CONOCIDO
from src.features.flujo_caja.schemas import DetalleFlujoCajaResponse, ResumenFlujoCajaResponse

router = APIRouter(prefix="/api/flujo-caja", tags=["flujo-caja"])


def _rango_por_defecto() -> tuple[date, date]:
    hoy = date.today()
    return hoy - timedelta(days=730), hoy


def _validar_fecha_desde(fecha_desde: date) -> None:
    if fecha_desde < FECHA_PRIMER_SALDO_CONOCIDO:
        raise HTTPException(
            status_code=400,
            detail=f"No hay saldo de apertura conocido antes de {FECHA_PRIMER_SALDO_CONOCIDO.isoformat()}",
        )


@router.get("/resumen", response_model=ResumenFlujoCajaResponse)
async def resumen(
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    granularidad: str = Query(default="mensual", pattern="^(mensual|semanal)$"),
) -> ResumenFlujoCajaResponse:
    desde_default, hasta_default = _rango_por_defecto()
    desde = fechaDesde or desde_default
    hasta = fechaHasta or hasta_default
    _validar_fecha_desde(desde)

    movimientos = await run_in_threadpool(repository.get_movimientos_normalizados, desde, hasta)
    periodos = await run_in_threadpool(repository.agregar_por_periodo, movimientos, granularidad)
    ultima_carga = await run_in_threadpool(repository.ultima_fecha_por_cuenta)

    return ResumenFlujoCajaResponse(periodos=periodos, ultimaCarga=ultima_carga)


@router.get("/detalle", response_model=DetalleFlujoCajaResponse)
async def detalle(
    fechaDesde: date = Query(...),
    fechaHasta: date = Query(...),
    banco: str | None = Query(default=None),
    numeroCuenta: str | None = Query(default=None),
    soloInternos: bool = Query(default=False),
) -> DetalleFlujoCajaResponse:
    _validar_fecha_desde(fechaDesde)
    movimientos = await run_in_threadpool(repository.get_movimientos_normalizados, fechaDesde, fechaHasta)

    if banco:
        movimientos = [m for m in movimientos if m["banco"] == banco]
    if numeroCuenta:
        movimientos = [m for m in movimientos if m["numeroCuentaBancaria"] == numeroCuenta]
    if soloInternos:
        movimientos = [m for m in movimientos if m["esInterno"]]

    return DetalleFlujoCajaResponse(movimientos=movimientos)
