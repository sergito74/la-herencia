"""Endpoints de Órdenes de Trabajo (011-ordenes-trabajo). Toda escritura va contra `WC`."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Response
from starlette.concurrency import run_in_threadpool

from src.features.ordenes import exportacion, repository, resultado
from src.features.ordenes.repository import RequiereConfirmacion
from src.features.ordenes.schemas import (
    AnularIn,
    DevolucionIn,
    EjecutarIn,
    FacturaContratistaIn,
    MaquinariaIn,
    OrdenIn,
    TipoLaborIn,
)

router = APIRouter(prefix="/api/ordenes", tags=["ordenes"])


async def _ejecutar(fn, *args, **kwargs):
    """Errores de negocio: 400 con la lista de mensajes; confirmaciones pendientes: 409."""
    try:
        return await run_in_threadpool(fn, *args, **kwargs)
    except RequiereConfirmacion as exc:
        raise HTTPException(status_code=409, detail=exc.mensajes) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=exc.args[0]) from exc


@router.get("/catalogos")
async def catalogos() -> dict:
    return {
        "lotes": await run_in_threadpool(repository.listar_lotes),
        "cultivos": await run_in_threadpool(repository.listar_cultivos),
        "campanias": await run_in_threadpool(repository.listar_campanias),
        "tiposLabor": await run_in_threadpool(repository.listar_tipos_labor),
        "contratistas": await run_in_threadpool(repository.listar_contratistas),
    }


@router.get("")
async def listar_ordenes(
    idContratista: int | None = None,
    idLote: int | None = None,
    idCultivo: int | None = None,
    idCampania: int | None = None,
    fechaDesde: date | None = None,
    fechaHasta: date | None = None,
    estado: str | None = None,
    page: int = 1,
    pageSize: int = 25,
) -> dict:
    return await _ejecutar(
        repository.listar_ordenes, idContratista, idLote, idCultivo, idCampania, fechaDesde, fechaHasta, estado, max(page, 1), min(max(pageSize, 1), 200)
    )


@router.get("/exportar")
async def exportar_ordenes(
    idContratista: int | None = None, idLote: int | None = None, idCultivo: int | None = None, idCampania: int | None = None,
    fechaDesde: date | None = None, fechaHasta: date | None = None, estado: str | None = None,
) -> Response:
    contenido = await _ejecutar(
        exportacion.ordenes_xlsx, idContratista=idContratista, idLote=idLote, idCultivo=idCultivo, idCampania=idCampania,
        fechaDesde=fechaDesde, fechaHasta=fechaHasta, estado=estado,
    )
    return Response(content=contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="ordenes-{date.today().isoformat()}.xlsx"'})


@router.get("/{id_orden}/formulario-retiro/exportar")
async def exportar_formulario_retiro(id_orden: int) -> Response:
    contenido = await _ejecutar(exportacion.formulario_retiro_xlsx, id_orden)
    return Response(content=contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="formulario-retiro-orden-{id_orden}.xlsx"'})


@router.get("/resultado-cultivo")
async def resultado_cultivo(idCultivo: int | None = None, idCampania: int | None = None, idLote: int | None = None) -> dict:
    """Costo por Cultivo/Campaña (Historia 6): sin fecha de cierre (FR-015)."""
    propio = await _ejecutar(resultado.costo_por_cultivo_campania, idCultivo, idCampania, idLote)
    heredado = await _ejecutar(resultado.resumen_campania_heredado, idCampania)
    return {"porCultivoCampania": propio, "resumenCampaniaHeredado": heredado}


@router.get("/resultado-cultivo/exportar")
async def exportar_resultado_cultivo(idCultivo: int | None = None, idCampania: int | None = None, idLote: int | None = None) -> Response:
    contenido = await _ejecutar(exportacion.resultado_cultivo_xlsx, idCultivo, idCampania, idLote)
    return Response(content=contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="resultado-cultivo-{date.today().isoformat()}.xlsx"'})


@router.get("/tipos-labor")
async def tipos_labor() -> list[dict]:
    return await _ejecutar(repository.listar_tipos_labor)


@router.post("/tipos-labor", status_code=201)
async def crear_tipo_labor(body: TipoLaborIn) -> dict:
    idx = await _ejecutar(repository.crear_tipo_labor, body.nombre)
    return {"idTipoLabor": idx}


@router.get("/{id_orden}")
async def get_orden(id_orden: int) -> dict:
    orden = await _ejecutar(repository.obtener_orden, id_orden)
    if orden is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return orden


@router.post("", status_code=201)
async def crear_orden(body: OrdenIn) -> dict:
    datos = body.model_dump(exclude={"confirmar"})
    return await _ejecutar(repository.crear_orden, datos, body.confirmar)


@router.patch("/{id_orden}")
async def editar_orden(id_orden: int, body: OrdenIn) -> dict:
    datos = body.model_dump(exclude={"confirmar"})
    await _ejecutar(repository.editar_orden, id_orden, datos, body.confirmar)
    return {"idOrden": id_orden}


@router.post("/{id_orden}/ejecutar", status_code=204)
async def ejecutar_orden(id_orden: int, body: EjecutarIn) -> None:
    await _ejecutar(repository.ejecutar_orden, id_orden, body.fechaEjecucion)


@router.post("/{id_orden}/anular", status_code=204)
async def anular_orden(id_orden: int, body: AnularIn) -> None:
    await _ejecutar(repository.anular_orden, id_orden, body.motivo)


@router.post("/{id_orden}/insumos/{id_orden_insumo}/devoluciones", status_code=201)
async def registrar_devolucion(id_orden: int, id_orden_insumo: int, body: DevolucionIn) -> dict:
    idx = await _ejecutar(repository.registrar_devolucion, id_orden_insumo, body.model_dump())
    return {"idDevolucion": idx}


@router.post("/{id_orden}/maquinaria", status_code=201)
async def agregar_maquinaria(id_orden: int, body: MaquinariaIn) -> dict:
    return await _ejecutar(repository.agregar_maquinaria, id_orden, body.model_dump())


@router.post("/{id_orden}/factura", status_code=201)
async def vincular_factura(id_orden: int, body: FacturaContratistaIn) -> dict:
    return await _ejecutar(repository.vincular_factura_contratista, id_orden, body.idCompra)
