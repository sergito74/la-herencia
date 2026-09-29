"""Traspasos internos de Tesorería (024) — ver
specs/024-traspasos-internos-tesoreria/contracts/traspasos-internos-api.md."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_one
from src.features.traspasos_internos_tesoreria import repository
from src.features.traspasos_internos_tesoreria.schemas import EstadoTraspasoInterno, VincularRequest

router = APIRouter(prefix="/api/tesoreria", tags=["traspasos-internos-tesoreria"])


def _usuario_actual(request: Request) -> str:
    payload = getattr(request.state, "usuario", None)
    if not payload:
        return "desconocido"
    fila = fetch_one("SELECT NombreUsuario AS n FROM dbo.AuthUsuarios WHERE IdUsuario = ?", (payload["idUsuario"],))
    return fila["n"] if fila else "desconocido"


def _status_code_para(mensaje: str) -> int:
    mensaje_normalizado = mensaje.lower()
    if "no admite traspasos internos" in mensaje_normalizado or "no se puede vincular un movimiento consigo mismo" in mensaje_normalizado:
        return 400
    if "no existe" in mensaje_normalizado or "no tiene ningún vínculo" in mensaje_normalizado:
        return 404
    return 409


@router.get("/{medio}/movimientos/{id_movimiento}/traspaso-interno", response_model=EstadoTraspasoInterno)
async def get_estado_traspaso_interno(medio: str, id_movimiento: int) -> EstadoTraspasoInterno:
    try:
        resultado = await run_in_threadpool(repository.estado_vinculo, medio, id_movimiento)
    except ValueError as e:
        raise HTTPException(status_code=_status_code_para(str(e)), detail=str(e)) from e
    return EstadoTraspasoInterno(**resultado)


@router.post("/{medio}/movimientos/{id_movimiento}/traspaso-interno", response_model=EstadoTraspasoInterno, status_code=201)
async def post_traspaso_interno(medio: str, id_movimiento: int, body: VincularRequest, request: Request) -> EstadoTraspasoInterno:
    usuario = _usuario_actual(request)
    try:
        resultado = await run_in_threadpool(repository.vincular, medio, id_movimiento, body.medioB, body.idMovimientoB, usuario)
    except ValueError as e:
        raise HTTPException(status_code=_status_code_para(str(e)), detail=str(e)) from e
    return EstadoTraspasoInterno(**resultado)


@router.delete("/{medio}/movimientos/{id_movimiento}/traspaso-interno", response_model=EstadoTraspasoInterno)
async def delete_traspaso_interno(medio: str, id_movimiento: int, request: Request) -> EstadoTraspasoInterno:
    usuario = _usuario_actual(request)
    try:
        resultado = await run_in_threadpool(repository.deshacer, medio, id_movimiento, usuario)
    except ValueError as e:
        raise HTTPException(status_code=_status_code_para(str(e)), detail=str(e)) from e
    return EstadoTraspasoInterno(**resultado)
