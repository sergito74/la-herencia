"""Revisión sistemática de cuentas — 036 (ficha por cuenta, etapas, detector de pagos sin factura, colas y lotes)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_all, fetch_one
from src.features.revision_cuentas import archivos, colas, datos, detector, evidencia, fichas, lotes, tablero
from src.features.revision_cuentas.schemas import (
    CambioCorte,
    ArchivosIncompletos,
    CambioFicha,
    ColaCuentas,
    Corte,
    FotoTablero,
    ListaFotos,
    Pregunta,
    Tablero,
    Decision,
    Ficha,
    Lote,
    PagoSinFactura,
    PagosSinFacturaCuenta,
    PedidoDecision,
    PedidoInventario,
    PedidoMarca,
    PedidoSimularLote,
    PedidoTildar,
    ReglaLote,
    NuevoSaldoExterno,
    SaldoExterno,
)

router = APIRouter(prefix="/api/revision-cuentas", tags=["revision-cuentas"])


def _usuario_actual(request: Request) -> str:
    """Mismo criterio que `auditoria_cuentas/router.py`: el nombre del usuario de la sesión."""
    payload = getattr(request.state, "usuario", None)
    if not payload:
        return "desconocido"
    fila = fetch_one("SELECT NombreUsuario AS n FROM dbo.AuthUsuarios WHERE IdUsuario = ?", (payload["idUsuario"],))
    return fila["n"] if fila else "desconocido"


# ---- Corte

@router.get("/corte", response_model=Corte)
async def obtener_corte() -> dict:
    corte = await run_in_threadpool(fichas.corte_vigente)
    if corte is None:
        raise HTTPException(status_code=404, detail="Todavía no hay un corte definido")
    return corte


@router.put("/corte", response_model=Corte)
async def cambiar_corte(body: CambioCorte, request: Request) -> dict:
    """Crea una fila nueva con el corte; el rol de solo lectura lo rechaza el middleware global."""
    usuario = _usuario_actual(request)
    try:
        return await run_in_threadpool(fichas.fijar_corte, body.corte, body.motivo, usuario)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---- Pagos sin factura (detector)

def _corte_o_404() -> date:
    corte = fichas.corte_vigente()
    if corte is None:
        raise HTTPException(status_code=404, detail="Todavía no hay un corte definido")
    return corte["corte"]


def _detectar_cuenta(id_contacto: int, corte: date) -> tuple[list[dict], dict, dict]:
    """Movimientos de la cuenta hasta el corte, resultado del detector y marcas vigentes (solo lectura)."""
    movimientos = datos.movimientos_de_cuenta(id_contacto, corte)
    if not movimientos:
        raise HTTPException(status_code=404, detail="La cuenta no existe o no tiene movimientos hasta el corte")
    return movimientos, detector.detectar(movimientos), evidencia.leer_marcas(id_contacto)


def _con_marca(pago: dict, marcas: dict) -> dict:
    return {**pago, "marca": marcas.get((pago["medio"], pago["idMovimiento"]))}


@router.get("/cuentas/{id_contacto}/pagos-sin-factura", response_model=PagosSinFacturaCuenta)
async def pagos_sin_factura(id_contacto: int, desde: date | None = Query(default=None), incluirMarcados: bool = Query(default=True)) -> dict:
    corte = _corte_o_404()
    _, resultado, marcas = await run_in_threadpool(_detectar_cuenta, id_contacto, corte)
    pagos = [_con_marca(p, marcas) for p in resultado["pagos"] if desde is None or p["fecha"] >= desde]
    if not incluirMarcados:
        pagos = [p for p in pagos if p["marca"] is None or p["marca"]["estado"] == "pendiente"]
    return {"idContacto": id_contacto, "corte": corte, "consistencia": resultado["consistencia"], "pagos": pagos,
            "facturasSinPago": resultado["facturasSinPago"]}


@router.put("/cuentas/{id_contacto}/pagos-sin-factura/{medio}/{id_movimiento}", response_model=PagoSinFactura)
async def marcar_pago_sin_factura(id_contacto: int, medio: str, id_movimiento: int, body: PedidoMarca, request: Request) -> dict:
    """Marca un pago sin factura; el rol de solo lectura lo rechaza el middleware global."""
    corte = _corte_o_404()
    todos = await run_in_threadpool(datos.movimientos_de_cuenta, id_contacto)
    if not any(datos.medio_de_origen(m["origen"]) == medio and m["idOrigen"] == id_movimiento for m in todos):
        raise HTTPException(status_code=404, detail="El movimiento no existe en esta cuenta")
    try:
        await run_in_threadpool(evidencia.validar_marca, id_contacto, body.estado, body.nota, body.idCompra, body.fuenteRespaldo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _, resultado, marcas = await run_in_threadpool(_detectar_cuenta, id_contacto, corte)
    pago = next((p for p in resultado["pagos"] if p["medio"] == medio and p["idMovimiento"] == id_movimiento), None)
    if pago is None:
        raise HTTPException(status_code=409, detail="El movimiento tiene una factura que lo respalda: no es un pago sin factura")
    marca = await run_in_threadpool(evidencia.guardar_marca, id_contacto, medio, id_movimiento, body.estado, body.idCompra,
                                    body.fuenteRespaldo, body.nota, _usuario_actual(request))
    return {**pago, "marca": marca}


# ---- Ficha de la cuenta

def _error(exc: fichas.FichaError) -> JSONResponse:
    """Error de negocio con su código; el detalle (por ejemplo los criterios que faltan) viaja junto al mensaje."""
    return JSONResponse(status_code=exc.codigo, content={"detail": exc.mensaje, **jsonable_encoder(exc.detalle)})


@router.get("/cuentas/{id_contacto}/ficha", response_model=Ficha)
async def ficha(id_contacto: int):
    """Ficha calculada de la cuenta (solo lectura: no crea la fila hasta que alguien cambia algo)."""
    try:
        return await run_in_threadpool(fichas.calcular_ficha, id_contacto)
    except fichas.FichaError as exc:
        return _error(exc)


@router.put("/cuentas/{id_contacto}/ficha", response_model=Ficha)
async def cambiar_ficha(id_contacto: int, body: CambioFicha, request: Request):
    """Cambia el estado manual de la ficha; el rol de solo lectura lo rechaza el middleware global."""
    usuario = _usuario_actual(request)
    try:
        return await run_in_threadpool(fichas.cambiar_estado, id_contacto, body.model_dump(), usuario)
    except fichas.FichaError as exc:
        return _error(exc)


@router.put("/cuentas/{id_contacto}/ficha/inventario", response_model=Ficha)
async def confirmar_inventario(id_contacto: int, body: PedidoInventario, request: Request):
    usuario = _usuario_actual(request)
    try:
        return await run_in_threadpool(fichas.confirmar_inventario, id_contacto, [f.model_dump() for f in body.fuentes], usuario)
    except fichas.FichaError as exc:
        return _error(exc)


# ---- Decisiones

@router.get("/cuentas/{id_contacto}/decisiones", response_model=list[Decision])
async def decisiones(id_contacto: int) -> list[dict]:
    return await run_in_threadpool(fichas.listar_decisiones, id_contacto)


@router.post("/cuentas/{id_contacto}/decisiones", response_model=Decision, status_code=201)
async def registrar_decision(id_contacto: int, body: PedidoDecision, request: Request):
    usuario = _usuario_actual(request)
    try:
        return await run_in_threadpool(fichas.registrar_decision, id_contacto, body.tipo, body.texto, body.evidencia, usuario)
    except fichas.FichaError as exc:
        return _error(exc)


# ---- Colas y lotes

def _error_de_lote(exc: Exception) -> JSONResponse:
    """Traduce los errores de negocio de lotes, fichas, correcciones y FIFO a su código HTTP."""
    if isinstance(exc, lotes.LoteError):
        return JSONResponse(status_code=exc.codigo, content={"detail": exc.mensaje})
    if isinstance(exc, fichas.FichaError):
        return _error(exc)
    codigo = getattr(exc, "codigo", None)
    if isinstance(codigo, int):                                   # CorreccionError de la 035
        return JSONResponse(status_code=codigo, content={"detail": str(exc)})
    nombre = type(exc).__name__
    if nombre in ("Conflicto", "RequiereConfirmacion"):           # errores del motor FIFO (032)
        return JSONResponse(status_code=409 if nombre == "Conflicto" else 422, content={"detail": str(exc)})
    raise exc


@router.get("/colas/{cola}", response_model=ColaCuentas)
async def cuentas_de_la_cola(cola: str, pagina: int = Query(default=1, ge=1), tamano: int = Query(default=100, ge=1, le=100), refrescar: bool = Query(default=False)):
    """Cuentas de una cola, de las más fáciles a las más complejas (menos movimientos primero; a igual cantidad, menor importe)."""
    if cola not in colas.COLAS:
        raise HTTPException(status_code=404, detail="La cola no existe: usá una letra de la A a la I")
    try:
        _, contextos = await run_in_threadpool(fichas.contextos_de_todas, None, refrescar)
    except fichas.FichaError as exc:
        return _error(exc)
    de_la_cola = colas.orden_de_dificultad([r for r in fichas.resumenes(contextos) if r["cola"] == cola])
    inicio = (pagina - 1) * tamano
    return {"cola": cola, "total": len(de_la_cola), "pagina": pagina, "cuentas": de_la_cola[inicio:inicio + tamano]}


@router.get("/reglas", response_model=list[ReglaLote])
async def reglas_de_lote() -> list[dict]:
    return lotes.reglas_disponibles()


@router.post("/lotes/simular", response_model=Lote, status_code=201)
async def simular_lote(body: PedidoSimularLote, request: Request):
    """Crea un lote simulado (no cambia nada). Con la regla FIFO puede tardar: recalcula las cuentas de la cola B."""
    usuario = _usuario_actual(request)
    try:
        return await run_in_threadpool(lotes.simular, body.cola, body.regla, usuario)
    except Exception as exc:
        return _error_de_lote(exc)


@router.put("/lotes/{id_correccion}/cuentas", response_model=Lote)
async def tildar_cuentas_del_lote(id_correccion: int, body: PedidoTildar):
    try:
        return await run_in_threadpool(lotes.tildar, id_correccion, body.idsContacto, body.tildarTodas)
    except Exception as exc:
        return _error_de_lote(exc)


@router.post("/lotes/{id_correccion}/aplicar", response_model=Lote)
async def aplicar_lote(id_correccion: int, request: Request):
    usuario = _usuario_actual(request)
    try:
        return await run_in_threadpool(lotes.aplicar, id_correccion, usuario)
    except Exception as exc:
        return _error_de_lote(exc)


@router.post("/lotes/{id_correccion}/revertir", response_model=Lote)
async def revertir_lote(id_correccion: int, request: Request):
    usuario = _usuario_actual(request)
    try:
        return await run_in_threadpool(lotes.revertir, id_correccion, usuario)
    except Exception as exc:
        return _error_de_lote(exc)


@router.get("/lotes/{id_correccion}", response_model=Lote)
async def ver_lote(id_correccion: int):
    try:
        return await run_in_threadpool(lotes.obtener, id_correccion)
    except Exception as exc:
        return _error_de_lote(exc)


@router.delete("/lotes/{id_correccion}", status_code=204)
async def descartar_lote(id_correccion: int):
    try:
        await run_in_threadpool(lotes.descartar, id_correccion)
    except Exception as exc:
        return _error_de_lote(exc)


# ---- Evidencia externa: saldos del proveedor, el banco o la tarjeta

def _saldos_externos_de(id_contacto: int) -> list[dict]:
    from src.features.auditoria_cuentas import parametros

    umbral = float(parametros.obtener().get("umbralPesos", evidencia.UMBRAL_PESOS))
    return evidencia.listar_saldos_externos(id_contacto, lambda f: datos.saldo_al_corte(id_contacto, f), umbral)


@router.get("/cuentas/{id_contacto}/saldos-externos", response_model=list[SaldoExterno])
async def saldos_externos(id_contacto: int) -> list[dict]:
    """Saldos externos cargados, con la diferencia contra el saldo de la cuenta a esa fecha (mismo signo: positivo a favor nuestro)."""
    return await run_in_threadpool(_saldos_externos_de, id_contacto)


@router.post("/cuentas/{id_contacto}/saldos-externos", response_model=SaldoExterno, status_code=201)
async def cargar_saldo_externo(id_contacto: int, body: NuevoSaldoExterno, request: Request):
    """Carga un saldo externo. No accede a ningún portal: lo informa una persona con la fecha y la fuente."""
    usuario = _usuario_actual(request)
    try:
        evidencia.validar_saldo_externo(body.fechaSaldo, body.fuente, body.nota, body.moneda)
        id_saldo = await run_in_threadpool(evidencia.crear_saldo_externo, id_contacto, body.fechaSaldo, body.saldo, body.moneda, body.fuente,
                                           body.referencia, body.nota, usuario)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    cargados = await run_in_threadpool(_saldos_externos_de, id_contacto)
    return next(s for s in cargados if s["idSaldoExterno"] == id_saldo)


@router.delete("/cuentas/{id_contacto}/saldos-externos/{id_saldo_externo}", status_code=204)
async def anular_saldo_externo(id_contacto: int, id_saldo_externo: int, request: Request):
    usuario = _usuario_actual(request)
    if not await run_in_threadpool(evidencia.anular_saldo_externo, id_contacto, id_saldo_externo, usuario):
        raise HTTPException(status_code=404, detail="El saldo externo no existe en esta cuenta")


# ---- Archivos de comprobantes (solo lectura)

@router.get("/archivos/incompletos", response_model=ArchivosIncompletos)
async def archivos_incompletos(periodo: str | None = Query(default=None), estado: str | None = Query(default=None),
                               pagina: int = Query(default=1, ge=1), tamano: int = Query(default=50, ge=1, le=200)) -> dict:
    """Archivos incompletos o por mirar de las carpetas de compras y si su comprobante está cargado. No modifica ningún archivo.

    La raíz de las carpetas la define el backend; el cliente solo elige el período fiscal (`04 AAAA - 03 AAAA+1`).
    """
    try:
        return await run_in_threadpool(archivos.revisar, periodo, estado, pagina, tamano)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---- Tablero, fotos semanales y preguntas

@router.get("/tablero", response_model=Tablero)
async def ver_tablero(request: Request, corte: date | None = Query(default=None), refrescar: bool = Query(default=False)):
    """Tablero de colas por etapas en vivo. Al abrirlo crea la foto de la semana (lunes) si todavía no existe, y la compara con la anterior."""
    try:
        return await run_in_threadpool(tablero.tablero, corte, refrescar, "sistema")
    except fichas.FichaError as exc:
        return _error(exc)


@router.get("/tablero/fotos", response_model=ListaFotos)
async def fotos_del_tablero(pagina: int = Query(default=1, ge=1), tamano: int = Query(default=20, ge=1, le=100)) -> dict:
    return await run_in_threadpool(tablero.listar_fotos, pagina, tamano)


@router.post("/tablero/fotos", response_model=FotoTablero, status_code=201)
async def crear_foto_del_tablero(request: Request):
    """Crea la foto de la semana actual a pedido (409 si ya existe: el tablero la crea solo al abrirse)."""
    usuario = _usuario_actual(request)
    try:
        return await run_in_threadpool(tablero.foto_manual, usuario)
    except tablero.TableroError as exc:
        return JSONResponse(status_code=exc.codigo, content={"detail": exc.mensaje})
    except fichas.FichaError as exc:
        return _error(exc)


@router.get("/preguntas", response_model=list[Pregunta])
async def preguntas_bloqueantes(refrescar: bool = Query(default=False)):
    """Preguntas que bloquean cuentas (una por cuenta), en el mismo orden de las colas."""
    try:
        return await run_in_threadpool(tablero.preguntas, refrescar)
    except fichas.FichaError as exc:
        return _error(exc)
