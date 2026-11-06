"""Endpoints de Órdenes de Trabajo (011-ordenes-trabajo). Toda escritura va contra `WC`."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from src.features.ordenes import exportacion, repository, resultado, retiro_pdf
from src.features.ordenes.repository import RequiereConfirmacion
from src.features.ordenes.schemas import (
    HectareasIn,
    AnularIn,
    DevolucionIn,
    EjecutarIn,
    MaquinariaIn,
    OrdenIn,
    TipoLaborIn,
)
from src.features.planificacion import repository as planificacion_repository

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
        "planAgricola": await run_in_threadpool(planificacion_repository.listar),
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
    insumo: str | None = None,
    idTipoLabor: int | None = None,
    page: int = 1,
    pageSize: int = 25,
) -> dict:
    return await _ejecutar(
        repository.listar_ordenes, idContratista, idLote, idCultivo, idCampania, fechaDesde, fechaHasta, estado, max(page, 1), min(max(pageSize, 1), 200), insumo, idTipoLabor
    )


@router.get("/exportar")
async def exportar_ordenes(
    idContratista: int | None = None, idLote: int | None = None, idCultivo: int | None = None, idCampania: int | None = None,
    fechaDesde: date | None = None, fechaHasta: date | None = None, estado: str | None = None, insumo: str | None = None, idTipoLabor: int | None = None,
) -> Response:
    contenido = await _ejecutar(
        exportacion.ordenes_xlsx, idContratista=idContratista, idLote=idLote, idCultivo=idCultivo, idCampania=idCampania,
        fechaDesde=fechaDesde, fechaHasta=fechaHasta, estado=estado, insumo=insumo, idTipoLabor=idTipoLabor,
    )
    return Response(content=contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="ordenes-{date.today().isoformat()}.xlsx"'})


@router.get("/contratistas/sin-orden")
async def facturas_sin_orden(idContratista: int | None = None) -> list[dict]:
    """048 FR-008: facturas de labor de contratistas sin orden vinculada, con sus renglones."""
    from src.features.ordenes import documentos_contratista as dc
    return await run_in_threadpool(dc.sin_orden, idContratista)


@router.get("/contratistas/sin-orden/exportar")
async def exportar_facturas_sin_orden(idContratista: int | None = None) -> Response:
    contenido = await run_in_threadpool(exportacion.sin_orden_xlsx, idContratista)
    return Response(content=contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="facturas-sin-orden-{date.today().isoformat()}.xlsx"'})


@router.get("/{id_orden}/formulario-retiro/pdf")
async def formulario_retiro_pdf(id_orden: int) -> Response:
    contenido = await _ejecutar(retiro_pdf.formulario_retiro_pdf, id_orden)
    return Response(content=contenido, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="formulario-retiro-orden-{id_orden}.pdf"'})


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


@router.patch("/{id_orden}/fecha-ejecucion", status_code=204)
async def corregir_fecha_ejecucion(id_orden: int, body: EjecutarIn) -> None:
    await _ejecutar(repository.corregir_fecha_ejecucion, id_orden, body.fechaEjecucion)


@router.patch("/{id_orden}/hectareas")
async def corregir_hectareas(id_orden: int, body: HectareasIn, request: Request) -> dict:
    """Hectáreas realmente aplicadas por lote: rearma el reparto de insumos entre cultivos."""
    reparto = await _ejecutar(repository.corregir_hectareas, id_orden, {l.idLote: l.superficie for l in body.lotes},
                              _usuario(request))
    return {"repartoPorCultivo": reparto}


@router.get("/{id_orden}/reparto-cultivos")
async def reparto_cultivos(id_orden: int) -> dict:
    return {"repartoPorCultivo": await run_in_threadpool(repository.reparto_por_cultivo, id_orden)}


@router.post("/{id_orden}/anular", status_code=204)
async def anular_orden(id_orden: int, body: AnularIn, request: Request) -> None:
    await _ejecutar(repository.anular_orden, id_orden, body.motivo, _usuario(request))


@router.post("/{id_orden}/insumos/{id_orden_insumo}/devoluciones", status_code=201)
async def registrar_devolucion(id_orden: int, id_orden_insumo: int, body: DevolucionIn) -> dict:
    idx = await _ejecutar(repository.registrar_devolucion, id_orden_insumo, body.model_dump())
    return {"idDevolucion": idx}


@router.post("/{id_orden}/maquinaria", status_code=201)
async def agregar_maquinaria(id_orden: int, body: MaquinariaIn) -> dict:
    return await _ejecutar(repository.agregar_maquinaria, id_orden, body.model_dump())


# 048: la factura del contratista se vincula desde Compras (GET/PUT /api/compras/{id}/ordenes-trabajo); la orden
# solo muestra sus documentos (obtener_orden → facturasContratista).


def _usuario(request: Request) -> str:
    from src.features.imputacion.repository import nombre_usuario
    payload = getattr(request.state, "usuario", None)
    return (nombre_usuario(payload["idUsuario"]) if payload else None) or "sistema"
