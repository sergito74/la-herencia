"""Endpoints de stock de insumos (010-remitos): catálogo, existencias FIFO, bajas y ajustes."""

from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Form, HTTPException, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from src.features.remitos import catalogo, exportacion, recuento, stock_repo
from src.features.remitos.repository import RequiereConfirmacion
from src.features.remitos.router import _ejecutar
from src.features.remitos.schemas import (
    AjusteIn,
    AnularIn,
    BajaIn,
    ConfirmarUnidadesIn,
    EquivalenciaIn,
    UnidadBaseIn,
)

router = APIRouter(prefix="/api/stock", tags=["stock"])


# ------------------------------------------------------------------ catálogo
@router.get("/unidades")
async def unidades() -> list[dict]:
    return await _ejecutar(catalogo.listar_unidades)


@router.get("/productos/tipos")
async def tipos() -> list[str]:
    return await _ejecutar(catalogo.tipos_de_producto)


@router.get("/productos/por-confirmar")
async def por_confirmar() -> list[dict]:
    """Productos con unidad base propuesta según su uso histórico, a revisar."""
    return await _ejecutar(catalogo.productos_por_confirmar)


@router.post("/productos/confirmar-unidades")
async def confirmar_unidades(body: ConfirmarUnidadesIn) -> dict:
    return {"confirmadas": await _ejecutar(catalogo.confirmar_unidades, body.ids)}


@router.get("/productos")
async def productos(q: str | None = None, tipo: str | None = None, limite: int = 30) -> list[dict]:
    return await _ejecutar(catalogo.buscar_productos, q, tipo, min(max(limite, 1), 100))


@router.get("/productos/{id_producto}")
async def producto(id_producto: int) -> dict:
    p = await _ejecutar(catalogo.get_producto, id_producto)
    if p is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {**p, "unidadBaseSugerida": catalogo.unidad_base_sugerida(p["tipo"])}


@router.put("/productos/{id_producto}/unidad-base", status_code=204)
async def set_unidad_base(id_producto: int, body: UnidadBaseIn) -> None:
    await _ejecutar(catalogo.set_unidad_base, id_producto, body.unidad.strip().upper())


@router.put("/productos/{id_producto}/equivalencias", status_code=204)
async def set_equivalencia(id_producto: int, body: EquivalenciaIn) -> None:
    await _ejecutar(catalogo.set_equivalencia, id_producto, body.unidad.strip().upper(), body.factor)


# ------------------------------------------------------------------ existencias
@router.get("/existencias")
async def existencias(q: str | None = None, tipo: str | None = None, estado: str | None = None) -> dict:
    """Existencia y valor FIFO por producto. `estado`: conStock, negativo, costoPendiente, todos."""
    return await _ejecutar(stock_repo.existencias, q, tipo, estado)


@router.get("/existencias/exportar")
async def exportar_existencias(q: str | None = None, tipo: str | None = None, estado: str | None = None) -> Response:
    contenido = await _ejecutar(exportacion.existencias_xlsx, q, tipo, estado)
    return Response(content=contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="existencias-{date.today().isoformat()}.xlsx"'})


@router.get("/existencias/recuento")
async def exportar_recuento(q: str | None = None, tipo: str | None = None, estado: str | None = None) -> Response:
    """Planilla imprimible para el recuento físico de stock en el campo."""
    contenido = await _ejecutar(exportacion.recuento_xlsx, q, tipo, estado)
    return Response(content=contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="recuento-stock-{date.today().isoformat()}.xlsx"'})


@router.post("/existencias/recuento/previsualizar")
async def previsualizar_recuento(archivo: UploadFile, fecha: date | None = Form(None), asignaciones: str | None = Form(None)) -> dict:
    """Compara la planilla de recuento completada contra la existencia a la fecha del recuento."""
    return await _ejecutar(recuento.previsualizar, await archivo.read(), fecha, _asignaciones(asignaciones))


@router.post("/existencias/recuento/aplicar", status_code=201)
async def aplicar_recuento(
    archivo: UploadFile, motivo: str = Form(...), fecha: date | None = Form(None), asignaciones: str | None = Form(None)
) -> dict:
    """Graba el recuento: reparte cada diferencia entre las órdenes del período (recuento.py)."""
    return await _ejecutar(recuento.aplicar, await archivo.read(), fecha, motivo, _asignaciones(asignaciones))


def _asignaciones(texto: str | None) -> dict[int, int]:
    """JSON {fila: idProducto} con los productos elegidos a mano en la vista previa."""
    if not texto:
        return {}
    try:
        return {int(k): int(v) for k, v in json.loads(texto).items()}
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail=["Asignaciones de productos inválidas."]) from exc


@router.get("/recuentos")
async def listar_recuentos() -> list[dict]:
    return await _ejecutar(recuento.listar)


@router.post("/recuentos/{id_recuento}/anular", status_code=204)
async def anular_recuento(id_recuento: int, body: AnularIn) -> None:
    await _ejecutar(recuento.anular, id_recuento, body.motivo)


@router.get("/existencias/{id_producto}/kardex")
async def kardex(id_producto: int) -> dict:
    k = await _ejecutar(stock_repo.kardex, id_producto)
    if k is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return k


# ------------------------------------------------------------------ bajas
@router.get("/bajas/opciones")
async def opciones_bajas() -> dict:
    return await _ejecutar(stock_repo.opciones_bajas)


@router.get("/bajas")
async def listar_bajas(
    fechaDesde: date | None = None, fechaHasta: date | None = None, motivo: str | None = None, producto: str | None = None,
    incluirAnuladas: bool = False, page: int = 1, pageSize: int = 25,
) -> dict:
    return await _ejecutar(stock_repo.listar_bajas, fechaDesde, fechaHasta, motivo, producto, incluirAnuladas, max(page, 1), min(max(pageSize, 1), 200))


@router.get("/bajas/exportar")
async def exportar_bajas(fechaDesde: date | None = None, fechaHasta: date | None = None, motivo: str | None = None, producto: str | None = None) -> Response:
    contenido = await _ejecutar(exportacion.bajas_xlsx, desde=fechaDesde, hasta=fechaHasta, motivo=motivo, producto=producto)
    return Response(content=contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="bajas-de-stock-{date.today().isoformat()}.xlsx"'})


@router.post("/bajas", status_code=201)
async def crear_baja(body: BajaIn) -> dict:
    return {"idBaja": await _ejecutar(stock_repo.crear_baja, body.model_dump(exclude={"confirmar"}), body.confirmar)}


@router.post("/bajas/{id_baja}/anular", status_code=204)
async def anular_baja(id_baja: int, body: AnularIn) -> None:
    await _ejecutar(stock_repo.anular_baja, id_baja, body.motivo)


# ------------------------------------------------------------------ ajustes
@router.get("/ajustes")
async def listar_ajustes(fechaDesde: date | None = None, fechaHasta: date | None = None, producto: str | None = None, page: int = 1, pageSize: int = 25) -> dict:
    return await _ejecutar(stock_repo.listar_ajustes, fechaDesde, fechaHasta, producto, max(page, 1), min(max(pageSize, 1), 200))


@router.post("/ajustes", status_code=201)
async def crear_ajuste(body: AjusteIn) -> dict:
    return {"idAjuste": await _ejecutar(stock_repo.crear_ajuste, body.model_dump(exclude={"confirmar"}), body.confirmar)}


@router.post("/ajustes/{id_ajuste}/anular", status_code=204)
async def anular_ajuste(id_ajuste: int, body: AnularIn) -> None:
    await _ejecutar(stock_repo.anular_ajuste, id_ajuste, body.motivo)
