"""Ventas de Hacienda endpoints.

La mayoría son GET (solo lectura, spec 005). Desde
007-ventas-hacienda-granos se agregan POST/PUT/DELETE de alta/edición/
eliminación y los endpoints de bloqueo — todos escriben exclusivamente
contra `WC` vía `execute_write_transaction` (ver `src/db/connection.py`),
nunca contra `LaHerencia`.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Header, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.ventas_hacienda import repository, repository_locks
from src.features.ventas_hacienda.schemas import (
    DocumentoRelacionado,
    DocumentoRelacionadoRequest,
    FiltrosVentaHaciendaResponse,
    LockRequest,
    LockResponse,
    RetencionesVentaHaciendaListResponse,
    RetencionVentaHacienda,
    VentaHacienda,
    VentaHaciendaAltaRequest,
    VentaHaciendaDetalleResponse,
    VentaHaciendaEditRequest,
    VentasHaciendaListResponse,
)

router = APIRouter(prefix="/api/ventas-hacienda", tags=["ventas-hacienda"])


@router.get("", response_model=VentasHaciendaListResponse)
async def list_ventas_hacienda(
    consignatario: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> VentasHaciendaListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_ventas_hacienda,
        consignatario,
        fechaDesde,
        fechaHasta,
        norm_page,
        norm_page_size,
    )
    return VentasHaciendaListResponse(
        items=[VentaHacienda(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/filtros", response_model=FiltrosVentaHaciendaResponse)
async def get_filtros_venta_hacienda() -> FiltrosVentaHaciendaResponse:
    return FiltrosVentaHaciendaResponse(**await run_in_threadpool(repository.get_filtros))


@router.get("/retenciones", response_model=RetencionesVentaHaciendaListResponse)
async def list_retenciones_venta_hacienda(
    contacto: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> RetencionesVentaHaciendaListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_retenciones_venta_hacienda,
        contacto,
        fechaDesde,
        fechaHasta,
        norm_page,
        norm_page_size,
    )
    return RetencionesVentaHaciendaListResponse(
        items=[RetencionVentaHacienda(**row) for row in rows],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


def _cabecera_dict(body: VentaHaciendaAltaRequest) -> dict:
    return body.model_dump(exclude={"lineas", "vencimientos"})


def _to_detalle_response(
    id_venta: int, cabecera: dict, totales: dict, vencimientos_out: list[dict], warnings: list[str]
) -> VentaHaciendaDetalleResponse:
    cabecera_sin_id = {k: v for k, v in cabecera.items() if k != "idVenta"}
    return VentaHaciendaDetalleResponse(
        idVenta=id_venta,
        **cabecera_sin_id,
        subTotal=totales["subTotal"],
        subtotalB=totales["subtotalB"],
        comision=totales["comision"],
        iva=totales["iva"],
        importe=totales["importe"],
        importeTotal=totales["importeTotal"],
        lineas=totales["lineas"],
        vencimientos=vencimientos_out,
        warnings=warnings,
    )


async def _warnings_duplicado(id_consignatario: int, numero_documento: str, excluir_id_venta: int | None = None) -> list[str]:
    """FR-009a: advertencia no bloqueante (decisión Q3) — a diferencia de
    Compras (006), acá NUNCA se rechaza el guardado por documento duplicado."""
    duplicado = await run_in_threadpool(
        repository.hay_documento_duplicado, id_consignatario, numero_documento, excluir_id_venta
    )
    if duplicado:
        return ["Ya existe una venta de hacienda con este número de documento para este consignatario."]
    return []


@router.post("", response_model=VentaHaciendaDetalleResponse, status_code=201)
async def crear_venta_hacienda(body: VentaHaciendaAltaRequest) -> VentaHaciendaDetalleResponse:
    cabecera = _cabecera_dict(body)
    lineas = [linea.model_dump() for linea in body.lineas]
    vencimientos = [v.model_dump() for v in body.vencimientos]

    # FR-009a: chequear duplicado ANTES de insertar — después de crear, la
    # fila recién insertada calzaría con su propia búsqueda y el aviso se
    # dispararía siempre, incluso en la primera carga de un documento nuevo.
    warnings = await _warnings_duplicado(body.idConsignatario, body.numeroDocumento)

    try:
        id_venta = await run_in_threadpool(repository.create_venta, cabecera, lineas, vencimientos)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    totales = repository.calcular_totales(lineas, cabecera)
    vencimientos_out = await run_in_threadpool(repository.get_vencimientos_venta, id_venta)

    return _to_detalle_response(id_venta, cabecera, totales, vencimientos_out, warnings)


@router.post("/{id_venta}/lock", response_model=LockResponse)
async def adquirir_lock_venta_hacienda(id_venta: int, body: LockRequest) -> LockResponse:
    try:
        lock = await run_in_threadpool(
            repository_locks.adquirir_lock, id_venta, body.lockToken, body.force
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if lock is None:
        raise HTTPException(status_code=409, detail="La venta está siendo editada.")
    return LockResponse(idVenta=lock.id_venta, lockToken=lock.lock_token, expiresAt=lock.expires_at)


@router.delete("/{id_venta}/lock", status_code=204)
async def liberar_lock_venta_hacienda(id_venta: int, x_lock_token: str = Header(...)) -> None:
    liberado = await run_in_threadpool(repository_locks.liberar_lock, id_venta, x_lock_token)
    if not liberado:
        raise HTTPException(status_code=409, detail="El bloqueo pertenece a otra sesión de edición.")


@router.put("/{id_venta}", response_model=VentaHaciendaDetalleResponse)
async def editar_venta_hacienda(
    id_venta: int, body: VentaHaciendaEditRequest, x_lock_token: str = Header(...)
) -> VentaHaciendaDetalleResponse:
    if await run_in_threadpool(repository.get_venta_cabecera, id_venta) is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_venta, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="La venta está siendo editada por otra sesión.")

    cabecera = _cabecera_dict(body)
    lineas = [linea.model_dump() for linea in body.lineas]
    vencimientos = [v.model_dump() for v in body.vencimientos]

    try:
        await run_in_threadpool(repository.update_venta, id_venta, cabecera, lineas, vencimientos)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    totales = repository.calcular_totales(lineas, cabecera)
    vencimientos_out = await run_in_threadpool(repository.get_vencimientos_venta, id_venta)
    warnings = await _warnings_duplicado(body.idConsignatario, body.numeroDocumento, id_venta)

    return _to_detalle_response(id_venta, cabecera, totales, vencimientos_out, warnings)


@router.delete("/{id_venta}", status_code=204)
async def eliminar_venta_hacienda(id_venta: int, x_lock_token: str = Header(...)) -> None:
    """Eliminación definitiva (documento cargado por error) — requiere el
    mismo lock exclusivo que la edición (FR-006a)."""
    if await run_in_threadpool(repository.get_venta_cabecera, id_venta) is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_venta, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="La venta está siendo editada por otra sesión.")

    await run_in_threadpool(repository.delete_venta, id_venta)


@router.get("/{id_venta}/relacionados", response_model=list[DocumentoRelacionado])
async def get_documentos_relacionados(id_venta: int) -> list[DocumentoRelacionado]:
    rows = await run_in_threadpool(repository.get_documentos_relacionados, id_venta)
    return [DocumentoRelacionado(**row) for row in rows]


@router.post("/{id_venta}/relacionados", status_code=204)
async def agregar_documento_relacionado(id_venta: int, body: DocumentoRelacionadoRequest) -> None:
    try:
        await run_in_threadpool(
            repository.agregar_documento_relacionado, id_venta, body.idVentaRelacionada
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{id_venta}/relacionados/{id_venta_relacionada}", status_code=204)
async def quitar_documento_relacionado(id_venta: int, id_venta_relacionada: int) -> None:
    await run_in_threadpool(
        repository.quitar_documento_relacionado, id_venta, id_venta_relacionada
    )


@router.get("/{id_venta}", response_model=VentaHaciendaDetalleResponse)
async def get_venta_hacienda_detalle(id_venta: int) -> VentaHaciendaDetalleResponse:
    """Detalle completo — usado para precargar el formulario de edición
    (a diferencia de `GET /api/ventas-hacienda` que solo trae un resumen)."""
    cabecera = await run_in_threadpool(repository.get_venta_cabecera, id_venta)
    if cabecera is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    lineas_rows = await run_in_threadpool(repository.get_lineas_venta, id_venta)
    lineas = [
        {
            "idComprador": row["idComprador"],
            "comprador": row["comprador"],
            "idTipoProducto": row["idTipoProducto"],
            "cantidad": row["cantidad"],
            "unidadMedida": row["unidadMedida"],
            "pesoTotal": row["pesoTotal"],
            "precioUnitarioA": row["precioUnitarioA"],
            "precioUnitarioB": row["precioUnitarioB"],
        }
        for row in lineas_rows
    ]
    totales = repository.calcular_totales(lineas, cabecera)
    vencimientos_out = await run_in_threadpool(repository.get_vencimientos_venta, id_venta)
    return _to_detalle_response(id_venta, cabecera, totales, vencimientos_out, [])
