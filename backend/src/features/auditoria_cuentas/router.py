"""Auditoría de cuentas corrientes de proveedores y clientes — 035."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from src.db.connection import fetch_all, fetch_one
import time

from src.features.cuentas_corrientes import origen_resolver
from src.features.auditoria_cuentas import ajustes, asignacion, bimonetaria, fifo_plan, clasificacion, conocidos, correcciones, datos, hallazgos as detectores, parametros, revision
from src.features.auditoria_cuentas.schemas import (
    AltaConocido,
    CambioRevision,
    PedidoTanda,
    PlanFifo,
    MovimientoSinContacto,
    PedidoAsignacion,
    MovimientosRevision,
    CorreccionCuenta,
    PedidoAnulacion,
    PedidoNotaAjuste,
    CuentaVecina,
    RevisionCuenta,
    CambioParametros,
    Conocido,
    CuentaAuditada,
    GrupoCuentas,
    Hallazgo,
    HallazgosCuenta,
    ParametrosAuditoria,
    ResumenAuditoria,
)

router = APIRouter(prefix="/api/auditoria-cuentas", tags=["auditoria-cuentas"])

NOMBRES_COMPONENTE = {
    "fuentes-no-contadas": "Movimientos de fuentes que el Access no contaba en la cuenta corriente",
    "reasignacion": "Movimientos reasignados a otro contacto",
    "datos-posteriores": "Movimientos cargados después de la referencia del Access",
    "correccion-importe": "Movimientos con otro importe que en el Access (corrección)",
    "otros": "Diferencia sin explicar",
}


def _usuario_actual(request: Request) -> str:
    payload = getattr(request.state, "usuario", None)
    if not payload:
        return "desconocido"
    fila = fetch_one("SELECT NombreUsuario AS n FROM dbo.AuthUsuarios WHERE IdUsuario = ?", (payload["idUsuario"],))
    return fila["n"] if fila else "desconocido"


_CACHE: dict = {"t": 0.0, "v": None}
TTL_SEGUNDOS = 600  # los cambios hechos desde esta pantalla la invalidan; el resto se ve a los 10 minutos o con ?refrescar=true


def invalidar_cache() -> None:
    _CACHE["v"] = None
    bimonetaria.invalidar()


def precalentar() -> None:
    """Deja listo el cálculo al arrancar para que la primera cuenta que se abra no espere."""
    try:
        _cuentas()
        bimonetaria.cargar_cuentas([])
        bimonetaria._vista_en_memoria()
    except Exception:
        pass  # sin base todavía: se calcula al primer pedido


def _cuentas(refrescar: bool = False) -> tuple[dict, list[dict], list[dict], dict]:
    """Clasificación completa; se guarda 90 segundos para que abrir cada cuenta sea ágil."""
    if refrescar or _CACHE["v"] is None or time.time() - _CACHE["t"] > TTL_SEGUNDOS:
        _CACHE["v"] = _calcular()
        _CACHE["t"] = time.time()
    return _CACHE["v"]


def _con_criterio_bimonetario(cuentas: list[dict]) -> None:
    """Para las cuentas con documentos en dólares, el saldo de la revisión es el saldo en pesos (documentos al TC de su factura)."""
    con_dolares = {f["c"] for f in fetch_all("SELECT DISTINCT IdContacto AS c FROM dbo.Compras WHERE Moneda = 'Dolares'", ())}
    todas = bimonetaria.cargar_cuentas(sorted(con_dolares & {c["idContacto"] for c in cuentas}))
    for c in cuentas:
        if c["idContacto"] in todas:
            r = todas[c["idContacto"]]
            c["saldoPesos"], c["saldoDolares"], c["gobierna"] = r["saldoPesos"], r["saldoDolares"], r["gobierna"]
            c["saldoRevision"] = r["saldoGobierna"]
            c["tcPactado"] = r.get("tcPactado", False)
            c["toleranciaRevision"] = r["toleranciaDolares"] if r["gobierna"] == "Dolares" else None


def _calcular() -> tuple[dict, list[dict], list[dict], dict]:
    d = datos.cargar()
    p = parametros.obtener()
    cuentas = clasificacion.clasificar_cuentas(d, p)
    ids = {c["idContacto"] for c in cuentas}
    h = datos.cargar_hallazgos(d["corte"])
    lista = [x for x in detectores.todos(h, p) if x["idContacto"] in ids]
    clasificacion.agregar_hallazgos(cuentas, lista)
    _con_criterio_bimonetario(cuentas)
    reglas = [k["clave"] for k in conocidos.listar() if k["tipo"] == "concepto-movimiento"]
    return d, cuentas, lista, detectores.hallazgos_movimiento_sin_contacto(h["movimientosSinContacto"], reglas)


@router.get("/parametros", response_model=ParametrosAuditoria)
async def leer_parametros() -> dict:
    return await run_in_threadpool(parametros.obtener)


@router.put("/parametros", response_model=ParametrosAuditoria)
async def cambiar_parametros(body: CambioParametros, request: Request) -> dict:
    cambios = {k: v for k, v in body.model_dump().items() if v is not None}
    if not cambios:
        raise HTTPException(status_code=422, detail="No hay nada para cambiar")
    try:
        return await run_in_threadpool(parametros.guardar, cambios, _usuario_actual(request))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/resumen", response_model=ResumenAuditoria)
async def resumen() -> dict:
    d, cuentas, _, sin_contacto = await run_in_threadpool(_cuentas)
    r = clasificacion.resumen(cuentas)
    if sin_contacto["movimientosSinExplicar"]:
        r["causas"].append({"causa": "movimiento-sin-contacto", "cuentas": 0, "movimientos": sin_contacto["movimientosSinExplicar"],
                            "importe": sin_contacto["importeSinExplicar"], "excepcion": True, "adicional": True})
    corte = d["corte"]
    return {"fechaCorte": corte, "parametros": parametros.obtener(), "avisoCorte":
            f"Los movimientos posteriores al {corte:%d/%m/%Y} no se comparan.", **r}


@router.get("/grupos/{causa}", response_model=GrupoCuentas)
async def grupo(causa: str, pagina: int = Query(default=1, ge=1), tamano: int = Query(default=100, ge=1, le=500)) -> dict:
    if causa not in clasificacion.CAUSAS:
        raise HTTPException(status_code=422, detail="Causa desconocida")
    _, cuentas, _, sin_contacto = await run_in_threadpool(_cuentas)
    if causa == "movimiento-sin-contacto":
        return {"causa": causa, "total": sin_contacto["movimientosSinExplicar"], "items": [],
                "conceptos": sin_contacto["sinExplicar"][:300], "explicados": sin_contacto["explicados"]}
    items = sorted((c for c in cuentas if c["causa"] == causa or causa in c["causasExtra"]),
                   key=lambda c: -abs(c["_importesExtra"].get(causa, 0.0) or c["diferencia"] or 0.0))
    desde = (pagina - 1) * tamano
    return {"causa": causa, "total": len(items),
            "items": [CuentaAuditada(**{k: v for k, v in c.items() if not k.startswith("_")}) for c in items[desde:desde + tamano]]}


@router.get("/cuentas/{id_contacto}/hallazgos", response_model=HallazgosCuenta)
async def hallazgos(id_contacto: int) -> dict:
    d, cuentas, todos, _ = await run_in_threadpool(_cuentas)
    cuenta = next((c for c in cuentas if c["idContacto"] == id_contacto), None)
    if cuenta is None:
        raise HTTPException(status_code=404, detail="La cuenta no está en la auditoría")
    lista = [Hallazgo(causa=comp, motivo=NOMBRES_COMPONENTE.get(comp, comp), importe=imp)
             for comp, imp in cuenta["componentes"].items() if abs(imp) >= 0.005]
    campos = set(Hallazgo.model_fields)
    propios = sorted((h for h in todos if h["idContacto"] == id_contacto), key=lambda h: -(h.get("importe") or 0))
    lista += [Hallazgo(**{k: v for k, v in h.items() if k in campos}) for h in propios[:200]]
    return {"idContacto": id_contacto, "razonSocial": cuenta["razonSocial"], "hallazgos": lista}


@router.get("/conocidos", response_model=list[Conocido])
async def listar_conocidos() -> list[dict]:
    return await run_in_threadpool(conocidos.listar)


async def _conocido(fn, *args):
    try:
        return await run_in_threadpool(fn, *args)
    except conocidos.ConocidoError as exc:
        raise HTTPException(status_code=exc.codigo, detail=str(exc)) from exc


@router.post("/conocidos", response_model=Conocido, status_code=201)
async def crear_conocido(body: AltaConocido, request: Request) -> dict:
    return await _conocido(conocidos.crear, body.tipo, body.clave, body.motivo, body.importeRef, _usuario_actual(request))


@router.delete("/conocidos/{id_conocido}", status_code=204)
async def dar_de_baja_conocido(id_conocido: int, request: Request) -> Response:
    await _conocido(conocidos.dar_de_baja, id_conocido, _usuario_actual(request))
    return Response(status_code=204)


def _con_tipo_de_cambio(avisos: list[dict]) -> list[dict]:
    from datetime import date

    for a in avisos:
        if a.get("sugerencia"):
            a["sugerencia"]["tipoDeCambio"] = bimonetaria.cotizacion_bna().dia_anterior(date.today())
    return avisos


async def _aviso_imputaciones(cuenta: dict) -> list[dict]:
    datos_ = await run_in_threadpool(revision.imputaciones, cuenta["idContacto"])
    aviso = revision.aviso_imputaciones(cuenta, datos_)
    return [aviso] if aviso else []


def _vecina(c: dict | None) -> dict | None:
    return None if c is None else {"idContacto": c["idContacto"], "razonSocial": c["razonSocial"]}


def _estados(cuentas: list[dict], filas: dict) -> dict[int, str]:
    return {c["idContacto"]: revision.estado_de_revision(filas.get(c["idContacto"]), c.get("saldoRevision", c["saldoSistema"])) for c in cuentas}


@router.get("/revision/siguiente", response_model=CuentaVecina | None)
async def siguiente_cuenta(despuesDe: int | None = None) -> dict | None:
    _, cuentas, _, _ = await run_in_threadpool(_cuentas)
    filas = await run_in_threadpool(revision.leer_todas)
    esperados = {i: f["SaldoEsperado"] for i, f in filas.items()}
    orden = revision.orden_de_revision(cuentas, esperados)
    return _vecina(revision.siguiente_sin_revisar(orden, _estados(cuentas, filas), despuesDe))


@router.get("/cuentas/{id_contacto}/revision", response_model=RevisionCuenta)
async def ver_revision(id_contacto: int, refrescar: bool = False) -> dict:
    _, cuentas, _, _ = await run_in_threadpool(_cuentas, refrescar)
    cuenta = next((c for c in cuentas if c["idContacto"] == id_contacto), None)
    if cuenta is None:
        raise HTTPException(status_code=404, detail="La cuenta no está en la auditoría")
    filas = await run_in_threadpool(revision.leer_todas)
    esperados = {i: f["SaldoEsperado"] for i, f in filas.items()}
    orden = revision.orden_de_revision(cuentas, esperados)
    ids = [c["idContacto"] for c in orden]
    pos = ids.index(id_contacto)
    estados = _estados(cuentas, filas)
    fila = filas.get(id_contacto)
    return {
        "idContacto": id_contacto, "razonSocial": cuenta["razonSocial"], "moneda": cuenta["moneda"], "saldo": cuenta.get("saldoRevision", cuenta["saldoSistema"]), "gobierna": cuenta.get("gobierna", "Pesos"),
        "saldoEsperado": fila["SaldoEsperado"] if fila else None, "estado": estados[id_contacto],
        "fechaRevision": fila["FechaRevision"] if fila else None, "usuarioRevision": fila["Usuario"] if fila else None,
        "nota": fila["Nota"] if fila else None, "saldoAlRevisar": float(fila["SaldoAlRevisar"]) if fila and fila["SaldoAlRevisar"] is not None else None,
        "dificultad": revision.dificultad(cuenta, fila["SaldoEsperado"] if fila else None),
        "avisos": _con_tipo_de_cambio(revision.avisos_de_cuenta(cuenta, fila["SaldoEsperado"] if fila else None)) + await _aviso_imputaciones(cuenta),
        "siguiente": _vecina(revision.siguiente_sin_revisar(orden, estados, id_contacto)),
        "anterior": _vecina(orden[pos - 1]) if pos > 0 else None,
        "revisadas": sum(1 for e in estados.values() if e == "revisada"), "totalCuentas": len(cuentas),
        "historial": await run_in_threadpool(revision.historial, id_contacto),
    }


@router.put("/cuentas/{id_contacto}/revision", response_model=RevisionCuenta)
async def cambiar_revision(id_contacto: int, body: CambioRevision, request: Request) -> dict:
    _, cuentas, _, _ = await run_in_threadpool(_cuentas)
    cuenta = next((c for c in cuentas if c["idContacto"] == id_contacto), None)
    if cuenta is None:
        raise HTTPException(status_code=404, detail="La cuenta no está en la auditoría")
    try:
        await run_in_threadpool(revision.guardar, id_contacto, cuenta.get("saldoRevision", cuenta["saldoSistema"]), _usuario_actual(request), body.estado, body.nota,
                                body.saldoEsperado, body.quitarSaldoEsperado)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await ver_revision(id_contacto)


@router.get("/cuentas/{id_contacto}/comprobantes")
async def comprobantes(id_contacto: int) -> dict:
    """Ruta del comprobante original (PDF) de cada compra de la cuenta, para abrirlo desde la revisión."""
    filas = await run_in_threadpool(
        fetch_all, "SELECT IdDeuda AS id, [Documento Original] AS ruta FROM dbo.Compras WHERE IdContacto = ? AND [Documento Original] IS NOT NULL",
        (id_contacto,))
    return {str(f["id"]): f["ruta"] for f in filas if f["ruta"]}


async def _escribir(fn, *args):
    try:
        return await run_in_threadpool(fn, *args)
    except (correcciones.CorreccionError, ajustes.AjusteError, asignacion.AsignacionError) as exc:
        raise HTTPException(status_code=exc.codigo, detail=str(exc)) from exc


def _saldo_de(id_contacto: int) -> float:
    _, cuentas, _, _ = _cuentas()
    cuenta = next((c for c in cuentas if c["idContacto"] == id_contacto), None)
    if cuenta is None:
        raise correcciones.CorreccionError(404, "La cuenta no está en la auditoría")
    return cuenta.get("saldoRevision", cuenta["saldoSistema"])


@router.post("/cuentas/{id_contacto}/anular-aplicaciones", status_code=201)
async def anular_aplicaciones(id_contacto: int, body: PedidoAnulacion, request: Request) -> dict:
    usuario = _usuario_actual(request)
    saldo = await _escribir(_saldo_de, id_contacto)
    res = await _escribir(correcciones.anular_aplicaciones, id_contacto, body.idsAplicacion, body.motivo, usuario, saldo)
    await run_in_threadpool(revision.registrar, id_contacto, "anular-imputaciones",
                            {"idCorreccion": res["idCorreccion"], "aplicaciones": res["aplicaciones"], "importe": res["importe"], "motivo": body.motivo}, usuario)
    invalidar_cache()
    return res


@router.post("/correcciones/{id_correccion}/revertir")
async def revertir_correccion(id_correccion: int, request: Request) -> dict:
    usuario = _usuario_actual(request)
    regla = await run_in_threadpool(fetch_one, "SELECT Regla AS r FROM dbo.AuditoriaCorrecciones WHERE IdCorreccion = ?", (id_correccion,))
    if regla and regla["r"] == asignacion.REGLA:
        res = await _escribir(asignacion.revertir, id_correccion, usuario)
    else:
        res = await _escribir(correcciones.revertir, id_correccion, usuario)
    invalidar_cache()
    return res


@router.get("/cuentas/{id_contacto}/correcciones", response_model=list[CorreccionCuenta])
async def correcciones_de_cuenta(id_contacto: int) -> list[dict]:
    return await run_in_threadpool(correcciones.listar_de_cuenta, id_contacto)


@router.post("/cuentas/{id_contacto}/nota-ajuste", status_code=201)
async def nota_ajuste(id_contacto: int, body: PedidoNotaAjuste, request: Request) -> dict:
    usuario = _usuario_actual(request)
    await _escribir(_saldo_de, id_contacto)
    id_compra = await _escribir(ajustes.cargar_nota_ajuste, id_contacto, body.tipo, body.fecha, body.importe, body.moneda, body.motivo, body.tipoDeCambio)
    await run_in_threadpool(revision.registrar, id_contacto, "nota-ajuste",
                            {"idCompra": id_compra, "tipo": body.tipo, "importe": body.importe, "moneda": body.moneda, "motivo": body.motivo}, usuario)
    invalidar_cache()
    return {"idCompra": id_compra}


@router.get("/cuentas/{id_contacto}/movimientos", response_model=MovimientosRevision)
async def movimientos_de_cuenta(id_contacto: int, page: int = Query(default=1, ge=1), pageSize: int = Query(default=100, ge=1, le=200),
                                refrescar: bool = False) -> dict:
    """Movimientos con un solo criterio de moneda: saldo en pesos (documentos en dólares al TC de su factura) y en dólares."""
    cuenta = await run_in_threadpool(bimonetaria.cargar_cuenta, id_contacto, refrescar)
    filas = list(reversed(cuenta["filas"]))  # los más nuevos primero; el saldo acumulado sigue siendo el cronológico
    desde = (page - 1) * pageSize
    pagina = filas[desde:desde + pageSize]

    def _resolver() -> list[dict]:
        return [{**f, "origen": origen_resolver.resolve_origen(f["origenTipo"], f["idOrigen"])} for f in pagina]

    items = await run_in_threadpool(_resolver)
    return {"items": items, "total": len(filas), "page": page, "pageSize": pageSize, "saldoPesos": cuenta["saldoPesos"],
            "saldoDolares": cuenta["saldoDolares"], "tieneDolares": cuenta["tieneDolares"], "bimonetaria": cuenta["bimonetaria"],
            "gobierna": cuenta["gobierna"], "saldoGobierna": cuenta["saldoGobierna"], "tcPactado": cuenta.get("tcPactado", False),
            "avisos": cuenta["avisos"]}


# ---- Recalcular las imputaciones de una cuenta (FIFO), con la misma simulación, aplicación y reversión del recálculo FIFO ----

def _admin(request: Request) -> None:
    from src.features.recalculo_fifo.router import _exigir_admin

    _exigir_admin(request)


@router.post("/cuentas/{id_contacto}/fifo/simular", status_code=201)
async def fifo_simular(id_contacto: int, request: Request) -> dict:
    from src.features.recalculo_fifo import ejecuciones as fifo

    _admin(request)
    try:
        res = await run_in_threadpool(fifo.simular, [id_contacto], _usuario_actual(request))
        det = await run_in_threadpool(fifo.detalle, res["idEjecucion"], id_contacto)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    vigentes = await run_in_threadpool(
        fetch_one, "SELECT COUNT(*) AS n FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
                   "WHERE a.Anulada = 0 AND c.IdContacto = ?", (id_contacto,))
    return {"idEjecucion": res["idEjecucion"], "contacto": det["contacto"], "aplicaciones": len(det["aplicaciones"]),
            "aplicacionesVigentes": vigentes["n"]}


@router.post("/cuentas/{id_contacto}/fifo/{id_ejecucion}/aplicar")
async def fifo_aplicar(id_contacto: int, id_ejecucion: int, request: Request) -> dict:
    from src.features.recalculo_fifo import ejecuciones as fifo

    _admin(request)
    usuario = _usuario_actual(request)
    try:
        res = await run_in_threadpool(fifo.aplicar, id_ejecucion, [id_contacto], False, usuario)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"No existe la ejecución {id_ejecucion}") from exc
    except fifo.Conflicto as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (fifo.RequiereConfirmacion, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await run_in_threadpool(revision.registrar, id_contacto, "fifo-aplicado", {"idEjecucion": id_ejecucion}, usuario)
    invalidar_cache()
    return res


@router.post("/cuentas/{id_contacto}/fifo/{id_ejecucion}/revertir")
async def fifo_revertir(id_contacto: int, id_ejecucion: int, request: Request) -> dict:
    from src.features.recalculo_fifo import ejecuciones as fifo

    _admin(request)
    usuario = _usuario_actual(request)
    try:
        res = await run_in_threadpool(fifo.revertir, id_ejecucion, usuario)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"No existe la ejecución {id_ejecucion}") from exc
    except fifo.Conflicto as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await run_in_threadpool(revision.registrar, id_contacto, "fifo-revertido", {"idEjecucion": id_ejecucion}, usuario)
    invalidar_cache()
    return res


@router.get("/movimientos-sin-contacto", response_model=list[MovimientoSinContacto])
async def movimientos_sin_contacto(concepto: str | None = None, limite: int = Query(default=300, ge=1, le=1000)) -> list[dict]:
    """Movimientos del banco sin contacto de cualquier monto (los que ninguna regla explica), para asignarles uno."""
    return await run_in_threadpool(asignacion.movimientos_sin_contacto, concepto, limite)


@router.post("/movimientos-sin-contacto/asignar", status_code=201)
async def asignar_contacto(body: PedidoAsignacion, request: Request) -> dict:
    usuario = _usuario_actual(request)
    res = await _escribir(asignacion.asignar, [i.model_dump() for i in body.items], body.idContacto, body.motivo, usuario)
    await run_in_threadpool(revision.registrar, body.idContacto, "asignar-movimientos",
                            {"idCorreccion": res["idCorreccion"], "movimientos": res["movimientos"], "motivo": body.motivo}, usuario)
    invalidar_cache()
    return res


# ---- FIFO de todos los contactos por tandas ----

@router.get("/fifo/plan", response_model=PlanFifo)
async def fifo_plan_endpoint() -> dict:
    return await run_in_threadpool(fifo_plan.plan)


@router.post("/fifo/tandas/simular", status_code=201)
async def fifo_simular_tanda(body: PedidoTanda, request: Request) -> dict:
    from src.features.recalculo_fifo import ejecuciones as fifo

    _admin(request)
    if not body.contactos or len(body.contactos) > fifo_plan.TAMANO_TANDA * 2:
        raise HTTPException(status_code=422, detail="La tanda está vacía o es demasiado grande")
    try:
        return await run_in_threadpool(fifo.simular, sorted(set(body.contactos)), _usuario_actual(request))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/fifo/tandas/{id_ejecucion}/aplicar")
async def fifo_aplicar_tanda(id_ejecucion: int, body: PedidoTanda, request: Request) -> dict:
    from src.features.recalculo_fifo import ejecuciones as fifo

    _admin(request)
    try:
        res = await run_in_threadpool(fifo.aplicar, id_ejecucion, sorted(set(body.contactos)), False, _usuario_actual(request))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"No existe la ejecución {id_ejecucion}") from exc
    except fifo.Conflicto as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (fifo.RequiereConfirmacion, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    invalidar_cache()
    return res


@router.post("/fifo/tandas/{id_ejecucion}/revertir")
async def fifo_revertir_tanda(id_ejecucion: int, request: Request) -> dict:
    from src.features.recalculo_fifo import ejecuciones as fifo

    _admin(request)
    try:
        res = await run_in_threadpool(fifo.revertir, id_ejecucion, _usuario_actual(request))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"No existe la ejecución {id_ejecucion}") from exc
    except fifo.Conflicto as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    invalidar_cache()
    return res
