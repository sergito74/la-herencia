"""Cajas de efectivo (027) — Giamigli SA y caja chica del campo. GET only
— 100% solo lectura (FR-011), mismo criterio que `cuentas_corrientes` (004)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.cajas_efectivo import repository
from src.features.cajas_efectivo.schemas import MovimientoCajaEfectivo, MovimientosCajaResponse, SaldoCaja

router = APIRouter(prefix="/api/cajas-efectivo", tags=["cajas-efectivo"])

# Mapeo slug de URL -> valor guardado en MovimientosCajaEfectivo.Caja
# (contracts/api.md).
_SLUG_A_CAJA = {"giamigli-sa": "GiamigliSA", "campo-chica": "CampoChica"}


def _resolver_caja(slug: str) -> str:
    caja = _SLUG_A_CAJA.get(slug)
    if caja is None:
        raise HTTPException(status_code=404, detail=f"Caja desconocida: {slug!r}")
    return caja


@router.get("/{caja}/saldo", response_model=SaldoCaja)
async def saldo_caja(caja: str) -> SaldoCaja:
    caja_real = _resolver_caja(caja)
    saldo = await run_in_threadpool(repository.calcular_saldo, caja_real)
    return SaldoCaja(caja=caja, saldo=saldo)


@router.get("/{caja}/movimientos", response_model=MovimientosCajaResponse)
async def movimientos_caja(
    caja: str,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> MovimientosCajaResponse:
    caja_real = _resolver_caja(caja)
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    items, total = await run_in_threadpool(repository.listar_movimientos, caja_real, norm_page, norm_page_size)
    return MovimientosCajaResponse(
        items=[MovimientoCajaEfectivo(**item) for item in items],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )
