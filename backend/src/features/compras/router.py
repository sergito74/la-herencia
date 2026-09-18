"""Compras endpoints.

La mayoría son GET (solo lectura, FR-010 de 002-compras). Desde
006-carga-compras se agregan POST/PUT de alta/edición y los endpoints de
bloqueo — todos escriben exclusivamente contra `WC` vía
`execute_write_transaction` (ver `src/db/connection.py`), nunca contra
`LaHerencia`.
"""

from __future__ import annotations

import mimetypes
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.compras import repository, repository_locks
from src.features.compras.schemas import (
    CampaniaCreada,
    CampaniaNuevaRequest,
    CentroCostoCreado,
    CentroCostoNuevoRequest,
    Compra,
    CompraAltaRequest,
    CompraDetalle,
    CompraDetalleResponse,
    CompraEditRequest,
    ComprasListResponse,
    DestinoCreado,
    DestinoNuevoRequest,
    DocumentoRelacionado,
    DocumentoRelacionadoRequest,
    FiltrosComprasResponse,
    LockRequest,
    LockResponse,
    RubroCreado,
    RubroNuevoRequest,
    RubroSugeridoResponse,
    TrazabilidadCompra,
)

router = APIRouter(prefix="/api/compras", tags=["compras"])


def _cabecera_dict(body: CompraAltaRequest) -> dict:
    return body.model_dump(exclude={"lineas", "vencimientos"})


def _to_detalle_response(
    id_compra: int, cabecera: dict, totales: dict, vencimientos_out: list[dict], warnings: list[str]
) -> CompraDetalleResponse:
    return CompraDetalleResponse(
        idCompra=id_compra,
        **cabecera,
        subtotalNeto=totales["subtotalNeto"],
        ivaCabecera=totales["ivaCabecera"],
        importeTotal=totales["importeTotal"],
        pesificado=totales["pesificado"],
        lineas=totales["lineas"],
        vencimientos=vencimientos_out,
        warnings=warnings,
    )


@router.get("", response_model=ComprasListResponse)
async def list_compras(
    proveedor: str | None = Query(default=None),
    numeroDocumento: str | None = Query(default=None),
    fechaDesde: date | None = Query(default=None),
    fechaHasta: date | None = Query(default=None),
    idCentroCosto: int | None = Query(default=None),
    idRubro: int | None = Query(default=None),
    idContacto: int | None = Query(default=None),
    tipoDocumento: list[str] | None = Query(default=None),
    productoServicio: str | None = Query(default=None),
    idDestino: int | None = Query(default=None),
    campania: str | None = Query(default=None),
    sortBy: str | None = Query(default=None),
    sortDir: str = Query(default="asc"),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> ComprasListResponse:
    """`idContacto` (006-carga-compras): filtro exacto, usado para listar los
    documentos relacionados de un proveedor al cargar/editar una compra.
    `tipoDocumento` (repetible, 006): restringe a esos tipos exactos —
    usado por el mismo panel para acotar a los tipos complementarios
    (ej. Notas de Crédito/Débito) sin que la paginación por fecha los deje
    afuera de la ventana visible. `productoServicio`/`idDestino`/`campania`
    (006): filtros de búsqueda del listado, pedido explícito del usuario.
    `sortBy`/`sortDir` (006): ordena todo el resultado en el servidor
    (`fecha`/`proveedor`/`tipoDocumento`/`numeroDocumento`), no solo la
    página cargada — pedido explícito tras detectar que el orden anterior
    (cliente, solo la página visible) no era el comportamiento esperado."""
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    items, total = await run_in_threadpool(
        repository.search_compras,
        proveedor,
        numeroDocumento,
        fechaDesde,
        fechaHasta,
        idCentroCosto,
        idRubro,
        norm_page,
        norm_page_size,
        idContacto,
        tipoDocumento,
        productoServicio,
        idDestino,
        campania,
        sortBy,
        sortDir,
    )
    return ComprasListResponse(
        items=[Compra(**item) for item in items],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.get("/filtros", response_model=FiltrosComprasResponse)
async def get_filtros_compras() -> FiltrosComprasResponse:
    return FiltrosComprasResponse(**await run_in_threadpool(repository.get_filtros))


@router.get("/rubro-sugerido", response_model=RubroSugeridoResponse)
async def get_rubro_sugerido(productoServicio: str = Query(min_length=1)) -> RubroSugeridoResponse:
    """FR-012a: sugerencia no vinculante, nunca forzada — ver DetalleLineaForm.tsx."""
    row = await run_in_threadpool(repository.get_rubro_sugerido, productoServicio)
    if row is None:
        return RubroSugeridoResponse()
    return RubroSugeridoResponse(**row)


@router.get("/documento-local")
async def abrir_documento_local(ruta: str = Query(min_length=1)) -> FileResponse:
    """Sirve por HTTP un PDF que está en el disco de esta misma PC (campo
    "Documento original" de una compra, ej. `C:\\...\\factura.pdf`). Un
    navegador nunca puede navegar directo a `file://` por seguridad — esto
    lo evita: el backend (que corre en esta PC) lee el archivo y lo
    devuelve como respuesta HTTP normal, que sí se puede mostrar/descargar.
    Lectura pura del filesystem local del usuario, no de una base de datos."""
    ruta_limpia = ruta.strip()
    if ruta_limpia.startswith('"') and ruta_limpia.endswith('"') and len(ruta_limpia) >= 2:
        ruta_limpia = ruta_limpia[1:-1]
    if not repository.es_ruta_local_windows(ruta_limpia):
        raise HTTPException(status_code=400, detail="La ruta no tiene formato de ruta local de Windows.")
    path = Path(ruta_limpia)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"No se encontró el archivo en: {ruta_limpia}")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path=path,
        media_type=media_type,
        # "inline", no "attachment" (default de FileResponse con `filename`):
        # el pedido es mostrar el PDF en la pestaña, no forzar la descarga.
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )


