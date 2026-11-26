"""Endpoints del Módulo Ganadero (052). Contrato: specs/052-modulo-ganadero/contracts/api-ganaderia.md."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from src.features.boveda.router import exigir_admin, usuario_actual
from src.features.ganaderia import configuracion, controles, costos, periodos, reservas, resultado, stock, superficie

router = APIRouter(prefix="/api/ganaderia", tags=["ganaderia"])


def _anio(clave: str | None, defecto: int) -> int:
    if not clave:
        return defecto
    try:
        return periodos.anio_de_etiqueta(clave)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Período inválido") from exc


def _vista(v: str) -> str:
    if v not in ("ejercicio", "campania"):
        raise HTTPException(status_code=422, detail="Vista inválida")
    return v


@router.get("/resultado")
async def get_resultado(vista: str = "ejercicio", moneda: str = "USD", desde: str | None = None,
                        hasta: str | None = None, establecimiento: int | None = None) -> dict:
    vista = _vista(vista)
    actual = periodos.anio_inicio(date.today(), vista)
    a1 = _anio(hasta, actual)
    a0 = _anio(desde, a1 - 4)
    if a0 > a1 or a1 - a0 > 15:
        raise HTTPException(status_code=422, detail="Rango de períodos inválido (máximo 16)")
    if moneda not in ("USD", "ARS"):
        raise HTTPException(status_code=422, detail="Moneda inválida")
    return await run_in_threadpool(resultado.resultado, a0, a1, vista, moneda, establecimiento)


@router.get("/resultado/detalle")
async def get_detalle(grupo: str, rubro: str, periodo: str, vista: str = "ejercicio",
                      establecimiento: int | None = None) -> dict:
    return {"items": await run_in_threadpool(resultado.detalle, grupo, rubro, _anio(periodo, 0), _vista(vista),
                                             establecimiento)}


@router.get("/superficie")
async def get_superficie(periodo: str | None = Query(None), vista: str = "ejercicio") -> dict:
    vista = _vista(vista)
    return await run_in_threadpool(superficie.superficie, _anio(periodo, periodos.anio_inicio(date.today(), vista)), vista)


@router.post("/resultado/recalcular", dependencies=[Depends(exigir_admin)])
async def recalcular() -> dict:
    """Vacía el cálculo guardado de forrajes (cuando se cargaron órdenes o compras de cultivos ganaderos)."""
    costos.invalidar()
    return {"ok": True}


# ---------------------------------------------------------------- stock (US2)

def _dueno(v: str) -> str:
    if v not in ("propia", "terceros", "todos"):
        raise HTTPException(status_code=422, detail="Dueño inválido")
    return v


@router.get("/stock")
async def get_stock(fecha: date | None = None, establecimiento: int | None = None, dueno: str = "todos") -> dict:
    return await run_in_threadpool(stock.stock, fecha or date.today(), establecimiento, _dueno(dueno))


@router.get("/movimientos")
async def get_movimientos(desde: date | None = None, hasta: date | None = None, tipo: str | None = None,
                          categoria: int | None = None, establecimiento: int | None = None) -> dict:
    return {"items": await run_in_threadpool(stock.movimientos, desde, hasta, tipo, categoria, establecimiento)}


@router.get("/categorias")
async def get_categorias() -> dict:
    from src.db.connection import fetch_all

    return {"items": await run_in_threadpool(fetch_all, "SELECT IdCategoria id, Nombre nombre FROM dbo.GanCategoria "
                                             "WHERE Activo = 1 ORDER BY Orden")}


class MovimientoIn(BaseModel):
    fecha: date
    tipo: str
    categoria: int
    categoriaDestino: int | None = None
    cabezas: int
    kg: float | None = None
    dueno: int | None = None
    establecimiento: int
    establecimientoDestino: int | None = None
    causa: str | None = None
    motivo: str | None = None
    confirmar: bool = False


@router.post("/movimientos", status_code=201, dependencies=[Depends(exigir_admin)])
async def post_movimiento(body: MovimientoIn, request: Request) -> dict:
    d = body.model_dump()
    try:
        i = await run_in_threadpool(stock.registrar_movimiento, d, usuario_actual(request), body.confirmar)
        controles.invalidar()
    except stock.MotivoFaltante as exc:
        raise HTTPException(status_code=422, detail="El ajuste de recuento necesita un motivo") from exc
    except stock.StockNegativo as exc:
        raise HTTPException(status_code=409, detail={"mensaje": "La existencia quedaría negativa", "faltantes": exc.faltantes}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": i}


class AnularIn(BaseModel):
    motivo: str


@router.post("/movimientos/{id_movimiento}/anular", dependencies=[Depends(exigir_admin)])
async def anular(id_movimiento: int, body: AnularIn) -> dict:
    try:
        await run_in_threadpool(stock.anular_movimiento, id_movimiento, body.motivo)
        controles.invalidar()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except stock.MotivoFaltante as exc:
        raise HTTPException(status_code=422, detail="Indicá el motivo") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/recuentos")
async def get_recuentos() -> dict:
    return {"items": await run_in_threadpool(stock.recuentos)}


class RecuentoDetalleIn(BaseModel):
    categoria: int
    dueno: int | None = None
    cabezas: int
    kgPromedio: float | None = None


class RecuentoIn(BaseModel):
    fecha: date
    establecimiento: int
    origen: str = "Recuento"
    observaciones: str | None = None
    detalle: list[RecuentoDetalleIn]


@router.post("/recuentos", status_code=201, dependencies=[Depends(exigir_admin)])
async def post_recuento(body: RecuentoIn, request: Request) -> dict:
    if body.origen not in ("Recuento", "Acta", "Cierre", "Planilla"):
        raise HTTPException(status_code=422, detail="Origen inválido")
    try:
        r = await run_in_threadpool(stock.registrar_recuento, body.model_dump(), usuario_actual(request))
        controles.invalidar()
        return r
    except stock.MotivoFaltante as exc:
        raise HTTPException(status_code=422, detail="El recuento no coincide con la existencia: indicá el motivo") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/reservas")
async def get_reservas(fecha: date | None = None) -> dict:
    return await run_in_threadpool(reservas.reservas, fecha)


class ConsumoReservaIn(BaseModel):
    fecha: date
    porcentaje: float
    motivo: str | None = None


@router.post("/reservas/{id_reserva}/consumos", status_code=201, dependencies=[Depends(exigir_admin)])
async def post_consumo_reserva(id_reserva: int, body: ConsumoReservaIn, request: Request) -> dict:
    try:
        await run_in_threadpool(reservas.registrar_consumo, id_reserva, body.fecha, body.porcentaje, body.motivo,
                                usuario_actual(request))
        controles.invalidar()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/controles")
async def get_controles() -> dict:
    return await run_in_threadpool(controles.resultado)


@router.post("/controles/correr")
async def correr_controles() -> dict:
    return await run_in_threadpool(controles.correr)


class AceptarControlIn(BaseModel):
    tipo: str
    clave: str
    motivo: str


@router.post("/controles/aceptar", dependencies=[Depends(exigir_admin)])
async def aceptar_control(body: AceptarControlIn, request: Request) -> dict:
    try:
        await run_in_threadpool(controles.aceptar, body.tipo, body.clave, body.motivo, usuario_actual(request))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/controles/aceptados/{id_aceptado}/quitar", dependencies=[Depends(exigir_admin)])
async def quitar_aceptado(id_aceptado: int) -> dict:
    await run_in_threadpool(controles.quitar, id_aceptado)
    return {"ok": True}


@router.get("/configuracion")
async def get_configuracion() -> dict:
    return {"secciones": configuracion.todas()}


def _seccion(nombre: str) -> str:
    if nombre not in configuracion.SECCIONES:
        raise HTTPException(status_code=404, detail="Sección inexistente")
    return nombre


@router.get("/configuracion/{seccion}")
async def get_configuracion_seccion(seccion: str) -> dict:
    return await run_in_threadpool(configuracion.seccion, _seccion(seccion))


class ConfiguracionIn(BaseModel):
    id: int | None = None
    valores: dict


@router.put("/configuracion/{seccion}", dependencies=[Depends(exigir_admin)])
async def put_configuracion(seccion: str, body: ConfiguracionIn, request: Request) -> dict:
    try:
        await run_in_threadpool(configuracion.guardar, _seccion(seccion), body.id, body.valores, usuario_actual(request))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}


@router.delete("/configuracion/{seccion}/{id_fila}", dependencies=[Depends(exigir_admin)])
async def delete_configuracion(seccion: str, id_fila: int) -> dict:
    try:
        await run_in_threadpool(configuracion.borrar, _seccion(seccion), id_fila)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}
