"""Endpoints de Resultado y Costos de Cultivo (012). Módulo 100% de solo
lectura: ningún endpoint de este router escribe en `WC`."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from starlette.concurrency import run_in_threadpool

from src.features.resultado_cultivo import campania_actual, exportacion, formularios_access, resultado
from src.db.connection import fetch_all

router = APIRouter(prefix="/api/resultado-cultivo", tags=["resultado-cultivo"])


async def _ejecutar(fn, *args, **kwargs):
    """Errores de negocio (Campaña/Cultivo inexistente, etc.) → 404."""
    try:
        return await run_in_threadpool(fn, *args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


def _campanias() -> list[dict]:
    return fetch_all("SELECT IdCampaña AS idCampania, Campaña AS campania FROM dbo.Campañas ORDER BY Campaña DESC")


@router.get("/campanias")
async def campanias() -> dict:
    return {
        "campanias": await run_in_threadpool(_campanias),
        "campaniaActualId": await run_in_threadpool(campania_actual.campania_actual),
    }


@router.get("/access/cultivo/{id_cultivo}/campanias")
async def access_campanias(id_cultivo: int) -> list[dict]:
    return await run_in_threadpool(formularios_access.campanias_de_cultivo, id_cultivo)


@router.get("/access/costos")
async def access_costos(idCultivo: int, idCampania: int) -> dict:
    """Formulario FrmCostos de Access."""
    return await _ejecutar(formularios_access.formulario_costos, idCultivo, idCampania)


@router.get("/access/costos/detalle")
async def access_costos_detalle(idCultivo: int, idCampania: int, idRubro: int) -> list[dict]:
    return await _ejecutar(formularios_access.detalle_rubro, idCultivo, idCampania, idRubro)


@router.get("/access/resultados")
async def access_resultados(idCultivo: int, idCampania: int) -> dict:
    """Formulario FrmResultados de Access."""
    return await _ejecutar(formularios_access.formulario_resultados, idCultivo, idCampania)


@router.get("/campania/{id_campania}")
async def campania(id_campania: int) -> dict:
    return await _ejecutar(resultado.resultado_campania, id_campania)


@router.get("/campania/{id_campania}/cultivo/{id_cultivo}")
async def cultivo(id_campania: int, id_cultivo: int) -> dict:
    return await _ejecutar(resultado.resultado_cultivo, id_cultivo, id_campania)


@router.get("/campania/{id_campania}/cultivo/{id_cultivo}/costos")
async def costos_cultivo(id_campania: int, id_cultivo: int) -> list[dict]:
    await _ejecutar(resultado.resultado_cultivo, id_cultivo, id_campania)
    return await run_in_threadpool(resultado.detalle_costos, id_cultivo, id_campania)


@router.get("/campania/{id_campania}/exportar")
async def exportar_campania(id_campania: int) -> Response:
    contenido = await _ejecutar(exportacion.resultado_campania_xlsx, id_campania)
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="resultado-cultivo-{id_campania}.xlsx"'},
    )


@router.get("/campania/{id_campania}/cultivo/{id_cultivo}/exportar")
async def exportar_cultivo(id_campania: int, id_cultivo: int) -> Response:
    contenido = await _ejecutar(exportacion.resultado_cultivo_xlsx, id_cultivo, id_campania)
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="resultado-cultivo-{id_campania}-{id_cultivo}.xlsx"'},
    )
