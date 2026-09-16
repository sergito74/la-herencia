"""Tesoreria endpoints. GET only for consultas (FR-010).

`POST /api/tesoreria/excel/validar` never persists anything in SQL Server —
it only validates and previews an uploaded file in memory (FR-008).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.tesoreria import excel_import, matching, repository
from src.features.tesoreria.schemas import (
    MEDIOS,
    ExcelValidacionResponse,
    LineaResumenTarjeta,
    MediosResponse,
    MovimientoBNA,
    MovimientoGalicia,
    MovimientosResponse,
    PagoEfectivo,
    ReferenciaOrigen,
    ValorPropio,
    ValorRecibido,
)

router = APIRouter(prefix="/api/tesoreria", tags=["tesoreria"])

_MODEL_BY_MEDIO = {
    "bna": MovimientoBNA,
    "galicia": MovimientoGalicia,
    "efectivo": PagoEfectivo,
    "valores-propios": ValorPropio,
    "valores-recibidos": ValorRecibido,
    "tarjetas": LineaResumenTarjeta,
}


def _validate_medio(medio: str) -> None:
    if medio not in MEDIOS:
        raise HTTPException(status_code=404, detail="Medio de tesoreria desconocido")


@router.get("/medios", response_model=MediosResponse)
async def list_medios() -> MediosResponse:
    return MediosResponse(medios=list(MEDIOS))


@router.get("/{medio}/movimientos", response_model=MovimientosResponse)
async def list_movimientos(
    medio: str,
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> MovimientosResponse:
    _validate_medio(medio)
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.get_movimientos, medio, fechaDesde, fechaHasta, norm_page, norm_page_size
    )
    model = _MODEL_BY_MEDIO[medio]
    return MovimientosResponse(
        items=[model(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/{medio}/movimientos/{id_movimiento}/referencia", response_model=ReferenciaOrigen)
async def get_referencia_origen(medio: str, id_movimiento: int) -> ReferenciaOrigen:
    _validate_medio(medio)
    resultado = await run_in_threadpool(matching.buscar_referencia, medio, id_movimiento)
    return ReferenciaOrigen(**resultado)


@router.post("/excel/validar", response_model=ExcelValidacionResponse)
async def validar_excel(archivo: UploadFile) -> ExcelValidacionResponse:
    contenido = await archivo.read()
    resultado = await run_in_threadpool(
        excel_import.validar_y_previsualizar, archivo.filename or "", contenido
    )
    return ExcelValidacionResponse(**resultado)
