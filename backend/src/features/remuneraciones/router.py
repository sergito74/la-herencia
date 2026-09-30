"""Remuneraciones endpoints. Lectura + alta (028) — ver contracts/api.md.

Las escrituras (`POST`) quedan bloqueadas automáticamente para sesiones
con rol `Lectura` por `AuthMiddleware` (src/main.py) — no requieren un
chequeo de rol propio acá.
"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.remuneraciones import repository
from src.features.remuneraciones.schemas import (
    AdjuntarReciboResponse,
    NuevaLiquidacionRequest,
    NuevaLiquidacionResponse,
    PagosRemuneracionListResponse,
    Remuneracion,
    RemuneracionesListResponse,
)

_TAMANIO_MAXIMO_RECIBO = 10 * 1024 * 1024  # 10 MB (SC-004)

router = APIRouter(prefix="/api/remuneraciones", tags=["remuneraciones"])


@router.get("", response_model=RemuneracionesListResponse)
async def list_remuneraciones(
    empleado: str | None = Query(default=None),
    periodoLiquidado: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> RemuneracionesListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_remuneraciones,
        empleado,
        periodoLiquidado,
        norm_page,
        norm_page_size,
    )
    return RemuneracionesListResponse(
        items=[Remuneracion(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.post("", response_model=NuevaLiquidacionResponse, status_code=201)
async def crear_liquidacion(body: NuevaLiquidacionRequest) -> NuevaLiquidacionResponse:
    """Alta de una liquidación nueva (contracts/api.md). `409` si ya existe
    una liquidación para el mismo empleado+período y no se confirmó el
    duplicado — FR-004, nunca bloquea, solo advierte."""
    if not await run_in_threadpool(repository.existe_contacto_empleado, body.idContacto):
        raise HTTPException(status_code=400, detail="El contacto elegido no es un Empleado válido.")

    if not body.confirmarDuplicado:
        id_existente = await run_in_threadpool(
            repository.existe_liquidacion_periodo, body.idContacto, body.periodoLiquidado
        )
        if id_existente is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe una liquidación (IdSalario {id_existente}) para este empleado "
                f"en el período '{body.periodoLiquidado}'.",
            )

    resultado = await run_in_threadpool(repository.crear_liquidacion, body)
    return NuevaLiquidacionResponse(**resultado)


@router.get("/pagos", response_model=PagosRemuneracionListResponse)
async def list_pagos_remuneracion(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> PagosRemuneracionListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_pagos_remuneracion, norm_page, norm_page_size
    )
    return PagosRemuneracionListResponse(
        items=rows,
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/{id_salario}/recibo")
async def abrir_recibo(id_salario: int) -> FileResponse:
    """Sirve el PDF del recibo de sueldo de una liquidación, si se puede
    ubicar sin ambigüedad en `repository.CARPETA_RECIBOS` (ver
    `buscar_archivo_recibo`). Lectura pura del filesystem local, no de una
    tabla nueva — mismo patrón que `/api/compras/documento-local`."""
    referencia = await run_in_threadpool(repository.get_recibo_referencia, id_salario)
    if referencia is None or referencia.get("fechaPago") is None or not referencia.get("empleado"):
        raise HTTPException(status_code=404, detail="Liquidación no encontrada o sin empleado/fecha.")
    path = await run_in_threadpool(
        repository.buscar_archivo_recibo, referencia["fechaPago"], referencia["empleado"]
    )
    if path is None:
        raise HTTPException(status_code=404, detail="No se encontró el recibo para esta liquidación.")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path=path,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )


@router.post("/{id_salario}/recibo", response_model=AdjuntarReciboResponse)
async def adjuntar_recibo(id_salario: int, archivo: UploadFile) -> AdjuntarReciboResponse:
    """Adjunta o reemplaza el PDF del recibo de una liquidación ya
    existente (US2, contracts/api.md) — `guardar_recibo` valida el
    contenido y escribe la columna `Recibo`."""
    referencia = await run_in_threadpool(repository.get_recibo_referencia, id_salario)
    if referencia is None or referencia.get("fechaPago") is None or not referencia.get("empleado"):
        raise HTTPException(status_code=404, detail="Liquidación no encontrada.")

    contenido = await archivo.read()
    if len(contenido) > _TAMANIO_MAXIMO_RECIBO:
        raise HTTPException(status_code=400, detail="El archivo supera el límite de 10 MB.")

    try:
        ruta = await run_in_threadpool(
            repository.guardar_recibo,
            id_salario,
            referencia["fechaPago"],
            referencia["empleado"],
            contenido,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return AdjuntarReciboResponse(idSalario=id_salario, recibo=ruta)
