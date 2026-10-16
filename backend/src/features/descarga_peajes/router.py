"""API de la descarga de peajes (037). El POST lo bloquea el middleware
global para el rol `Lectura` (403). Nunca expone credenciales."""

from __future__ import annotations

import ntpath

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from src.features.auth.repository import get_usuario_por_id
from src.features.descarga_peajes import configuracion, repository, servicio
from src.features.descarga_peajes.schemas import (
    DocumentosPagina, Ejecucion, EjecucionDetalle, EjecucionEnCurso, EjecucionesPagina, EjecucionIniciada, Estado,
    PortalConfiguracion, ResumenContador, TareaSemanal,
)

router = APIRouter(prefix="/api/descarga-peajes", tags=["descarga-peajes"])

ESTADOS_DOCUMENTO = {"pendiente", "cargado_auto", "ya_cargado"}


def _con_nombre(doc: dict) -> dict:
    return {**doc, "nombreArchivo": ntpath.basename(doc["ruta"]) if doc.get("ruta") else None}


def _usuario(request: Request) -> str | None:
    payload = getattr(request.state, "usuario", None) or {}
    try:
        u = get_usuario_por_id(payload.get("idUsuario"))
        return (u or {}).get("NombreUsuario")
    except Exception:
        return None


@router.get("/estado", response_model=Estado)
def estado() -> Estado:
    en_curso = repository.ejecucion_en_curso()
    return Estado(
        portales=[PortalConfiguracion(portal=p, credenciales=configuracion.credenciales_configuradas(p))
                  for p in configuracion.CUENTAS],
        tarea=TareaSemanal(**configuracion.estado_tarea()),
        enCurso=EjecucionEnCurso(**{k: en_curso[k] for k in ("idEjecucion", "inicio", "origen")}) if en_curso else None,
    )


@router.post("/ejecuciones", status_code=202, response_model=EjecucionIniciada)
def iniciar(request: Request):
    id_ejecucion, id_en_curso = servicio.iniciar_en_segundo_plano(_usuario(request))
    if id_ejecucion is None:
        return JSONResponse(status_code=409, content={"detail": "Ya hay una descarga en curso", "idEjecucion": id_en_curso})
    return EjecucionIniciada(idEjecucion=id_ejecucion)


@router.get("/ejecuciones", response_model=EjecucionesPagina)
def listar_ejecuciones(limite: int = Query(20, ge=1, le=100), desde: int = Query(0, ge=0)) -> EjecucionesPagina:
    items, total = repository.listar_ejecuciones(limite, desde)
    return EjecucionesPagina(items=[Ejecucion(**i) for i in items], total=total)


@router.get("/ejecuciones/{id_ejecucion}", response_model=EjecucionDetalle)
def detalle_ejecucion(id_ejecucion: int) -> EjecucionDetalle:
    e = repository.obtener_ejecucion(id_ejecucion)
    if e is None:
        raise HTTPException(status_code=404, detail="Ejecución inexistente")
    return EjecucionDetalle(**{**e, "documentos": [_con_nombre(d) for d in e["documentos"]]})


@router.get("/documentos", response_model=DocumentosPagina)
def listar_documentos(estado: str | None = Query(None), limite: int = Query(50, ge=1, le=100),
                      desde: int = Query(0, ge=0)) -> DocumentosPagina:
    if estado is not None and estado not in ESTADOS_DOCUMENTO:
        raise HTTPException(status_code=400, detail="Estado inválido")
    repository.revalidar_pendientes()
    items, total = repository.listar_documentos(estado, limite, desde)
    return DocumentosPagina(items=[_con_nombre(d) for d in items], total=total)


@router.get("/resumen", response_model=ResumenContador)
def resumen() -> ResumenContador:
    repository.revalidar_pendientes()
    return ResumenContador(**repository.resumen())
