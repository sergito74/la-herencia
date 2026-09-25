"""Cuentas de socios (021) — ver contracts/api.md. Sin restricción de rol
(Clarifications, 2026-09-26): cualquier usuario autenticado puede asignar
gastos, anular y registrar devoluciones."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_one
from src.features.cuentas_socios import repository
from src.features.cuentas_socios.schemas import (
    AnularMovimientoRequest,
    AsignarGastoRequest,
    DetalleSocioResponse,
    DevolucionRequest,
    ListaCandidatasResponse,
    ListaSociosResponse,
    MovimientoCuentaSocio,
)

router = APIRouter(prefix="/api/cuentas-socios", tags=["cuentas-socios"])


def _usuario_actual(request: Request) -> str:
    """Mismo patrón que `aplicaciones_pago/router.py`: quién hizo la
    acción queda siempre registrado (FR-005)."""
    payload = getattr(request.state, "usuario", None)
    if not payload:
        return "desconocido"
    fila = fetch_one("SELECT NombreUsuario AS n FROM dbo.AuthUsuarios WHERE IdUsuario = ?", (payload["idUsuario"],))
    return fila["n"] if fila else "desconocido"


@router.get("", response_model=ListaSociosResponse)
async def listar_socios() -> ListaSociosResponse:
    socios = await run_in_threadpool(repository.listar_socios_con_saldo)
    return ListaSociosResponse(socios=socios)


@router.get("/compras-particulares-candidatas", response_model=ListaCandidatasResponse)
async def compras_particulares_candidatas(proveedor: str | None = Query(default=None)) -> ListaCandidatasResponse:
    compras = await run_in_threadpool(repository.listar_compras_particulares_candidatas, proveedor)
    return ListaCandidatasResponse(compras=compras)


@router.get("/{idSocio}/movimientos", response_model=DetalleSocioResponse)
async def detalle_socio(idSocio: int) -> DetalleSocioResponse:
    socio = fetch_one("SELECT IdSocio AS idSocio, Nombre AS nombre FROM dbo.Socios WHERE IdSocio = ?", (idSocio,))
    if socio is None:
        raise HTTPException(status_code=404, detail="Socio no encontrado")
    movimientos = await run_in_threadpool(repository.listar_movimientos, idSocio)
    saldo = await run_in_threadpool(repository.calcular_saldo, idSocio)
    return DetalleSocioResponse(idSocio=idSocio, nombre=socio["nombre"], saldo=saldo, movimientos=movimientos)


@router.post("/{idSocio}/asignar-gasto", response_model=MovimientoCuentaSocio, status_code=201)
async def asignar_gasto(idSocio: int, body: AsignarGastoRequest, request: Request) -> MovimientoCuentaSocio:
    usuario = _usuario_actual(request)
    try:
        movimiento = await run_in_threadpool(repository.asignar_gasto, idSocio, body.idCompra, usuario, body.motivo)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return MovimientoCuentaSocio(**movimiento)


@router.post("/movimientos/{idMovimiento}/anular", response_model=MovimientoCuentaSocio)
async def anular_movimiento(idMovimiento: int, body: AnularMovimientoRequest, request: Request) -> MovimientoCuentaSocio:
    usuario = _usuario_actual(request)
    try:
        movimiento = await run_in_threadpool(repository.anular_movimiento, idMovimiento, body.motivo, usuario)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return MovimientoCuentaSocio(**movimiento)


@router.post("/{idSocio}/devolucion", response_model=MovimientoCuentaSocio, status_code=201)
async def registrar_devolucion(idSocio: int, body: DevolucionRequest, request: Request) -> MovimientoCuentaSocio:
    usuario = _usuario_actual(request)
    try:
        movimiento = await run_in_threadpool(
            repository.registrar_devolucion, idSocio, body.importe, body.fecha, body.medio, body.motivo, usuario
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return MovimientoCuentaSocio(**movimiento)
