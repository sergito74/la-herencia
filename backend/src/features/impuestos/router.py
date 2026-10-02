"""Impuestos endpoints.

Listados de impuestos y retenciones (005). Desde 033-alta-impuestos
(2026-10-02) también alta, edición y baja de boletas en `dbo.Impuestos`
(reemplaza el FR-008 de 005 para boletas; retenciones siguen solo lectura).
El middleware global rechaza escrituras del rol `Lectura`.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.impuestos import repository
from src.features.impuestos.schemas import (
    CatalogoImpuestos,
    ImpuestoDetalle,
    ImpuestoInput,
    Impuesto,
    ImpuestosListResponse,
    Retencion,
    RetencionesListResponse,
)

router = APIRouter(prefix="/api/impuestos", tags=["impuestos"])


@router.get("", response_model=ImpuestosListResponse)
async def list_impuestos(
    organismo: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> ImpuestosListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_impuestos, organismo, fechaDesde, fechaHasta, norm_page, norm_page_size
    )
    return ImpuestosListResponse(
        items=[Impuesto(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/retenciones", response_model=RetencionesListResponse)
async def list_retenciones(
    contacto: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> RetencionesListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_retenciones, contacto, fechaDesde, fechaHasta, norm_page, norm_page_size
    )
    return RetencionesListResponse(
        items=[Retencion(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


# --- 033-alta-impuestos -----------------------------------------------------


@router.get("/catalogo", response_model=CatalogoImpuestos)
async def catalogo_impuestos() -> CatalogoImpuestos:
    return CatalogoImpuestos(**await run_in_threadpool(repository.get_catalogo))


async def _validar_o_400(body: ImpuestoInput, excluir_id: int | None = None) -> dict:
    datos = body.model_dump()
    errores = await run_in_threadpool(repository.validar, datos)
    if errores:
        raise HTTPException(status_code=400, detail=errores)
    dup = await run_in_threadpool(repository.buscar_duplicado, body.idOrganismo, body.numeroDocumento, excluir_id)
    if dup:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe la boleta #{dup['idImpuesto']} con el mismo número para este organismo.",
        )
    return datos


@router.get("/{id_impuesto}", response_model=ImpuestoDetalle)
async def obtener_impuesto(id_impuesto: int) -> ImpuestoDetalle:
    fila = await run_in_threadpool(repository.get_impuesto, id_impuesto)
    if fila is None:
        raise HTTPException(status_code=404, detail="Boleta no encontrada")
    return ImpuestoDetalle(**fila)


@router.post("", response_model=ImpuestoDetalle, status_code=201)
async def crear_impuesto(body: ImpuestoInput) -> ImpuestoDetalle:
    datos = await _validar_o_400(body)
    nuevo = await run_in_threadpool(repository.crear, datos)
    return ImpuestoDetalle(**await run_in_threadpool(repository.get_impuesto, nuevo))


@router.put("/{id_impuesto}", response_model=ImpuestoDetalle)
async def editar_impuesto(id_impuesto: int, body: ImpuestoInput) -> ImpuestoDetalle:
    if await run_in_threadpool(repository.get_impuesto, id_impuesto) is None:
        raise HTTPException(status_code=404, detail="Boleta no encontrada")
    datos = await _validar_o_400(body, id_impuesto)
    await run_in_threadpool(repository.actualizar, id_impuesto, datos)
    return ImpuestoDetalle(**await run_in_threadpool(repository.get_impuesto, id_impuesto))


@router.delete("/{id_impuesto}", status_code=204)
async def eliminar_impuesto(id_impuesto: int) -> Response:
    if await run_in_threadpool(repository.get_impuesto, id_impuesto) is None:
        raise HTTPException(status_code=404, detail="Boleta no encontrada")
    usos = await run_in_threadpool(repository.vinculos, id_impuesto)
    if usos:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: la boleta está vinculada a " + ", ".join(usos) + ". Quitá esos vínculos primero.",
        )
    await run_in_threadpool(repository.eliminar, id_impuesto)
    return Response(status_code=204)