@router.get("/{id_compra}", response_model=CompraDetalle)
async def get_compra_detalle(id_compra: int) -> CompraDetalle:
    cabecera = await run_in_threadpool(repository.get_compra_cabecera, id_compra)
    if cabecera is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    lineas = await run_in_threadpool(repository.get_lineas_compra, id_compra)
    vencimientos = await run_in_threadpool(repository.get_vencimientos_compra, id_compra)
    return CompraDetalle(**cabecera, lineas=lineas, vencimientos=vencimientos)


@router.get("/{id_compra}/trazabilidad", response_model=TrazabilidadCompra)
async def get_compra_trazabilidad(id_compra: int) -> TrazabilidadCompra:
    movimientos = await run_in_threadpool(repository.get_trazabilidad_compra, id_compra)
    return TrazabilidadCompra(idCompra=id_compra, movimientos=movimientos)


@router.get("/{id_compra}/relacionados", response_model=list[DocumentoRelacionado])
async def get_documentos_relacionados(id_compra: int) -> list[DocumentoRelacionado]:
    """Documentos vinculados manualmente a esta compra (ej. una Nota de
    Crédito/Débito que complementa una Factura) — no es un listado
    automático de todo lo comprado al proveedor, ver research/feedback 2026-09-17."""
    rows = await run_in_threadpool(repository.get_documentos_relacionados, id_compra)
    return [DocumentoRelacionado(**row) for row in rows]


@router.post("/{id_compra}/relacionados", status_code=204)
async def agregar_documento_relacionado(id_compra: int, body: DocumentoRelacionadoRequest) -> None:
    try:
        await run_in_threadpool(
            repository.agregar_documento_relacionado, id_compra, body.idCompraRelacionada
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{id_compra}/relacionados/{id_compra_relacionada}", status_code=204)
async def quitar_documento_relacionado(id_compra: int, id_compra_relacionada: int) -> None:
    await run_in_threadpool(
        repository.quitar_documento_relacionado, id_compra, id_compra_relacionada
    )


@router.post("/rubros", response_model=RubroCreado, status_code=201)
async def crear_rubro(body: RubroNuevoRequest) -> RubroCreado:
    """Alta controlada (006): el combo de Rubro no admite texto libre — este
    endpoint solo se llama tras una confirmación explícita del usuario en el frontend."""
    return RubroCreado(**await run_in_threadpool(repository.create_rubro, body.nombre))


@router.post("/centros-costo", response_model=CentroCostoCreado, status_code=201)
async def crear_centro_costo(body: CentroCostoNuevoRequest) -> CentroCostoCreado:
    return CentroCostoCreado(**await run_in_threadpool(repository.create_centro_costo, body.nombre))


@router.post("/destinos", response_model=DestinoCreado, status_code=201)
async def crear_destino(body: DestinoNuevoRequest) -> DestinoCreado:
    return DestinoCreado(**await run_in_threadpool(repository.create_destino, body.nombre))


@router.post("/campanias", response_model=CampaniaCreada, status_code=201)
async def crear_campania(body: CampaniaNuevaRequest) -> CampaniaCreada:
    return CampaniaCreada(**await run_in_threadpool(repository.create_campania, body.nombre))


async def _rechazar_si_duplicado(
    id_contacto: int, numero_documento: str, excluir_id_compra: int | None = None
) -> None:
    """Bloqueo duro (400), sin excepción: proveedor + nº de documento ya
    cargado en otra compra. Pedido explícito del usuario (2026-09-17) tras
    detectar cargas duplicadas por error — antes era solo un warning no
    bloqueante (FR-014 original); esto lo reemplaza."""
    duplicado = await run_in_threadpool(
        repository.buscar_documento_duplicado, id_contacto, numero_documento, excluir_id_compra
    )
    if duplicado is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Ya existe la compra #{duplicado['idCompra']} con el mismo número de "
                "documento para este proveedor."
            ),
        )


