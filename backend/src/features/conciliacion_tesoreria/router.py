"""Conciliación de Tesorería (023) — ver
specs/023-conciliacion-tesoreria/contracts/conciliacion-tesoreria-api.md.
Sin restricción de rol adicional (Assumptions de spec.md): cualquier
usuario autenticado con permisos de escritura puede conciliar, igual que
el resto del sistema."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_one
from src.features.conciliacion_tesoreria import repository
from src.features.conciliacion_tesoreria.schemas import (
    Conciliacion,
    ConciliarRequest,
    EstadoConciliacion,
)
from src.features.conciliacion_tesoreria.schemas import (
    Documento,
    Candidatos,
    Calculo,
    ReferenciaDocumento,
    ConciliarLoteRequest,
    MotivoRequest,
)

router = APIRouter(prefix="/api/tesoreria", tags=["conciliacion-tesoreria"])


def _usuario_actual(request: Request) -> str:
    payload = getattr(request.state, "usuario", None)
    if not payload:
        return "desconocido"
    fila = fetch_one(
        "SELECT NombreUsuario AS n FROM dbo.AuthUsuarios WHERE IdUsuario = ?",
        (payload["idUsuario"],),
    )
    return fila["n"] if fila else "desconocido"


def _status_code_para(mensaje: str) -> int:
    mensaje_normalizado = mensaje.lower()
    if "no se concilia desde este módulo" in mensaje_normalizado:
        return 400
    if "no existe" in mensaje_normalizado:
        return 404 if "movimiento" in mensaje_normalizado else 400
    return 409


async def _documental(fn, *args):
    try:
        return await run_in_threadpool(fn, *args)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        text = str(e)
        status = 400 if "Motivo inválido" in text else _status_code_para(text)
        raise HTTPException(status_code=status, detail=text) from e


@router.get("/documentos-buscar", response_model=list[Documento])
async def buscar_documentos(q: str = Query(min_length=2, max_length=100)):
    return await _documental(repository.buscar_documentos, q)


@router.get("/{medio}/movimientos/{id_movimiento}/candidatos", response_model=Candidatos)
async def get_candidatos(medio: str, id_movimiento: int):
    return await _documental(repository.candidatos, medio, id_movimiento)


@router.get("/{medio}/movimientos/{id_movimiento}/conciliacion-preview", response_model=Calculo)
async def preview(
    medio: str, id_movimiento: int, documentos: list[str] = Query(min_length=1, max_length=20)
):
    try:
        refs = []
        for value in documentos:
            origen, id_origen = value.split(":")
            refs.append(ReferenciaDocumento(origen=origen, idOrigen=int(id_origen)))
        body = ConciliarLoteRequest(documentos=refs)
    except (ValueError, ValidationError) as e:
        raise HTTPException(
            status_code=422, detail="Referencias documentales inválidas o repetidas."
        ) from e
    return await _documental(
        repository.calcular_conciliacion,
        medio,
        id_movimiento,
        [d.model_dump() for d in body.documentos],
    )


@router.post(
    "/{medio}/movimientos/{id_movimiento}/conciliacion-lote",
    response_model=list[Conciliacion],
    status_code=201,
)
async def post_lote(medio: str, id_movimiento: int, body: ConciliarLoteRequest, request: Request):
    usuario = await run_in_threadpool(_usuario_actual, request)
    return await _documental(
        repository.vincular_lote,
        medio,
        id_movimiento,
        [d.model_dump() for d in body.documentos],
        body.aceptarDiferencia.model_dump() if body.aceptarDiferencia else None,
        usuario,
    )


@router.post("/{medio}/movimientos/{id_movimiento}/sin-documento", status_code=204)
async def sin_documento(medio: str, id_movimiento: int, body: MotivoRequest, request: Request):
    usuario = await run_in_threadpool(_usuario_actual, request)
    await _documental(
        repository.marcar_sin_documento, medio, id_movimiento, body.motivo, body.detalle, usuario
    )


@router.delete("/{medio}/movimientos/{id_movimiento}/estado", status_code=204)
async def quitar_estado(medio: str, id_movimiento: int, request: Request):
    usuario = await run_in_threadpool(_usuario_actual, request)
    await _documental(repository.quitar_estado, medio, id_movimiento, usuario)


@router.delete("/{medio}/movimientos/{id_movimiento}/conciliacion/{id_conciliacion}", status_code=204)
async def quitar_vinculo(medio: str, id_movimiento: int, id_conciliacion: int):
    await _documental(repository.quitar_vinculo, medio, id_movimiento, id_conciliacion)


@router.get("/{medio}/movimientos/{id_movimiento}/conciliacion", response_model=EstadoConciliacion)
async def get_estado_conciliacion(medio: str, id_movimiento: int) -> EstadoConciliacion:
    try:
        resultado = await run_in_threadpool(repository.calcular_estado, medio, id_movimiento)
    except ValueError as e:
        raise HTTPException(status_code=_status_code_para(str(e)), detail=str(e)) from e
    return EstadoConciliacion(**resultado)


@router.post(
    "/{medio}/movimientos/{id_movimiento}/conciliacion",
    response_model=Conciliacion,
    status_code=201,
)
async def post_conciliacion(
    medio: str, id_movimiento: int, body: ConciliarRequest, request: Request
) -> Conciliacion:
    usuario = _usuario_actual(request)
    try:
        resultado = await run_in_threadpool(
            repository.aplicar_conciliacion,
            medio,
            id_movimiento,
            body.idContacto,
            body.importe,
            usuario,
        )
    except ValueError as e:
        raise HTTPException(status_code=_status_code_para(str(e)), detail=str(e)) from e
    return Conciliacion(**resultado)


@router.get("/{medio}/movimientos/{id_movimiento}/pase-caja-candidatos")
async def pase_caja_candidatos(medio: str, id_movimiento: int) -> list[dict]:
    """Movimientos de caja (±5 días, mismo importe con signo opuesto) para conciliar una extracción o un depósito como
    pase a/desde caja (19/11/2026: 'COBRADO POR CAJA' del BNA del 09/10/2019 → caja Giamigli)."""
    from src.db.connection import fetch_all
    from src.features.tesoreria.repository import get_movimientos_por_ids

    def correr():
        m = (get_movimientos_por_ids(medio, [id_movimiento]) or [None])[0]
        if not m:
            return []
        fecha = m.get("fechaHora") or m.get("fecha")
        importe = m["importe"] if "importe" in m else float(m.get("creditos") or 0) - float(m.get("debitos") or 0)
        usados = {r["d"] for r in fetch_all("SELECT Detalle AS d FROM dbo.ConciliacionesTesoreriaEstado WHERE Motivo = 'PaseCaja'")}
        filas = fetch_all("SELECT IdMovimiento AS id, Caja AS caja, CAST(Fecha AS date) AS fecha, Importe AS importe, Concepto AS concepto "
                          "FROM dbo.MovimientosCajaEfectivo WHERE ABS(DATEDIFF(day, Fecha, ?)) <= 5 AND ROUND(Importe, 2) = ROUND(?, 2) "
                          "ORDER BY ABS(DATEDIFF(day, Fecha, ?)), IdMovimiento", (fecha, -float(importe), fecha))
        return [{**f, "detalle": f"Pase a caja {f['caja']} (movimiento de caja {f['id']})"} for f in filas
                if f"Pase a caja {f['caja']} (movimiento de caja {f['id']})" not in usados]
    return await run_in_threadpool(correr)
