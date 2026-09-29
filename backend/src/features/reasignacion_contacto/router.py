"""Reasignación de contacto en movimientos de cuenta corriente (022) — ver
contracts/api.md. Sin restricción de rol adicional (Assumptions de spec.md):
cualquier usuario autenticado con permisos de escritura puede reasignar y
descartar candidatos, igual que el resto del sistema."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_one
from src.features.reasignacion_contacto import repository
from src.features.reasignacion_contacto.schemas import (
    CandidatosResponse,
    DescartarCandidatoRequest,
    HistorialResponse,
    Reasignacion,
    ReasignarRequest,
)

router = APIRouter(prefix="/api/reasignacion-contacto", tags=["reasignacion-contacto"])


def _usuario_actual(request: Request) -> str:
    payload = getattr(request.state, "usuario", None)
    if not payload:
        return "desconocido"
    fila = fetch_one("SELECT NombreUsuario AS n FROM dbo.AuthUsuarios WHERE IdUsuario = ?", (payload["idUsuario"],))
    return fila["n"] if fila else "desconocido"


@router.post("/reasignar", response_model=Reasignacion, status_code=201)
async def reasignar(body: ReasignarRequest, request: Request) -> Reasignacion:
    usuario = _usuario_actual(request)
    try:
        resultado = await run_in_threadpool(
            repository.reasignar, body.origen, body.idOrigen, body.idContactoNuevo, usuario, body.motivo
        )
    except ValueError as e:
        mensaje = str(e)
        if "todavía no admite reasignación" in mensaje:
            raise HTTPException(status_code=400, detail=mensaje) from e
        if "no existe" in mensaje:
            raise HTTPException(status_code=404, detail=mensaje) from e
        raise HTTPException(status_code=409, detail=mensaje) from e
    return Reasignacion(**resultado)


@router.get("/historial", response_model=HistorialResponse)
async def historial(
    origen: str | None = Query(default=None), idOrigen: int | None = Query(default=None)
) -> HistorialResponse:
    items = await run_in_threadpool(repository.listar_historial, origen, idOrigen)
    return HistorialResponse(items=items)


@router.get("/candidatos", response_model=CandidatosResponse)
async def candidatos() -> CandidatosResponse:
    resultado = await run_in_threadpool(repository.detectar_candidatos)
    return CandidatosResponse(candidatos=resultado)


@router.post("/candidatos/descartar")
async def descartar_candidato(body: DescartarCandidatoRequest, request: Request) -> dict:
    usuario = _usuario_actual(request)
    await run_in_threadpool(
        repository.descartar_candidato, body.origen, body.idOrigen, body.idContactoSugerido, usuario
    )
    return {"ok": True}
