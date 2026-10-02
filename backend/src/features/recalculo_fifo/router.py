"""032 — /api/recalculo-fifo: simulación y consulta del recálculo FIFO
(ver specs/032-recalculo-fifo-cuentas/contracts/api.md)."""

from __future__ import annotations

from typing import Literal, Union

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from src.features.recalculo_fifo import ejecuciones
from src.features.vinculos.router import _usuario

router = APIRouter(prefix="/api/recalculo-fifo", tags=["recalculo-fifo"])


def _exigir_admin(request: Request) -> None:
    payload = getattr(request.state, "usuario", None) or {}
    if payload.get("rol") != "Administrador":
        raise HTTPException(status_code=403, detail="Solo un Administrador puede ejecutar o modificar el recálculo FIFO.")


class SimularRequest(BaseModel):
    alcance: Union[Literal["todos", "etapa-1"], list[int]] = "etapa-1"


class ExcepcionRequest(BaseModel):
    estado: Literal["pendiente", "resuelta"]
    nota: str | None = None


@router.post("/ejecuciones", status_code=201)
async def simular_endpoint(body: SimularRequest, request: Request) -> dict:
    _exigir_admin(request)
    try:
        return await run_in_threadpool(ejecuciones.simular, body.alcance, _usuario(request))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/ejecuciones")
async def listar_endpoint() -> list[dict]:
    return await run_in_threadpool(ejecuciones.listar)


@router.get("/ejecuciones/{id_ejecucion}")
async def obtener_endpoint(id_ejecucion: int) -> dict:
    try:
        return await run_in_threadpool(ejecuciones.obtener, id_ejecucion)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"No existe la ejecución {id_ejecucion}") from exc


@router.get("/ejecuciones/{id_ejecucion}/contactos")
async def contactos_endpoint(id_ejecucion: int, filtro: str = "todos", orden: str = "volumen",
                             pagina: int = Query(default=1, ge=1), tamanio: int = Query(default=50, ge=1, le=500)) -> dict:
    try:
        return await run_in_threadpool(ejecuciones.contactos, id_ejecucion, filtro, orden, pagina, tamanio)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/ejecuciones/{id_ejecucion}/contactos/{id_contacto}")
async def detalle_endpoint(id_ejecucion: int, id_contacto: int) -> dict:
    try:
        return await run_in_threadpool(ejecuciones.detalle, id_ejecucion, id_contacto)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"El contacto {id_contacto} no está en la ejecución {id_ejecucion}") from exc


@router.patch("/ejecuciones/{id_ejecucion}/contactos/{id_contacto}/excepcion", status_code=204)
async def excepcion_endpoint(id_ejecucion: int, id_contacto: int, body: ExcepcionRequest, request: Request) -> None:
    _exigir_admin(request)
    try:
        await run_in_threadpool(ejecuciones.marcar_excepcion, id_ejecucion, id_contacto, body.estado, body.nota)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Contacto no encontrado en la ejecución") from exc


@router.post("/ejecuciones/{id_ejecucion}/descartar", status_code=204)
async def descartar_endpoint(id_ejecucion: int, request: Request) -> None:
    _exigir_admin(request)
    try:
        await run_in_threadpool(ejecuciones.descartar, id_ejecucion)
    except KeyError as exc:
        raise HTTPException(status_code=409, detail="Solo se puede descartar una simulación vigente.") from exc


class AplicarRequest(BaseModel):
    contactos: list[int] | None = None
    confirmarEmpeoran: bool = False


@router.post("/ejecuciones/{id_ejecucion}/aplicar")
async def aplicar_endpoint(id_ejecucion: int, body: AplicarRequest, request: Request) -> dict:
    _exigir_admin(request)
    try:
        return await run_in_threadpool(ejecuciones.aplicar, id_ejecucion, body.contactos, body.confirmarEmpeoran,
                                       _usuario(request))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"No existe la ejecución {id_ejecucion}") from exc
    except ejecuciones.Conflicto as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ejecuciones.RequiereConfirmacion, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/ejecuciones/{id_ejecucion}/revertir")
async def revertir_endpoint(id_ejecucion: int, request: Request) -> dict:
    _exigir_admin(request)
    try:
        return await run_in_threadpool(ejecuciones.revertir, id_ejecucion, _usuario(request))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"No existe la ejecución {id_ejecucion}") from exc
    except ejecuciones.Conflicto as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
