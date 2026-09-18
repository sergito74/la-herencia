"""Compras en cuotas endpoints (Historia 3, 008-tarjetas) — **solo
lectura** desde 2026-09-19 (feedback del usuario, punto 5): la estructura
real (`[Tarjetas de Credito]`/`[Cuotas Tarjetas de Credito]`) está
obsoleta, sin uso desde diciembre de 2015 — el mecanismo de financiación
en cuotas vigente (AgroNacion) es otro (líneas repetidas con
`CreditoContingente`/`InteresPagoDiferido` dentro del resumen mensual,
`tarjetas_resumenes`). Se conserva el catálogo histórico de 18 compras /
183 cuotas como referencia, sin alta/edición/eliminación."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.tarjetas_cuotas import repository
from src.features.tarjetas_cuotas.schemas import (
    CompraCuotasDetalleResponse,
    CompraCuotasListItem,
    ComprasCuotasListResponse,
    CuotaResponse,
)

router = APIRouter(prefix="/api/tarjetas-cuotas", tags=["tarjetas-cuotas"])


@router.get("", response_model=ComprasCuotasListResponse)
async def list_compras(
    idContacto: int | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> ComprasCuotasListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_compras, idContacto, fechaDesde, fechaHasta, norm_page, norm_page_size
    )
    return ComprasCuotasListResponse(
        items=[CompraCuotasListItem(**row) for row in rows], page=norm_page, pageSize=norm_page_size, total=total
    )


@router.get("/{id_pago_tarjeta}", response_model=CompraCuotasDetalleResponse)
async def get_compra_detalle(id_pago_tarjeta: int) -> CompraCuotasDetalleResponse:
    cabecera = await run_in_threadpool(repository.get_detalle, id_pago_tarjeta)
    if cabecera is None:
        raise HTTPException(status_code=404, detail="Compra en cuotas no encontrada")
    cuotas = await run_in_threadpool(repository.get_cuotas, id_pago_tarjeta)
    importe_total = sum(c["importe"] for c in cuotas)
    cabecera_sin_id = {k: v for k, v in cabecera.items() if k != "idPagoTarjeta"}
    return CompraCuotasDetalleResponse(
        idPagoTarjeta=id_pago_tarjeta,
        **cabecera_sin_id,
        importeTotal=importe_total,
        cuotas=[CuotaResponse(**c) for c in cuotas],
    )
