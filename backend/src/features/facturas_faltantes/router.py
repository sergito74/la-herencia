"""044 — /api/facturas-faltantes (contrato: specs/044-detector-facturas-faltantes/contracts/api.md)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_one
from src.features.facturas_faltantes import repository as repo
from src.features.facturas_faltantes import service

router = APIRouter(prefix="/api/facturas-faltantes", tags=["facturas-faltantes"])
Medio = Literal["galicia", "bna", "efectivo"]


class Descarte(BaseModel):
    motivo: str = Field(min_length=1, max_length=255)


class NuevaMarca(BaseModel):
    idContacto: int
    origenPago: Medio
    idPago: int
    periodoDesde: date | None = None
    periodoHasta: date | None = None
    importeAprox: float | None = Field(default=None, gt=0)


class Perfil(BaseModel):
    cicloDias: Literal[30, 60, 90] | None = None
    sinCiclo: bool = False
    margenDias: int | None = Field(default=None, ge=0, le=120)


class Baja(BaseModel):
    dadoDeBaja: bool


def _usuario(request: Request) -> str:
    payload = getattr(request.state, "usuario", None)
    if not payload:
        raise HTTPException(401, "Se requiere sesión.")
    if payload.get("rol") == "Lectura":
        raise HTTPException(403, "Tu usuario tiene permiso de solo lectura.")
    row = fetch_one("SELECT NombreUsuario nombre FROM dbo.AuthUsuarios WHERE IdUsuario=?", (payload["idUsuario"],))
    if not row:
        raise HTTPException(401, "Usuario inexistente.")
    return row["nombre"]


@router.get("/tablero")
async def tablero():
    return await run_in_threadpool(service.tablero)


@router.get("/alarmas")
async def alarmas(tipo: Literal["pago-sin-factura", "saldo-a-favor", "retencion-sin-factura", "remito-sin-factura"] | None = None,
                  page: int = Query(1, ge=1), pageSize: int = Query(50, ge=1, le=200)):
    return await run_in_threadpool(service.alarmas, tipo, page, pageSize)


@router.post("/alarmas/{clave}/descartar", status_code=204)
async def descartar(clave: str, body: Descarte, request: Request):
    usuario = await run_in_threadpool(_usuario, request)
    try:
        await run_in_threadpool(service.descartar, clave, body.motivo.strip(), usuario)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    return Response(status_code=204)


@router.get("/marcas")
async def marcas(estado: Literal["abierta", "cerrada", "anulada"] | None = None):
    return await run_in_threadpool(service.marcas, estado)


@router.post("/marcas", status_code=201)
async def crear_marca(body: NuevaMarca, request: Request):
    usuario = await run_in_threadpool(_usuario, request)
    try:
        id_marca = await run_in_threadpool(service.crear_marca, body.model_dump(), usuario)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    return {"idMarca": id_marca}


@router.post("/marcas/{id_marca}/anular", status_code=204)
async def anular_marca(id_marca: int, body: Descarte, request: Request):
    usuario = await run_in_threadpool(_usuario, request)
    if not await run_in_threadpool(repo.anular_marca, id_marca, body.motivo.strip(), usuario):
        raise HTTPException(404, "La marca no existe o ya está cerrada.")
    service.invalidar()
    return Response(status_code=204)


@router.put("/perfil/{id_contacto}", status_code=204)
async def perfil(id_contacto: int, body: Perfil, request: Request):
    usuario = await run_in_threadpool(_usuario, request)
    await run_in_threadpool(repo.guardar_perfil, id_contacto,
                            {"CicloDias": body.cicloDias, "SinCiclo": int(body.sinCiclo), "MargenDias": body.margenDias}, usuario)
    service.invalidar()
    return Response(status_code=204)


@router.post("/perfil/{id_contacto}/baja", status_code=204)
async def baja(id_contacto: int, body: Baja, request: Request):
    usuario = await run_in_threadpool(_usuario, request)
    await run_in_threadpool(repo.guardar_perfil, id_contacto, {"DadoDeBaja": int(body.dadoDeBaja)}, usuario)
    service.invalidar()
    return Response(status_code=204)


@router.get("/resumen-mensual")
async def resumen_mensual():
    return await run_in_threadpool(service.resumen_mensual)


@router.get("/pago-sin-factura")
async def pago_sin_factura(origen: Medio, idPago: int):
    return await run_in_threadpool(service.pago_sin_factura, origen, idPago)
