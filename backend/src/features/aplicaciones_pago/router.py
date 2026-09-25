"""Aplicación de pagos/cobros: GET de solo lectura + POST para confirmar/
anular (019) — ver contracts/api-aplicaciones-pago.md."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_one
from src.features.aplicaciones_pago import documentos, repository, sugerencia
from src.features.aplicaciones_pago.schemas import (
    AnularAplicacionRequest,
    ConfirmarAplicacionRequest,
    DocumentoPendiente,
    EstadoDocumentoResponse,
    EstadoMovimientoResponse,
    SugerenciaAplicacionResponse,
    SugerirRequest,
)

router = APIRouter(prefix="/api/aplicaciones-pago", tags=["aplicaciones-pago"])


def _usuario_actual(request: Request) -> str:
    """`NombreUsuario` de la sesión actual (mismo patrón que
    `imputacion/router.py`) — quién confirmó/anuló queda siempre
    registrado (FR-005/FR-011)."""
    payload = getattr(request.state, "usuario", None)
    if not payload:
        return "desconocido"
    fila = fetch_one("SELECT NombreUsuario AS n FROM dbo.AuthUsuarios WHERE IdUsuario = ?", (payload["idUsuario"],))
    return fila["n"] if fila else "desconocido"


@router.get("/documentos-pendientes", response_model=list[DocumentoPendiente])
async def documentos_pendientes_endpoint(
    idContacto: int = Query(...),
    tipo: str | None = Query(default=None, pattern="^(compra|venta)$"),
) -> list[DocumentoPendiente]:
    filas = await run_in_threadpool(documentos.documentos_pendientes, idContacto, tipo)
    return [DocumentoPendiente(**f) for f in filas]


@router.post("/sugerir", response_model=SugerenciaAplicacionResponse)
async def sugerir_endpoint(body: SugerirRequest) -> SugerenciaAplicacionResponse:
    resultado = await run_in_threadpool(sugerencia.sugerir, body.origenMovimiento, body.idMovimientoOrigen)
    return SugerenciaAplicacionResponse(**resultado)


@router.post("")
async def confirmar_aplicacion(body: ConfirmarAplicacionRequest, request: Request) -> dict:
    aplicaciones = [a.model_dump() for a in body.aplicaciones]
    usuario = _usuario_actual(request)
    try:
        ids = await run_in_threadpool(
            repository.insertar_aplicaciones, body.origenMovimiento, body.idMovimientoOrigen, aplicaciones, usuario
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"idsAplicacion": ids}


@router.post("/{id_aplicacion}/anular")
async def anular_aplicacion_endpoint(id_aplicacion: int, body: AnularAplicacionRequest, request: Request) -> dict:
    usuario = _usuario_actual(request)
    try:
        await run_in_threadpool(repository.anular_aplicacion, id_aplicacion, body.motivo, usuario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/documento/{tipo_documento}/{id_documento}", response_model=EstadoDocumentoResponse)
async def estado_documento_endpoint(tipo_documento: str, id_documento: int) -> EstadoDocumentoResponse:
    resultado = await run_in_threadpool(repository.estado_documento, tipo_documento, id_documento)
    return EstadoDocumentoResponse(**resultado)


@router.get("/movimiento/{origen_movimiento}/{id_movimiento_origen}", response_model=EstadoMovimientoResponse)
async def estado_movimiento_endpoint(origen_movimiento: str, id_movimiento_origen: int) -> EstadoMovimientoResponse:
    resultado = await run_in_threadpool(repository.estado_movimiento, origen_movimiento, id_movimiento_origen)
    return EstadoMovimientoResponse(**resultado)
