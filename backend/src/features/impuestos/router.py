"""Impuestos endpoints.

Listados de impuestos y retenciones (005). Desde 033-alta-impuestos
(2026-10-02) también alta, edición y baja de boletas en `dbo.Impuestos`
(reemplaza el FR-008 de 005 para boletas; retenciones siguen solo lectura).
El middleware global rechaza escrituras del rol `Lectura`.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.impuestos import repository
from src.features.impuestos.schemas import (
    CatalogoImpuestos,
    ImpuestoDetalle,
    ImpuestoInput,
    Impuesto,
    ImpuestosListResponse,
    AnularInput,
    CargaInput,
    DevolucionInput,
    Retencion,
    RetencionesListResponse,
)

router = APIRouter(prefix="/api/impuestos", tags=["impuestos"])


@router.get("", response_model=ImpuestosListResponse)
async def list_impuestos(
    organismo: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
    particular: bool = Query(default=False),
) -> ImpuestosListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_impuestos, organismo, fechaDesde, fechaHasta, norm_page, norm_page_size, particular
    )
    resumen = await run_in_threadpool(_resumen_seguro, [r["idImpuesto"] for r in rows])
    return ImpuestosListResponse(
        items=[Impuesto(**row, **resumen.get(row["idImpuesto"], {})) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/retenciones", response_model=RetencionesListResponse)
async def list_retenciones(
    contacto: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> RetencionesListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_retenciones, contacto, fechaDesde, fechaHasta, norm_page, norm_page_size
    )
    return RetencionesListResponse(
        items=[Retencion(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


# --- 033-alta-impuestos -----------------------------------------------------


@router.get("/catalogo", response_model=CatalogoImpuestos)
async def catalogo_impuestos() -> CatalogoImpuestos:
    return CatalogoImpuestos(**await run_in_threadpool(repository.get_catalogo))


async def _validar_o_400(body: ImpuestoInput, excluir_id: int | None = None) -> dict:
    datos = body.model_dump()
    errores = await run_in_threadpool(repository.validar, datos)
    if errores:
        raise HTTPException(status_code=400, detail=errores)
    dup = await run_in_threadpool(repository.buscar_duplicado, body.idOrganismo, body.numeroDocumento, excluir_id)
    if dup:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe la boleta #{dup['idImpuesto']} con el mismo número para este organismo.",
        )
    return datos


@router.get("/{id_impuesto}", response_model=ImpuestoDetalle)
async def obtener_impuesto(id_impuesto: int) -> ImpuestoDetalle:
    fila = await run_in_threadpool(repository.get_impuesto, id_impuesto)
    if fila is None:
        raise HTTPException(status_code=404, detail="Boleta no encontrada")
    return ImpuestoDetalle(**fila)


@router.post("", response_model=ImpuestoDetalle, status_code=201)
async def crear_impuesto(body: ImpuestoInput) -> ImpuestoDetalle:
    datos = await _validar_o_400(body)
    nuevo = await run_in_threadpool(repository.crear, datos)
    return ImpuestoDetalle(**await run_in_threadpool(repository.get_impuesto, nuevo))


@router.put("/{id_impuesto}", response_model=ImpuestoDetalle)
async def editar_impuesto(id_impuesto: int, body: ImpuestoInput) -> ImpuestoDetalle:
    if await run_in_threadpool(repository.get_impuesto, id_impuesto) is None:
        raise HTTPException(status_code=404, detail="Boleta no encontrada")
    datos = await _validar_o_400(body, id_impuesto)
    try:
        await run_in_threadpool(repository.actualizar, id_impuesto, datos)
    except repository.ImpuestoConCargas as exc:
        raise HTTPException(status_code=409, detail={"codigo": "IMPUESTO_CON_CARGAS", "mensaje": str(exc)}) from exc
    return ImpuestoDetalle(**await run_in_threadpool(repository.get_impuesto, id_impuesto))


@router.delete("/{id_impuesto}", status_code=204)
async def eliminar_impuesto(id_impuesto: int) -> Response:
    if await run_in_threadpool(repository.get_impuesto, id_impuesto) is None:
        raise HTTPException(status_code=404, detail="Boleta no encontrada")
    usos = await run_in_threadpool(repository.vinculos, id_impuesto)
    if usos:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: la boleta está vinculada a " + ", ".join(usos) + ". Quitá esos vínculos primero.",
        )
    try:
        await run_in_threadpool(repository.eliminar, id_impuesto)
    except repository.ImpuestoConCargas as exc:
        raise HTTPException(status_code=409, detail={"codigo": "IMPUESTO_CON_CARGAS", "mensaje": str(exc)}) from exc
    return Response(status_code=204)


# --- 041 impuestos particulares ------------------------------------------------------------------------------------


def _resumen_seguro(ids: list[int]) -> dict:
    from src.features.impuestos import particular

    try:
        return particular.leer_resumen(ids)
    except Exception as exc:  # antes de crear las tablas 041
        if "Invalid object name" in str(exc):
            return {}
        raise


def _usuario(request: Request) -> str:
    payload = getattr(request.state, "usuario", None) or {}
    if payload.get("rol") == "Lectura":
        raise HTTPException(403, "Tu usuario tiene permiso de solo lectura.")
    from src.db.connection import fetch_one

    row = fetch_one("SELECT NombreUsuario nombre FROM dbo.AuthUsuarios WHERE IdUsuario=?", (payload.get("idUsuario"),)) if payload else None
    return row["nombre"] if row else "desconocido"


async def _particular(fn, *args):
    from src.features.impuestos.particular import ErrorParticular

    try:
        return await run_in_threadpool(fn, *args)
    except ErrorParticular as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detalle()) from exc


def _json(x):
    import json
    from decimal import Decimal

    return json.loads(json.dumps(x, default=lambda v: str(v) if isinstance(v, Decimal) else v.isoformat()))


@router.get("/partidas/{partida:path}")
async def consultar_partida(partida: str):
    from src.features.impuestos import particular

    return _json(await _particular(particular.leer_partida, partida))


@router.get("/{id_impuesto}/particular")
async def ver_particular(id_impuesto: int, partida: str | None = Query(default=None)):
    from src.features.impuestos import particular

    return _json(await _particular(particular.leer, id_impuesto, partida))


@router.post("/{id_impuesto}/particular")
async def crear_particular(id_impuesto: int, body: CargaInput, request: Request):
    from src.features.impuestos import particular

    usuario = await run_in_threadpool(_usuario, request)
    carga, creada = await _particular(particular.tx_crear_carga, id_impuesto, body.model_dump(mode="json"), usuario)
    return JSONResponse(_json(carga), status_code=201 if creada else 200)


@router.post("/particular/{id_carga}/devoluciones")
async def devolucion_particular(id_carga: int, body: DevolucionInput, request: Request):
    from src.features.impuestos import particular

    usuario = await run_in_threadpool(_usuario, request)
    datos = {k: v for k, v in body.model_dump(mode="json").items() if v is not None}
    res, creada = await _particular(particular.tx_vincular, id_carga, datos, usuario)
    return JSONResponse(_json(res), status_code=201 if creada else 200)


@router.post("/particular/{id_carga}/devoluciones/{id_vinculo}/anular")
async def anular_devolucion(id_carga: int, id_vinculo: int, body: AnularInput, request: Request):
    from src.features.impuestos import particular

    usuario = await run_in_threadpool(_usuario, request)
    return _json(await _particular(particular.tx_anular_vinculo, id_carga, id_vinculo, body.motivo, usuario))


@router.post("/particular/{id_carga}/anular")
async def anular_particular(id_carga: int, body: AnularInput, request: Request):
    from src.features.impuestos import particular

    usuario = await run_in_threadpool(_usuario, request)
    return _json(await _particular(particular.tx_anular_carga, id_carga, body.motivo, usuario))
