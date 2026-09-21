"""Resúmenes de tarjeta endpoints (Historia 1, 008-tarjetas). Todo
`POST`/`PUT`/`DELETE` escribe exclusivamente contra `WC`."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Header, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.tarjetas import repository as tarjetas_repository
from src.features.tarjetas_resumenes import repository, repository_locks
from src.features.tarjetas_resumenes.schemas import (
    CandidatosLineaResponse,
    CompraVinculada,
    ConciliacionPreviewResponse,
    LockRequest,
    LockResponse,
    PagoResumen,
    ResumenAltaRequest,
    ResumenDetalleResponse,
    ResumenEditRequest,
    ResumenesListResponse,
    ResumenListItem,
    VincularCompraRequest,
    VincularLoteRequest,
    VincularPagoRequest,
)

router = APIRouter(prefix="/api/tarjetas-resumenes", tags=["tarjetas-resumenes"])


@router.get("", response_model=ResumenesListResponse)
async def list_resumenes(
    idTarjeta: int | None = Query(default=None),
    fechaCierreDesde: date | None = Query(default=None),
    fechaCierreHasta: date | None = Query(default=None),
    fechaVencimientoDesde: date | None = Query(default=None),
    fechaVencimientoHasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> ResumenesListResponse:
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    rows, total = await run_in_threadpool(
        repository.search_resumenes,
        idTarjeta,
        fechaCierreDesde,
        fechaCierreHasta,
        fechaVencimientoDesde,
        fechaVencimientoHasta,
        norm_page,
        norm_page_size,
    )
    return ResumenesListResponse(
        items=[ResumenListItem(**row) for row in rows], page=norm_page, pageSize=norm_page_size, total=total
    )


def _cabecera_dict(body: ResumenAltaRequest) -> dict:
    return body.model_dump(exclude={"lineas"})


def _to_detalle_response(
    id_resumen: int, cabecera: dict, lineas_out: list[dict], warnings: list[str], pagos_out: list[dict] | None = None
) -> ResumenDetalleResponse:
    total = repository.calcular_total(cabecera, lineas_out)
    cabecera_sin_id = {k: v for k, v in cabecera.items() if k != "idResumen"}
    return ResumenDetalleResponse(
        idResumen=id_resumen,
        **cabecera_sin_id,
        totalCalculado=total,
        lineas=lineas_out,
        pagos=pagos_out or [],
        warnings=warnings,
    )


async def _warnings_duplicado(id_tarjeta: int, codigo: str, excluir_id_resumen: int | None = None) -> list[str]:
    """FR-012: advertencia no bloqueante — nunca rechaza el guardado."""
    duplicado = await run_in_threadpool(repository.hay_resumen_duplicado, id_tarjeta, codigo, excluir_id_resumen)
    if duplicado:
        return ["Ya existe un resumen con este código para esta tarjeta."]
    return []


@router.post("", response_model=ResumenDetalleResponse, status_code=201)
async def crear_resumen(body: ResumenAltaRequest) -> ResumenDetalleResponse:
    cabecera = _cabecera_dict(body)
    lineas = [linea.model_dump() for linea in body.lineas]

    # FR-012: chequear duplicado ANTES de insertar — después de crear, la
    # fila recién insertada calzaría con su propia búsqueda y el aviso se
    # dispararía siempre, incluso en la primera carga de un código nuevo.
    warnings = await _warnings_duplicado(body.idTarjeta, body.codigo)

    try:
        id_resumen = await run_in_threadpool(repository.create_resumen, cabecera, lineas)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    await run_in_threadpool(repository.auto_vincular_compras, id_resumen)
    await run_in_threadpool(tarjetas_repository.auto_vincular_pago, id_resumen)
    lineas_out = await run_in_threadpool(repository.get_lineas, id_resumen)
    pagos_out = await run_in_threadpool(repository.get_pagos, id_resumen)
    return _to_detalle_response(id_resumen, cabecera, lineas_out, warnings, pagos_out)


@router.post("/{id_resumen}/lock", response_model=LockResponse)
async def adquirir_lock_resumen(id_resumen: int, body: LockRequest) -> LockResponse:
    try:
        lock = await run_in_threadpool(repository_locks.adquirir_lock, id_resumen, body.lockToken, body.force)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if lock is None:
        raise HTTPException(status_code=409, detail="El resumen está siendo editado.")
    return LockResponse(idResumen=lock.id_resumen, lockToken=lock.lock_token, expiresAt=lock.expires_at)


@router.delete("/{id_resumen}/lock", status_code=204)
async def liberar_lock_resumen(id_resumen: int, x_lock_token: str = Header(...)) -> None:
    liberado = await run_in_threadpool(repository_locks.liberar_lock, id_resumen, x_lock_token)
    if not liberado:
        raise HTTPException(status_code=409, detail="El bloqueo pertenece a otra sesión de edición.")


@router.put("/{id_resumen}", response_model=ResumenDetalleResponse)
async def editar_resumen(id_resumen: int, body: ResumenEditRequest, x_lock_token: str = Header(...)) -> ResumenDetalleResponse:
    if await run_in_threadpool(repository.get_resumen_detalle, id_resumen) is None:
        raise HTTPException(status_code=404, detail="Resumen no encontrado")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_resumen, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="El resumen está siendo editado por otra sesión.")

    cabecera = _cabecera_dict(body)
    lineas = [linea.model_dump() for linea in body.lineas]

    try:
        await run_in_threadpool(repository.update_resumen, id_resumen, cabecera, lineas)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    # Las líneas se recrean de punta a punta en cada edición (mismo
    # criterio "PUT reemplaza todo" que el resto de la app) — se
    # reintenta el auto-vínculo por si alguna línea nueva matchea.
    await run_in_threadpool(repository.auto_vincular_compras, id_resumen)
    await run_in_threadpool(tarjetas_repository.auto_vincular_pago, id_resumen)
    lineas_out = await run_in_threadpool(repository.get_lineas, id_resumen)
    pagos_out = await run_in_threadpool(repository.get_pagos, id_resumen)
    warnings = await _warnings_duplicado(body.idTarjeta, body.codigo, id_resumen)
    return _to_detalle_response(id_resumen, cabecera, lineas_out, warnings, pagos_out)


@router.delete("/{id_resumen}", status_code=204)
async def eliminar_resumen(id_resumen: int, x_lock_token: str = Header(...)) -> None:
    if await run_in_threadpool(repository.get_resumen_detalle, id_resumen) is None:
        raise HTTPException(status_code=404, detail="Resumen no encontrado")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_resumen, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="El resumen está siendo editado por otra sesión.")

    await run_in_threadpool(repository.delete_resumen, id_resumen)


@router.get("/{id_resumen}", response_model=ResumenDetalleResponse)
async def get_resumen_detalle(id_resumen: int) -> ResumenDetalleResponse:
    cabecera = await run_in_threadpool(repository.get_resumen_detalle, id_resumen)
    if cabecera is None:
        raise HTTPException(status_code=404, detail="Resumen no encontrado")
    # Resuelve automáticamente los resúmenes históricos (migrados antes de
    # que existiera este mecanismo) la primera vez que se consultan — sin
    # esto, los ~1600 resúmenes ya cargados quedarían sin vincular hasta
    # que alguien los edite (feedback 2026-09-19, puntos 4 y 6).
    await run_in_threadpool(repository.auto_vincular_compras, id_resumen)
    await run_in_threadpool(tarjetas_repository.auto_vincular_pago, id_resumen)
    lineas_out = await run_in_threadpool(repository.get_lineas, id_resumen)
    pagos_out = await run_in_threadpool(repository.get_pagos, id_resumen)
    return _to_detalle_response(id_resumen, cabecera, lineas_out, warnings=[], pagos_out=pagos_out)


# --- Punto 4 del feedback (2026-09-19): vínculo línea de consumo -> Compras reales ---


@router.post("/lineas/{id_linea_consumo}/compras", response_model=CompraVinculada, status_code=201)
async def vincular_compra_a_linea(id_linea_consumo: int, body: VincularCompraRequest) -> CompraVinculada:
    try:
        id_vinculo = await run_in_threadpool(
            repository.vincular_compra, id_linea_consumo, body.idCompra, body.importeImputado
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc
    vinculos = await run_in_threadpool(repository.get_compras_vinculadas, id_linea_consumo)
    for v in vinculos:
        if v["idVinculo"] == id_vinculo:
            return CompraVinculada(**v)
    raise HTTPException(status_code=500, detail="No se pudo leer el vínculo recién creado")


@router.get("/lineas/{id_linea_consumo}/candidatos", response_model=CandidatosLineaResponse)
async def get_candidatos_linea(id_linea_consumo: int) -> CandidatosLineaResponse:
    """Documentos del proveedor de la línea (pesificados) y combinaciones de
    ellos que la concilian — ver `conciliacion_documentos`."""
    data = await run_in_threadpool(repository.get_candidatos_linea, id_linea_consumo)
    if data is None:
        raise HTTPException(status_code=404, detail="Línea de consumo no encontrada")
    return CandidatosLineaResponse(**data)


@router.get("/lineas/{id_linea_consumo}/conciliacion", response_model=ConciliacionPreviewResponse)
async def previsualizar_conciliacion(
    id_linea_consumo: int, idsCompra: list[int] = Query(min_length=1)
) -> ConciliacionPreviewResponse:
    try:
        data = await run_in_threadpool(repository.calcular_conciliacion, id_linea_consumo, idsCompra)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc
    return ConciliacionPreviewResponse(**data)


@router.post("/lineas/{id_linea_consumo}/compras/lote", response_model=list[CompraVinculada], status_code=201)
async def vincular_compras_lote(id_linea_consumo: int, body: VincularLoteRequest) -> list[CompraVinculada]:
    """Vincula varios documentos (Factura/NC/ND) a la línea de una sola vez,
    repartiendo su importe entre ellos (pesificando los que están en dólares)."""
    try:
        vinculos = await run_in_threadpool(repository.vincular_compras_lote, id_linea_consumo, body.idsCompra)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc
    return [CompraVinculada(**v) for v in vinculos]


@router.delete("/lineas/{id_linea_consumo}/compras/{id_vinculo}", status_code=204)
async def quitar_vinculo_compra(id_linea_consumo: int, id_vinculo: int) -> None:
    await run_in_threadpool(repository.quitar_vinculo_compra, id_vinculo)


# --- Punto 6 del feedback (2026-09-19): pagos de un resumen ---


@router.get("/{id_resumen}/pagos", response_model=list[PagoResumen])
async def get_pagos_resumen(id_resumen: int) -> list[PagoResumen]:
    rows = await run_in_threadpool(repository.get_pagos, id_resumen)
    return [PagoResumen(**row) for row in rows]


@router.post("/{id_resumen}/pagos", response_model=PagoResumen, status_code=201)
async def registrar_pago_resumen(id_resumen: int, body: VincularPagoRequest) -> PagoResumen:
    id_pago = await run_in_threadpool(
        repository.registrar_pago, id_resumen, body.fecha, body.importe, body.origen, body.idMovimientoOrigen
    )
    rows = await run_in_threadpool(repository.get_pagos, id_resumen)
    for row in rows:
        if row["idPago"] == id_pago:
            return PagoResumen(**row)
    raise HTTPException(status_code=500, detail="No se pudo leer el pago recién creado")


@router.delete("/{id_resumen}/pagos/{id_pago}", status_code=204)
async def eliminar_pago_resumen(id_resumen: int, id_pago: int) -> None:
    await run_in_threadpool(repository.eliminar_pago, id_pago)