@router.post("", response_model=CompraDetalleResponse, status_code=201)
async def crear_compra(body: CompraAltaRequest) -> CompraDetalleResponse:
    await _rechazar_si_duplicado(body.idContacto, body.numeroDocumento)

    cabecera = _cabecera_dict(body)
    lineas = [linea.model_dump() for linea in body.lineas]
    vencimientos = [v.model_dump() for v in body.vencimientos]

    try:
        id_compra = await run_in_threadpool(repository.create_compra, cabecera, lineas, vencimientos)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    lineas_con_defaults = repository.resolver_defaults_lineas(lineas)
    totales = repository.calcular_totales(lineas_con_defaults, cabecera)
    vencimientos_out = await run_in_threadpool(repository.get_vencimientos_compra, id_compra)

    return _to_detalle_response(id_compra, cabecera, totales, vencimientos_out, [])


@router.post("/{id_compra}/lock", response_model=LockResponse)
async def adquirir_lock_compra(id_compra: int, body: LockRequest) -> LockResponse:
    try:
        lock = await run_in_threadpool(
            repository_locks.adquirir_lock, id_compra, body.lockToken, body.force
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if lock is None:
        raise HTTPException(status_code=409, detail="La compra está siendo editada.")
    return LockResponse(idCompra=lock.id_compra, lockToken=lock.lock_token, expiresAt=lock.expires_at)


@router.delete("/{id_compra}/lock", status_code=204)
async def liberar_lock_compra(id_compra: int, x_lock_token: str = Header(...)) -> None:
    liberado = await run_in_threadpool(repository_locks.liberar_lock, id_compra, x_lock_token)
    if not liberado:
        raise HTTPException(status_code=409, detail="El bloqueo pertenece a otra sesión de edición.")


@router.put("/{id_compra}", response_model=CompraDetalleResponse)
async def editar_compra(
    id_compra: int, body: CompraEditRequest, x_lock_token: str = Header(...)
) -> CompraDetalleResponse:
    if await run_in_threadpool(repository.get_compra_cabecera, id_compra) is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_compra, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="La compra está siendo editada por otra sesión.")

    await _rechazar_si_duplicado(body.idContacto, body.numeroDocumento, id_compra)

    cabecera = _cabecera_dict(body)
    lineas = [linea.model_dump() for linea in body.lineas]
    vencimientos = [v.model_dump() for v in body.vencimientos]

    try:
        await run_in_threadpool(repository.update_compra, id_compra, cabecera, lineas, vencimientos)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc

    lineas_con_defaults = repository.resolver_defaults_lineas(lineas)
    totales = repository.calcular_totales(lineas_con_defaults, cabecera)
    vencimientos_out = await run_in_threadpool(repository.get_vencimientos_compra, id_compra)

    return _to_detalle_response(id_compra, cabecera, totales, vencimientos_out, [])


@router.delete("/{id_compra}", status_code=204)
async def eliminar_compra(id_compra: int, x_lock_token: str = Header(...)) -> None:
    """Eliminación definitiva (documento cargado por error) — requiere el
    mismo lock exclusivo que la edición, para no borrar una compra que
    otra sesión está editando en simultáneo."""
    if await run_in_threadpool(repository.get_compra_cabecera, id_compra) is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")

    vigente = await run_in_threadpool(repository_locks.verificar_lock, id_compra, x_lock_token)
    if not vigente:
        raise HTTPException(status_code=409, detail="La compra está siendo editada por otra sesión.")

    await run_in_threadpool(repository.delete_compra, id_compra)
