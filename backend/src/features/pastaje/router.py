"""039: API de contratos de pastaje (contracts/api.md). Escrituras: 403 para rol Lectura."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_one
from src.features.pastaje import inmag, service
from src.features.pastaje.lector_factura import NoReconocido
from src.features.pastaje.schemas import (
    AnularBody, ComprobanteBody, ContratoBody, ContratoUpdate, FinalizarBody, IndiceManual, LeerComprobante,
    LiquidacionBody, MovimientoBody, PeriodoBody, VersionBody,
)

router = APIRouter(prefix="/api/pastaje", tags=["pastaje"])


def _usuario(request: Request) -> str:
    payload = getattr(request.state, "usuario", None)
    if not payload:
        raise HTTPException(401, "Se requiere sesión.")
    if payload.get("rol") == "Lectura":
        raise HTTPException(403, "Tu usuario tiene permiso de solo lectura.")
    row = fetch_one("SELECT NombreUsuario nombre FROM dbo.AuthUsuarios WHERE IdUsuario=?", (payload["idUsuario"],))
    if not row:
        raise HTTPException(401, "Sesión inválida.")
    return row["nombre"]


def _json(x):
    return json.loads(json.dumps(x, default=lambda v: str(v) if isinstance(v, Decimal) else v.isoformat()))


async def _ejecutar(fn, *args):
    try:
        return _json(await run_in_threadpool(fn, *args))
    except service.NoExiste as exc:
        raise HTTPException(404, str(exc)) from exc
    except service.Conflicto as exc:
        raise HTTPException(409, str(exc)) from exc
    except service.SinIndice as exc:
        raise HTTPException(409, str(exc)) from exc
    except NoReconocido as exc:
        raise HTTPException(422, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


async def _escribir(request: Request, fn, *args):
    usuario = await run_in_threadpool(_usuario, request)
    return await _ejecutar(fn, *args, usuario)


def _periodo(valor: str) -> date:
    try:
        return date.fromisoformat(valor + "-01" if len(valor) == 7 else valor)
    except ValueError as exc:
        raise HTTPException(422, "Período inválido (AAAA-MM).") from exc


# --- Índice INMAG --------------------------------------------------------------

@router.get("/indice-inmag")
async def indice(desde: date, hasta: date):
    return await _ejecutar(inmag.listar, desde, hasta)


@router.post("/indice-inmag/actualizar")
async def indice_actualizar(request: Request, body: PeriodoBody | None = None):
    await run_in_threadpool(_usuario, request)
    b = body or PeriodoBody()
    return await _ejecutar(inmag.actualizar, b.desde, b.hasta)


@router.put("/indice-inmag/{fecha}")
async def indice_manual(fecha: date, body: IndiceManual, request: Request):
    return await _escribir(request, inmag.corregir, fecha, body.indice, body.nota)


# --- Contratos -----------------------------------------------------------------

@router.get("/contratos")
async def contratos(estado: str | None = Query(default=None)):
    return await _ejecutar(service.tarjetas, estado)


@router.post("/contratos")
async def crear_contrato(body: ContratoBody, request: Request):
    return await _escribir(request, service.crear_contrato, body.model_dump())


@router.get("/contratos/{id_contrato}")
async def ficha(id_contrato: int):
    return await _ejecutar(service.ficha, id_contrato)


@router.put("/contratos/{id_contrato}")
async def actualizar_contrato(id_contrato: int, body: ContratoUpdate, request: Request):
    return await _escribir(request, service.actualizar_contrato, id_contrato, body.model_dump())


@router.post("/contratos/{id_contrato}/finalizar")
async def finalizar(id_contrato: int, body: FinalizarBody, request: Request):
    return await _escribir(request, service.finalizar, id_contrato, body.fechaFin, body.motivo, body.version)


@router.post("/contratos/{id_contrato}/anular")
async def anular(id_contrato: int, body: AnularBody, request: Request):
    return await _escribir(request, service.anular, id_contrato, body.motivo, body.version)


# --- Bitácora --------------------------------------------------------------------

@router.get("/contratos/{id_contrato}/bitacora")
async def bitacora(id_contrato: int):
    return await _ejecutar(service.bitacora, id_contrato)


@router.post("/contratos/{id_contrato}/bitacora")
async def registrar_movimiento(id_contrato: int, body: MovimientoBody, request: Request):
    return await _escribir(request, service.registrar_movimiento, id_contrato, body.model_dump())


@router.post("/bitacora/{id_mov}/anular")
async def anular_movimiento(id_mov: int, body: AnularBody, request: Request):
    return await _escribir(request, service.anular_movimiento, id_mov, body.motivo, body.version)


# --- Liquidaciones ---------------------------------------------------------------

@router.get("/contratos/{id_contrato}/liquidaciones/preview")
async def preview(id_contrato: int, periodo: str):
    return await _ejecutar(service.preview, id_contrato, _periodo(periodo))


@router.get("/contratos/{id_contrato}/liquidaciones")
async def liquidaciones(id_contrato: int):
    from src.features.pastaje import repository

    return await _ejecutar(repository.liquidaciones, id_contrato)


@router.post("/contratos/{id_contrato}/liquidaciones")
async def crear_liquidacion(id_contrato: int, body: LiquidacionBody, request: Request):
    return await _escribir(request, service.crear_borrador, id_contrato, _periodo(body.periodo))


@router.post("/liquidaciones/generar-mes")
async def generar_mes(body: LiquidacionBody, request: Request):
    return await _escribir(request, service.generar_mes, _periodo(body.periodo))


@router.get("/liquidaciones/{id_liq}")
async def liquidacion(id_liq: int):
    from src.features.pastaje import repository

    return await _ejecutar(repository.liquidacion, id_liq)


@router.post("/liquidaciones/{id_liq}/confirmar")
async def confirmar(id_liq: int, body: VersionBody, request: Request):
    return await _escribir(request, service.confirmar, id_liq, body.version)


@router.post("/liquidaciones/{id_liq}/anular")
async def anular_liquidacion(id_liq: int, body: VersionBody, request: Request):
    return await _escribir(request, service.anular_liquidacion, id_liq, body.version)


@router.post("/liquidaciones/{id_liq}/ajuste")
async def ajuste(id_liq: int, request: Request):
    return await _escribir(request, service.crear_ajuste, id_liq)


@router.get("/liquidaciones/{id_liq}/texto-factura")
async def texto_factura(id_liq: int):
    from src.features.pastaje import repository

    def armar():
        liq = repository.liquidacion(id_liq)
        return {"detalle": service.texto_sugerido(liq), "neto": liq["neto"], "iva": liq["iva"], "total": liq["total"]}
    return await _ejecutar(armar)


def _archivo(ruta: str | None) -> FileResponse:
    if not ruta or not Path(ruta).is_file():
        raise HTTPException(404, "El PDF no está disponible.")
    return FileResponse(ruta, media_type="application/pdf", filename=Path(ruta).name)


@router.get("/liquidaciones/{id_liq}/pdf")
async def liquidacion_pdf(id_liq: int):
    from src.features.pastaje import repository

    liq = await _ejecutar(repository.liquidacion, id_liq)
    return _archivo(liq["archivoPdf"])


# --- Comprobantes ----------------------------------------------------------------

@router.post("/comprobantes/leer")
async def leer(body: LeerComprobante, request: Request):
    await run_in_threadpool(_usuario, request)
    ruta = Path(body.ruta.strip().strip('"'))
    if ruta.suffix.lower() != ".pdf" or not ruta.is_file():
        raise HTTPException(422, "Elegí un PDF existente del comprobante.")
    datos = await _ejecutar(service.leer_comprobante, ruta.read_bytes())
    return {**datos, "archivoPdf": str(ruta)}


@router.post("/comprobantes/previsualizar")
async def previsualizar_comprobante(body: ComprobanteBody):
    return await _ejecutar(service.previsualizar_comprobante, body.model_dump())


@router.post("/comprobantes")
async def registrar_comprobante(body: ComprobanteBody, request: Request):
    return await _escribir(request, service.registrar_comprobante, body.model_dump())


@router.get("/contratos/{id_contrato}/comprobantes")
async def comprobantes(id_contrato: int):
    return await _ejecutar(service.comprobantes, id_contrato)


@router.post("/comprobantes/{id_comp}/anular")
async def anular_comprobante(id_comp: int, body: AnularBody, request: Request):
    return await _escribir(request, service.anular_comprobante, id_comp, body.motivo, body.version)


@router.get("/comprobantes/{id_comp}/pdf")
async def comprobante_pdf(id_comp: int):
    from src.features.pastaje import repository

    c = await _ejecutar(repository.comprobante, id_comp)
    return _archivo(c["archivoPdf"])


@router.get("/ingresos")
async def ingresos(campania: str):
    return await _ejecutar(service.ingresos_por_campania, campania)


@router.get("/categorias")
async def categorias():
    from src.features.pastaje import repository

    return await _ejecutar(lambda: [{"id": k, "nombre": v} for k, v in sorted(repository.categorias().items())])
