"""Cajas 038: lectura compatible 027 y operaciones auditadas con permisos 016."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
    Response,
    Header,
    UploadFile,
    File,
    Form,
)
from uuid import UUID
from datetime import date
from starlette.concurrency import run_in_threadpool

from src.db.pagination import normalize_pagination
from src.features.cajas_efectivo import repository
from src.features.cajas_efectivo.schemas import (
    MovimientoCajaEfectivo,
    MovimientosCajaResponse,
    SaldoCaja,
)
from src.features.cajas_efectivo.schemas import OperacionCaja, ConfirmarOperacion, AnularOperacion, ConciliarBancoCaja
from src.features.cajas_efectivo import operaciones, service
from src.features.cajas_efectivo import arqueos
from src.features.cajas_efectivo import importacion
from src.db.connection import fetch_one

router = APIRouter(prefix="/api/cajas-efectivo", tags=["cajas-efectivo"])

# Mapeo slug de URL -> valor guardado en MovimientosCajaEfectivo.Caja
# (contracts/api.md).
_SLUG_A_CAJA = {
    "giamigli-sa": "GiamigliSA",
    "giamigli-dolares": "GiamigliUSD",
    "campo-chica": "CampoChica",
    "condominio-lsc": "CondominioLSC",
}


def _resolver_caja(slug: str) -> str:
    caja = _SLUG_A_CAJA.get(slug)
    if caja is None:
        raise HTTPException(status_code=404, detail=f"Caja desconocida: {slug!r}")
    return caja


def _usuario(request: Request):
    payload = getattr(request.state, "usuario", None)
    if not payload:
        raise HTTPException(401, "Se requiere sesión.")
    if payload.get("rol") == "Lectura":
        raise HTTPException(403, "Tu usuario tiene permiso de solo lectura.")
    row = fetch_one(
        "SELECT NombreUsuario nombre FROM dbo.AuthUsuarios WHERE IdUsuario=?",
        (payload["idUsuario"],),
    )
    if not row:
        raise HTTPException(401, "Sesión inválida.")
    return row["nombre"]


async def _ejecutar(fn, *args):
    try:
        result = await run_in_threadpool(fn, *args)
        if fn in (
            service.crear,
            service.anular,
            service.conciliar_banco,
            arqueos.guardar,
            arqueos.confirmar,
            importacion.confirmar,
        ):
            # Called only after the outer transaction committed successfully.
            from src.features.auditoria_cuentas.bimonetaria import invalidar
            from src.features.revision_cuentas.cache import invalidar as invalidar_revision

            invalidar()
            invalidar_revision()
        return result
    except service.NoExisteCaja as exc:
        raise HTTPException(404, str(exc)) from exc
    except service.ConflictoCaja as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            500, "No se pudo completar la operación. No se guardaron cambios parciales."
        ) from exc


@router.post("/operaciones/previsualizar")
async def previsualizar(body: OperacionCaja, request: Request):
    await run_in_threadpool(_usuario, request)
    result = await _ejecutar(service.previsualizar, body)
    # Encode Decimal explicitly, including nested valuation context.
    import json

    return json.loads(operaciones.dumps(result))


@router.post("/operaciones")
async def crear(
    body: ConfirmarOperacion,
    request: Request,
    response: Response,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
):
    user = await run_in_threadpool(_usuario, request)
    result, created = await _ejecutar(service.crear, body, idempotency_key, user)
    response.status_code = 201 if created else 200
    return result


@router.get("/operaciones/{id_operacion}")
async def detalle(id_operacion: int):
    result = await _ejecutar(operaciones.detail, id_operacion)
    if result is None:
        raise HTTPException(404, "Operación inexistente.")
    try:
        result['anulacion'] = await _ejecutar(service.previsualizar_anulacion, id_operacion)
    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        result['anulacion'] = {'bloqueo': exc.detail}
    return result


@router.get("/particulares/asientos")
async def asientos_particulares(
    idContacto: int = Query(gt=0), fecha: date = Query(), importe: str = Query()
):
    from decimal import Decimal, InvalidOperation

    try:
        amount = Decimal(importe)
        if not amount.is_finite() or amount <= 0:
            raise InvalidOperation()
    except InvalidOperation as exc:
        raise HTTPException(422, "Importe inválido.") from exc
    rows = await _ejecutar(
        operaciones.read,
        "SELECT TOP 50 IdPagoEfectivo id, Caja caja, Cuenta cuenta, Fecha fecha "
        "FROM dbo.vw_PagosEfectivoVigentes WHERE IdContacto=? AND Caja LIKE ? "
        "AND CAST(Fecha AS date)=? AND [Importe imputado]=? ORDER BY IdPagoEfectivo",
        (idContacto, "Particular%", fecha, -amount),
    )
    return {"items": rows}


@router.post("/operaciones/{id_operacion}/anular")
async def anular(id_operacion: int, body: AnularOperacion, request: Request):
    user = await run_in_threadpool(_usuario, request)
    return await _ejecutar(service.anular, id_operacion, body, user)


@router.get("/{caja}/arqueos")
async def listar_arqueos(
    caja: str, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=200)
):
    _resolver_caja(caja)
    return await _ejecutar(arqueos.listar, caja, page, pageSize)


@router.post("/{caja}/arqueos", status_code=201)
async def crear_arqueo(caja: str, body: arqueos.Recuento, request: Request):
    _resolver_caja(caja)
    user = await run_in_threadpool(_usuario, request)
    return await _ejecutar(arqueos.guardar, caja, body, user)


@router.put("/{caja}/arqueos/{id_arqueo}")
async def editar_arqueo(caja: str, id_arqueo: int, body: arqueos.Recuento, request: Request):
    _resolver_caja(caja)
    user = await run_in_threadpool(_usuario, request)
    return await _ejecutar(arqueos.guardar, caja, body, user, id_arqueo)


@router.post("/{caja}/arqueos/{id_arqueo}/confirmar")
async def confirmar_arqueo(caja: str, id_arqueo: int, body: arqueos.Confirmacion, request: Request):
    _resolver_caja(caja)
    user = await run_in_threadpool(_usuario, request)
    return await _ejecutar(arqueos.confirmar, caja, id_arqueo, body, user)


@router.post("/importaciones/previsualizar")
async def preview_import(
    request: Request,
    archivo: UploadFile = File(...),
    libro: str = Form(...),
    fechaCorte: date = Form(...),
):
    user = await run_in_threadpool(_usuario, request)
    if not (archivo.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(422, "Seleccioná un archivo .xlsx sin macros.")
    try:
        content = await archivo.read(10 * 1024 * 1024 + 1)
        return await _ejecutar(importacion.previsualizar, content, libro, fechaCorte, user)
    finally:
        await archivo.close()


@router.get("/importaciones/{id_lote}")
async def detalle_import(id_lote: int):
    return await _ejecutar(importacion.detalle, id_lote)


@router.post("/importaciones/{id_lote}/confirmar")
async def confirmar_import(id_lote: int, body: importacion.ConfirmarImportacion, request: Request):
    user = await run_in_threadpool(_usuario, request)
    return await _ejecutar(importacion.confirmar, id_lote, body, user)


@router.get("/{caja}/saldo", response_model=SaldoCaja)
async def saldo_caja(caja: str, detalleSaldo: bool = False) -> SaldoCaja:
    caja_real = _resolver_caja(caja)
    if detalleSaldo:
        row = await _ejecutar(operaciones.one,
                             'SELECT ISNULL(SUM(Importe),0) saldo FROM dbo.vw_MovimientosCajaEfectivoOperativos '
                             'WHERE Caja=? AND Anulada=0', (caja_real,))
        latest = await _ejecutar(arqueos.listar, caja, 1, 1)
        return SaldoCaja(caja=caja, saldo=float(row['saldo']), saldoDecimal=f"{row['saldo']:.2f}",
                         ultimoArqueo=latest['items'][0] if latest['items'] else None,
                         cobertura='Neto de movimientos documentados con Giamigli; no representa efectivo físico ni saldo de la cuenta del socio.'
                         if caja == 'condominio-lsc' else ('Tenencia de billetes en dólares estadounidenses.' if caja == 'giamigli-dolares' else 'Caja de Giamigli en pesos.'))
    saldo = await run_in_threadpool(repository.calcular_saldo, caja_real)
    return SaldoCaja(caja=caja, saldo=saldo, saldoDecimal=f'{saldo:.2f}')


@router.get("/{caja}/movimientos", response_model=MovimientosCajaResponse)
async def movimientos_caja(
    caja: str,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
    desde: date | None = None,
    hasta: date | None = None,
    tipo: str | None = None,
    idContacto: int | None = Query(None, gt=0),
    idSocio: int | None = Query(None, gt=0),
    incluirAnuladas: bool = False,
    detalleSaldo: bool = False,
) -> MovimientosCajaResponse:
    caja_real = _resolver_caja(caja)
    norm_page, norm_page_size = normalize_pagination(page, pageSize)
    if desde and hasta and desde > hasta:
        raise HTTPException(422, "El inicio supera el fin del período.")
    if detalleSaldo or any((desde, hasta, tipo, idContacto, idSocio, incluirAnuladas)):
        result = await _ejecutar(
            repository.consultar_movimientos,
            caja_real,
            norm_page,
            norm_page_size,
            desde,
            hasta,
            tipo,
            idContacto,
            idSocio,
            incluirAnuladas,
        )
        return MovimientosCajaResponse(**result)
    items, total = await run_in_threadpool(
        repository.listar_movimientos, caja_real, norm_page, norm_page_size
    )
    return MovimientosCajaResponse(
        items=[MovimientoCajaEfectivo(**item) for item in items],
        page=norm_page,
        pageSize=norm_page_size,
        total=total,
    )


@router.post("/operaciones/{id_operacion}/conciliar-banco")
async def conciliar_banco(id_operacion: int, body: ConciliarBancoCaja, request: Request):
    user = await run_in_threadpool(_usuario, request)
    return await _ejecutar(service.conciliar_banco, id_operacion, body, user)


@router.get("/{caja}/transferencias-pendientes")
async def transferencias_pendientes(caja: str, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=200)):
    _resolver_caja(caja)
    return await _ejecutar(operaciones.transferencias_pendientes, caja, page, pageSize)
