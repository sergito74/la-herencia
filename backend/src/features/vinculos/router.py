"""031 — /api/integridad-vinculos: control de integridad y lotes de
corrección (ver specs/031-integridad-vinculos/contracts/api.md)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_one
from src.features.vinculos import control, fuente, lotes

router = APIRouter(prefix="/api/integridad-vinculos", tags=["integridad-vinculos"])


class Eleccion(BaseModel):
    idItem: int
    candidato: int


class ActualizarItemsRequest(BaseModel):
    incluir: list[int] = []
    excluir: list[int] = []
    elegir: list[Eleccion] = []
    incluirGrupo: str | None = None
    excluirGrupo: str | None = None


def _usuario(request: Request) -> str:
    payload = getattr(request.state, "usuario", None)
    if not payload:
        return "desconocido"
    fila = fetch_one("SELECT NombreUsuario AS n FROM dbo.AuthUsuarios WHERE IdUsuario = ?", (payload["idUsuario"],))
    return fila["n"] if fila else "desconocido"


def _exigir_admin(request: Request) -> None:
    payload = getattr(request.state, "usuario", None) or {}
    if payload.get("rol") != "Administrador":
        raise HTTPException(status_code=403, detail="Solo un Administrador puede modificar lotes de corrección.")


def _control(categoria: str | None) -> dict:
    raw = fuente.cargar()
    hallazgos = control.hallazgos(raw)
    documentos = raw["documentos"]
    for h in hallazgos:
        d = documentos.get((h["tipoDocumento"], h["idDocumento"])) if h["tipoDocumento"] else None
        h["fechaDocumento"] = d["fecha"].date().isoformat() if d and isinstance(d.get("fecha"), datetime) else None
        h["idContacto"] = d.get("idContacto") if d else None
    return {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "totales": control.totales(hallazgos),
        "hallazgos": [h for h in hallazgos if categoria is None or h["categoria"] == categoria],
    }


@router.get("/control")
async def control_endpoint(categoria: str | None = Query(default=None)) -> dict:
    if categoria is not None and categoria not in control.CATEGORIAS:
        raise HTTPException(status_code=422, detail=f"Categoría inválida: {categoria}")
    return await run_in_threadpool(_control, categoria)


@router.get("/lotes")
async def listar_lotes_endpoint() -> list[dict]:
    return await run_in_threadpool(lotes.listar_lotes)


@router.post("/lotes", status_code=201)
async def crear_lote_endpoint(request: Request) -> dict:
    _exigir_admin(request)
    return await run_in_threadpool(lotes.crear_lote, _usuario(request))


@router.get("/lotes/{id_lote}")
async def obtener_lote_endpoint(id_lote: int, grupo: str | None = None, pagina: int = Query(default=1, ge=1),
                                tamanio: int = Query(default=100, ge=1, le=500)) -> dict:
    try:
        return await run_in_threadpool(lotes.obtener, id_lote, grupo, pagina, tamanio)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"No existe el lote {id_lote}") from exc


async def _escritura(fn, *args):
    try:
        return await run_in_threadpool(fn, *args)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No existe el lote") from exc
    except lotes.LoteConflicto as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/lotes/{id_lote}/items")
async def actualizar_items_endpoint(id_lote: int, body: ActualizarItemsRequest, request: Request) -> dict:
    _exigir_admin(request)
    return await _escritura(lotes.actualizar_items, id_lote, body.incluir, body.excluir,
                            [e.model_dump() for e in body.elegir], body.incluirGrupo, body.excluirGrupo)


@router.post("/lotes/{id_lote}/aplicar")
async def aplicar_endpoint(id_lote: int, request: Request) -> dict:
    _exigir_admin(request)
    return await _escritura(lotes.aplicar, id_lote, _usuario(request))


@router.post("/lotes/{id_lote}/revertir")
async def revertir_endpoint(id_lote: int, request: Request) -> dict:
    _exigir_admin(request)
    return await _escritura(lotes.revertir, id_lote, _usuario(request))


@router.post("/lotes/{id_lote}/descartar")
async def descartar_endpoint(id_lote: int, request: Request) -> dict:
    _exigir_admin(request)
    await _escritura(lotes.descartar, id_lote)
    return {"ok": True}
