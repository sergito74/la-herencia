"""API de la descarga de peajes (037), desde 042 sobre la Bóveda de portales.

Conserva el permiso de 037 (sesión; el middleware bloquea el POST al rol
`Lectura`) y **no** exige Administrador: es la vista de Compras de los 4
portales de peaje. Lee corridas y documentos de las tablas de la bóveda y
dispara las corridas con `boveda.servicio`. Nunca expone credenciales,
autorizaciones editables ni programación (contracts/api.md de 042,
"Compatibilidad 037").
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from src.features.boveda import repository as boveda
from src.features.boveda import servicio
from src.features.boveda.router import con_nombre, corrida_iso, iso, usuario_actual

router = APIRouter(prefix="/api/descarga-peajes", tags=["descarga-peajes"])

CONECTORES_PEAJE = ("telepeajeplus", "telepase", "ceamse", "aubasa")
ESTADOS_DOCUMENTO = {"pendiente", "cargado_auto", "ya_cargado"}


def _peajes() -> list[dict]:
    return [f for f in boveda.listar_portales() if f["codigoConector"] in CONECTORES_PEAJE]


def _ids() -> list[int]:
    return [f["idPortal"] for f in _peajes()] or [0]


@router.get("/estado")
def estado() -> dict:
    portales = [{
        "idPortal": f["idPortal"], "portal": f["nombre"],
        "credenciales": bool(f["claveConfigurada"]) and not f["credencialRechazada"],
        "autorizado": f["autFecha"] is not None,
        "proximaCorrida": None if f["suspendida"] else iso(f["proximaCorrida"]),
        "ultimaCorrida": {"estado": f["ucEstado"], "inicio": iso(f["ucInicio"])} if f["ucId"] else None,
    } for f in _peajes()]
    return {"portales": portales, "enCurso": any(f["ucEstado"] == "en_curso" for f in _peajes())}


@router.post("/ejecuciones", status_code=202)
def iniciar(request: Request):
    peajes = _peajes()
    if any(f["ucEstado"] == "en_curso" for f in peajes):
        return JSONResponse(status_code=409, content={"detail": "Ya hay una descarga en curso"})
    ids = [f["idPortal"] for f in peajes if f["autFecha"] is not None]
    if not ids:
        raise HTTPException(status_code=409, detail="Ningún portal de peaje tiene autorización vigente")
    servicio.correr_varios_en_segundo_plano(ids, usuario_actual(request))
    return {"portales": ids}


@router.get("/corridas")
def listar_corridas(limite: int = Query(20, ge=1, le=100), desde: int = Query(0, ge=0)) -> dict:
    filas, total = boveda.listar_corridas(None, limite, desde, portales=_ids())
    return {"items": [corrida_iso(c) for c in filas], "total": total}


@router.get("/documentos")
def listar_documentos(estado: str | None = Query(None), limite: int = Query(50, ge=1, le=100),
                      desde: int = Query(0, ge=0)) -> dict:
    if estado is not None and estado not in ESTADOS_DOCUMENTO:
        raise HTTPException(status_code=400, detail="Estado inválido")
    boveda.revalidar_pendientes()
    filas, total = boveda.listar_documentos(None, estado, limite, desde, portales=_ids())
    return {"items": [con_nombre(d) for d in filas], "total": total}


@router.get("/resumen")
def resumen() -> dict:
    boveda.revalidar_pendientes()
    r = boveda.resumen(_ids())
    return {"pendientes": r["pendientesCarga"], "portalesConError": r["conError"] + r["requiereIntervencion"]}
