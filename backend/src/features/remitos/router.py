"""Endpoints de Remitos (010-remitos). Toda escritura va contra `WC`."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_all
from src.features.remitos import exportacion, repository
from src.features.remitos.repository import RequiereConfirmacion
from src.features.remitos.schemas import AnularIn, FacturaIn, RemitoIn, ValidarRemitoIn, VincularIn

router = APIRouter(prefix="/api/remitos", tags=["remitos"])


async def _ejecutar(fn, *args, **kwargs):
    """Errores de negocio: 400 con la lista de mensajes; confirmaciones pendientes: 409."""
    try:
        return await run_in_threadpool(fn, *args, **kwargs)
    except RequiereConfirmacion as exc:
        raise HTTPException(status_code=409, detail=exc.mensajes) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc


@router.get("")
async def listar_remitos(
    idProveedor: int | None = None,
    proveedor: str | None = None,
    fechaDesde: date | None = None,
    fechaHasta: date | None = None,
    producto: str | None = None,
    nroRemito: str | None = None,
    estado: str | None = Query(default=None, description="sinFactura, sinVincular, parcial, completo, conDiferencia, anulado, revisar"),
    page: int = 1,
    pageSize: int = 25,
) -> dict:
    return await _ejecutar(repository.listar_remitos, idProveedor, proveedor, fechaDesde, fechaHasta, producto, estado, nroRemito, max(page, 1), min(max(pageSize, 1), 200))


@router.get("/exportar")
async def exportar_remitos(
    idProveedor: int | None = None, proveedor: str | None = None, fechaDesde: date | None = None, fechaHasta: date | None = None,
    producto: str | None = None, nroRemito: str | None = None, estado: str | None = None,
) -> Response:
    """Planilla (.xlsx) de remitos y sus renglones, con los filtros del listado."""
    contenido = await _ejecutar(
        exportacion.remitos_xlsx, id_proveedor=idProveedor, proveedor=proveedor, desde=fechaDesde, hasta=fechaHasta, producto=producto, estado=estado, nro_remito=nroRemito
    )
    return Response(content=contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="remitos-{date.today().isoformat()}.xlsx"'})


@router.get("/catalogos")
async def catalogos() -> dict:
    est = await run_in_threadpool(fetch_all, "SELECT Id AS id, Establecimiento AS nombre FROM dbo.Establecimientos ORDER BY Id")
    return {"establecimientos": est}


@router.get("/facturas-sin-remito")
async def facturas_sin_remito(
    fechaDesde: date | None = None, fechaHasta: date | None = None, proveedor: str | None = None, page: int = 1, pageSize: int = 25
) -> dict:
    """Facturas con renglones de insumos que no tienen remito vinculado."""
    return await _ejecutar(repository.facturas_sin_remito, fechaDesde, fechaHasta, proveedor, max(page, 1), min(max(pageSize, 1), 200))


@router.post("/validar")
async def validar_remito(body: ValidarRemitoIn) -> dict:
    """Advertencias de un número de remito (formato y duplicado), sin guardar."""
    adv = await _ejecutar(repository.advertencias, body.idProveedor, body.nroRemito, body.idExcluir)
    return {**adv, "mensajes": repository._mensajes_advertencia(adv)}


@router.get("/{id_remito}")
async def get_remito(id_remito: int) -> dict:
    remito = await _ejecutar(repository.get_remito, id_remito)
    if remito is None:
        raise HTTPException(status_code=404, detail="Remito no encontrado")
    return remito


@router.post("", status_code=201)
async def crear_remito(body: RemitoIn) -> dict:
    datos = body.model_dump(exclude={"confirmar"})
    id_remito = await _ejecutar(repository.crear_remito, datos, body.confirmar)
    return {"idRemito": id_remito}


@router.put("/{id_remito}")
async def actualizar_remito(id_remito: int, body: RemitoIn) -> dict:
    datos = body.model_dump(exclude={"confirmar"})
    await _ejecutar(repository.actualizar_remito, id_remito, datos, body.confirmar)
    return {"idRemito": id_remito}


@router.post("/{id_remito}/anular", status_code=204)
async def anular_remito(id_remito: int, body: AnularIn) -> None:
    await _ejecutar(repository.anular_remito, id_remito, body.motivo)


@router.get("/{id_remito}/facturas-candidatas")
async def facturas_candidatas(id_remito: int) -> list[dict]:
    return await _ejecutar(repository.facturas_candidatas, id_remito)


@router.post("/{id_remito}/vinculos", status_code=201)
async def vincular_renglones(id_remito: int, body: VincularIn) -> dict:
    return await _ejecutar(repository.vincular_renglones, id_remito, [i.model_dump() for i in body.items])


@router.delete("/{id_remito}/vinculos/{id_vinculo}", status_code=204)
async def desvincular_renglon(id_remito: int, id_vinculo: int) -> None:
    await _ejecutar(repository.desvincular_renglon, id_remito, id_vinculo)


@router.post("/{id_remito}/facturas", status_code=204)
async def vincular_factura(id_remito: int, body: FacturaIn) -> None:
    await _ejecutar(repository.vincular_factura, id_remito, body.idCompra)


@router.delete("/{id_remito}/facturas/{id_compra}", status_code=204)
async def desvincular_factura(id_remito: int, id_compra: int) -> None:
    await _ejecutar(repository.desvincular_factura, id_remito, id_compra)
