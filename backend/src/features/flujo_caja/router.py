"""Flujo de caja real: GET only (FR-006) — ver contracts/api-flujo-caja.md."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, Response
from starlette.concurrency import run_in_threadpool

from src.features.flujo_caja import repository
from src.features.flujo_caja.repository import FECHA_PRIMER_SALDO_CONOCIDO
from src.features.flujo_caja.schemas import (
    DetalleCeldaRubroResponse,
    DetalleFlujoCajaResponse,
    FlujoCajaPorRubroResponse,
    ResumenFlujoCajaResponse,
)

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


_GRANULARIDAD_RUBRO = "^(semanal|mensual|trimestral|anual)$"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _rango(fechaDesde: date | None, fechaHasta: date | None) -> tuple[date, date]:
    desde_default, hasta_default = _rango_por_defecto()
    desde, hasta = fechaDesde or desde_default, fechaHasta or hasta_default
    _validar_fecha_desde(desde)
    if hasta < desde:
        raise HTTPException(status_code=422, detail="fechaHasta es anterior a fechaDesde.")
    return desde, hasta


@router.get("/por-rubro", response_model=FlujoCajaPorRubroResponse)
async def por_rubro(
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    granularidad: str = Query(default="mensual", pattern=_GRANULARIDAD_RUBRO),
    moneda: str = Query(default="ARS", pattern="^(ARS|USD)$"),
) -> FlujoCajaPorRubroResponse:
    """Flujo de caja real por rubro (030): movimientos bancarios reales
    repartidos por lo aplicado a cada documento, internos en sección propia,
    saldos por cuenta, en ARS o USD por cotización del día. Se recalcula
    siempre, sin cachear (pedido explícito de Sergio)."""
    desde, hasta = _rango(fechaDesde, fechaHasta)
    resultado = await run_in_threadpool(repository.flujo_por_rubro, desde, hasta, granularidad, moneda)
    resultado.pop("_partes")
    return FlujoCajaPorRubroResponse(**resultado)


@router.get("/por-rubro/detalle", response_model=DetalleCeldaRubroResponse)
async def por_rubro_detalle(
    periodo: str = Query(...),
    seccion: str = Query(..., pattern="^(ingresos|egresos|internos)$"),
    rubro: str = Query(...),
    centroCosto: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    granularidad: str = Query(default="mensual", pattern=_GRANULARIDAD_RUBRO),
    moneda: str = Query(default="ARS", pattern="^(ARS|USD)$"),
) -> DetalleCeldaRubroResponse:
    desde, hasta = _rango(fechaDesde, fechaHasta)
    try:
        resultado = await run_in_threadpool(
            repository.detalle_celda, desde, hasta, granularidad, moneda, periodo, seccion, rubro, centroCosto
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DetalleCeldaRubroResponse(**resultado)


@router.get("/por-rubro/exportar")
async def por_rubro_exportar(
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    granularidad: str = Query(default="mensual", pattern=_GRANULARIDAD_RUBRO),
    moneda: str = Query(default="ARS", pattern="^(ARS|USD)$"),
) -> Response:
    from src.features.flujo_caja import exportacion

    desde, hasta = _rango(fechaDesde, fechaHasta)
    contenido = await run_in_threadpool(exportacion.flujo_por_rubro_xlsx, desde, hasta, granularidad, moneda)
    nombre = f"flujo-caja-por-rubro-{desde.isoformat()}-{hasta.isoformat()}-{moneda}.xlsx"
    return Response(content=contenido, media_type=_XLSX, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})
