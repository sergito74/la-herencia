"""API de clasificación analítica ARCA; no escribe movimientos contables."""
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from src.features.cuentas_corrientes import arca, arca_documentos, arca_fiscal
from src.features.revision_cuentas.router import _usuario_actual

router = APIRouter(prefix="/api/arca", tags=["arca"])
Monto = Annotated[Decimal, Field(ge=0, max_digits=19, decimal_places=4)]


@router.get('/fiscal')
async def fiscal_listar(impuesto: str | None = Query(None, max_length=20)):
    try:
        return await run_in_threadpool(arca_fiscal.listar, impuesto)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get('/fiscal/{ident}')
async def fiscal_detalle(ident: int):
    try:
        return await run_in_threadpool(arca_fiscal.detalle, ident)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get('/fiscal/{ident}/archivo')
async def fiscal_archivo(ident: int):
    try:
        ruta = await run_in_threadpool(arca_fiscal.archivo, ident)
        return FileResponse(ruta, media_type='application/pdf', filename=ruta.name, content_disposition_type='inline')
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


class Parte(BaseModel):
    subcuenta: str
    deuda: Monto = Decimal(0)
    credito: Monto = Decimal(0)

    @field_validator("subcuenta")
    @classmethod
    def clave_valida(cls, value):
        if value not in arca.CATALOGO:
            raise ValueError("Subcuenta desconocida")
        return value


class Clasificacion(BaseModel):
    origen: str = Field(min_length=1, max_length=80)
    idOrigen: int = Field(gt=0)
    version: int = Field(ge=0)
    partes: list[Parte] = Field(max_length=len(arca.CATALOGO))
    motivo: str = Field(min_length=3, max_length=500)

    @field_validator("motivo")
    @classmethod
    def motivo_valido(cls, value):
        if len(value.strip()) < 3:
            raise ValueError("Indicá el motivo de la clasificación")
        return value.strip()


class Resumen(BaseModel):
    clave: str
    nombre: str
    deuda: Decimal
    credito: Decimal
    saldo: Decimal
    cantidad: int


class Documento(BaseModel):
    idDocumento: int
    tipo: str
    periodo: str | None = None
    numero: str | None = None
    esOriginal: bool


class Movimiento(BaseModel):
    fecha: date
    documento: str | None
    numeroDocumento: str | None
    origen: str
    idOrigen: int
    detalle: str
    deuda: Decimal
    credito: Decimal
    deudaOriginal: Decimal
    creditoOriginal: Decimal
    saldo: Decimal
    partes: list[Parte]
    version: int
    manual: bool
    revisarReparto: bool
    motivo: str | None
    documentos: list[Documento] = Field(default_factory=list)


class Cuenta(BaseModel):
    resumen: list[Resumen]
    saldoTotal: Decimal
    apertura: Decimal
    saldoSeleccion: Decimal
    items: list[Movimiento]
    total: int
    page: int
    pageSize: int


@router.get("/cuenta", response_model=Cuenta)
async def cuenta(fechaDesde: date | None = None, fechaHasta: date | None = None,
                 subcuenta: str | None = None, page: int = Query(1, ge=1),
                 pageSize: int = Query(50, ge=1, le=200)):
    try:
        return await run_in_threadpool(arca.cuenta, fechaDesde, fechaHasta, subcuenta, page, pageSize)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/historial")
async def historial(origen: str = Query(min_length=1, max_length=80), idOrigen: int = Query(gt=0)):
    return await run_in_threadpool(arca.read,
        "SELECT TOP (100) IdClasificacion version,Reparto reparto,Motivo motivo,Usuario usuario,Fecha fecha "
        "FROM dbo.ArcaClasificaciones WHERE Origen=? AND IdOrigen=? ORDER BY IdClasificacion DESC", (origen, idOrigen))


@router.get("/documentos/{id_documento}/archivo")
async def documento(id_documento: int):
    try:
        ruta = await run_in_threadpool(arca_documentos.archivo, id_documento)
        return FileResponse(ruta, media_type="application/pdf", filename=ruta.name, content_disposition_type="inline")
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.put("/clasificacion")
async def guardar(body: Clasificacion, request: Request):
    try:
        usuario = await run_in_threadpool(_usuario_actual, request)
        return await run_in_threadpool(arca.guardar, body.origen, body.idOrigen, body.version,
                                      [p.model_dump() for p in body.partes], body.motivo, usuario)
    except arca.ConflictoVersion as exc:
        raise HTTPException(409, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
