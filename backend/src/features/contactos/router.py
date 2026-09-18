"""Contactos endpoints (master data): GET list/detail, POST create, PATCH update.

Master data used by every other module for contact selection (dropdowns).
Create/update write exclusively to `WC`, never `LaHerencia` (regla de
oro, ver `src/db/connection.py`). No hay DELETE: borrar un contacto
referenciado por Compras/Ventas/Arrendamientos/etc. rompería la
integridad de esos módulos.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.contactos import repository
from src.features.contactos.schemas import (
    Contacto,
    ContactoCreateRequest,
    ContactoUpdateRequest,
    ContactosListResponse,
)

router = APIRouter(prefix="/api/contactos", tags=["contactos"])


@router.get("", response_model=ContactosListResponse)
async def list_contactos(
    q: str | None = Query(default=None),
    tipoContacto: list[str] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> ContactosListResponse:
    """`tipoContacto` es repetible (006) — ej. un selector de proveedor de
    Compras acepta varios tipos válidos (Proveedor/Multiple/Organismo/
    Empleado/Banco), no solo uno."""
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_contactos, q, tipoContacto, norm_page, norm_page_size
    )
    return ContactosListResponse(
        items=[Contacto(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/{id_contacto}", response_model=Contacto)
async def get_contacto(id_contacto: int) -> Contacto:
    row = await run_in_threadpool(repository.get_contacto, id_contacto)
    if row is None:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return Contacto(**row)


@router.post("", response_model=Contacto, status_code=201)
async def create_contacto(body: ContactoCreateRequest) -> Contacto:
    new_id = await run_in_threadpool(
        repository.create_contacto,
        body.razonSocial,
        body.tipoContacto,
        body.cuit,
        body.esContratistaLabores,
    )
    row = await run_in_threadpool(repository.get_contacto, new_id)
    return Contacto(**row)


@router.patch("/{id_contacto}", response_model=Contacto)
async def update_contacto(id_contacto: int, body: ContactoUpdateRequest) -> Contacto:
    updated = await run_in_threadpool(
        repository.update_contacto,
        id_contacto,
        body.razonSocial,
        body.tipoContacto,
        body.cuit,
        body.esContratistaLabores,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    row = await run_in_threadpool(repository.get_contacto, id_contacto)
    return Contacto(**row)
