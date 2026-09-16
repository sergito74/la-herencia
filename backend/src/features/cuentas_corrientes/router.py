"""Cuentas corrientes endpoints. GET only — 100% read-only (FR-010).

Do not add POST/PUT/PATCH/DELETE routes to this router.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.cuentas_corrientes import origen_resolver, repository
from src.features.cuentas_corrientes.schemas import (
    Contacto,
    ContactosListResponse,
    MovimientoCuentaCorriente,
    MovimientosListResponse,
    Saldo,
)

router = APIRouter(prefix="/api/cuentas-corrientes", tags=["cuentas-corrientes"])


@router.get("/contactos", response_model=ContactosListResponse)
async def list_contactos(
    q: str | None = Query(default=None),
    tipoContacto: str | None = Query(default=None),
) -> ContactosListResponse:
    items = await run_in_threadpool(repository.search_contactos, q, tipoContacto)
    return ContactosListResponse(items=[Contacto(**item) for item in items])


@router.get("/contactos/{id_contacto}/saldo", response_model=Saldo)
async def get_saldo(id_contacto: int) -> Saldo:
    saldo = await run_in_threadpool(repository.get_saldo, id_contacto)
    if saldo is None:
        raise HTTPException(status_code=404, detail="Contacto sin saldo registrado")
    return Saldo(**saldo)


@router.get("/contactos/{id_contacto}/movimientos", response_model=MovimientosListResponse)
async def list_movimientos(
    id_contacto: int,
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> MovimientosListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.get_movimientos,
        id_contacto,
        fechaDesde,
        fechaHasta,
        norm_page,
        norm_page_size,
    )
    def _resolve_items() -> list[MovimientoCuentaCorriente]:
        return [
            MovimientoCuentaCorriente(
                fecha=row["fecha"],
                documento=row["documento"],
                numeroDocumento=row["numeroDocumento"],
                deuda=row["deuda"],
                credito=row["credito"],
                origen=origen_resolver.resolve_origen(row["origenTipo"], row["idOrigen"]),
            )
            for row in rows
        ]

    items = await run_in_threadpool(_resolve_items)
    return MovimientosListResponse(
        items=items,
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )
