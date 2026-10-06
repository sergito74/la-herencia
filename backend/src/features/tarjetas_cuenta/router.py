"""Cuenta de tarjetas, control de integridad y cruces — 034-cuenta-corriente-tarjetas."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_one
from src.features.tarjetas_cuenta import control as ctl, control_datos, cruces, exportacion, repository
from src.features.tarjetas_cuenta.schemas import AltaCruce, ControlResponse, Cruce, CruceCreado, CuentaTarjetaResponse, ResumenTarjetasResponse

router = APIRouter(prefix="/api/tarjetas-cuenta", tags=["tarjetas-cuenta"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _cuenta(id_tarjeta: int, desde: date | None, hasta: date | None, agrupar: str) -> dict:
    if agrupar not in ("movimientos", "resumenes"):
        raise HTTPException(status_code=422, detail="agrupar debe ser 'movimientos' o 'resumenes'")
    try:
        cuenta = await run_in_threadpool(repository.cuenta_tarjeta, id_tarjeta, desde, hasta, agrupar)
    except LookupError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if cuenta is None:
        raise HTTPException(status_code=404, detail="La tarjeta no existe")
    return cuenta


@router.get("/resumen", response_model=ResumenTarjetasResponse)
async def resumen(hasta: date | None = Query(default=None)) -> dict:
    return await run_in_threadpool(repository.resumen_tarjetas, hasta)


def _validar_categoria(categoria: str | None) -> None:
    if categoria and categoria not in ctl.CATEGORIAS:
        raise HTTPException(status_code=422, detail="Categoría desconocida")


@router.get("/control", response_model=ControlResponse)
async def control(idTarjeta: int | None = None, categoria: str | None = None) -> dict:
    _validar_categoria(categoria)
    return await run_in_threadpool(control_datos.control, idTarjeta, categoria)


@router.get("/control/exportar")
async def exportar_control(idTarjeta: int | None = None, categoria: str | None = None) -> Response:
    _validar_categoria(categoria)
    datos = await run_in_threadpool(control_datos.control, idTarjeta, categoria)
    contenido = await run_in_threadpool(exportacion.control_xlsx, datos)
    return Response(content=contenido, media_type=_XLSX, headers={
        "Content-Disposition": f'attachment; filename="control-tarjetas-{date.today().isoformat()}.xlsx"'})


def _usuario_actual(request: Request) -> str:
    payload = getattr(request.state, "usuario", None)
    if not payload:
        return "desconocido"
    fila = fetch_one("SELECT NombreUsuario AS n FROM dbo.AuthUsuarios WHERE IdUsuario = ?", (payload["idUsuario"],))
    return fila["n"] if fila else "desconocido"


async def _cruce(fn, *args):
    try:
        return await run_in_threadpool(fn, *args)
    except cruces.CruceError as exc:
        raise HTTPException(status_code=exc.codigo, detail=str(exc)) from exc


@router.get("/cruces/sugerencias")
async def sugerencias_cruce(tipo: str = "devolucion-debito", idTarjeta: int | None = None) -> dict:
    return {"sugerencias": await _cruce(cruces.sugerencias, tipo, idTarjeta)}


@router.get("/cruces", response_model=list[Cruce])
async def listar_cruces(idTarjeta: int | None = None, incluirDeshechos: bool = False) -> list[dict]:
    return await run_in_threadpool(cruces.listar, idTarjeta, incluirDeshechos)


@router.post("/cruces", response_model=CruceCreado, status_code=201)
async def aprobar_cruce(body: AltaCruce, request: Request) -> dict:
    return await _cruce(cruces.aprobar, body.model_dump(), _usuario_actual(request))


@router.delete("/cruces/{id_cruce}", status_code=204)
async def deshacer_cruce(id_cruce: int, request: Request) -> Response:
    await _cruce(cruces.deshacer, id_cruce, _usuario_actual(request))
    return Response(status_code=204)


@router.get("/{id_tarjeta}", response_model=CuentaTarjetaResponse)
async def cuenta(id_tarjeta: int, desde: date | None = None, hasta: date | None = None,
                 agrupar: str = "movimientos") -> dict:
    return await _cuenta(id_tarjeta, desde, hasta, agrupar)


@router.get("/{id_tarjeta}/exportar")
async def exportar(id_tarjeta: int, desde: date | None = None, hasta: date | None = None,
                   agrupar: str = "movimientos") -> Response:
    datos = await _cuenta(id_tarjeta, desde, hasta, agrupar)
    contenido = await run_in_threadpool(exportacion.cuenta_tarjeta_xlsx, datos)
    return Response(content=contenido, media_type=_XLSX, headers={
        "Content-Disposition": f'attachment; filename="cuenta-tarjeta-{id_tarjeta}-{date.today().isoformat()}.xlsx"'})
