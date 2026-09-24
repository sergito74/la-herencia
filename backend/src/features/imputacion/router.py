"""Endpoints del motor de auto-clasificación (017-imputacion-automatica-costos)."""

from __future__ import annotations

import asyncio
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from src.features.imputacion import exportacion, motor, repository
from src.features.ordenes import resultado as ordenes_resultado
from src.features.imputacion.repository import CorridaNoVigente
from src.features.imputacion.schemas import (
    AprobarLoteIn,
    AprobarLoteOut,
    AprobarLoteResultado,
    AprobarPropuestaIn,
    ComparacionCampaniaOut,
    CostoCampaniaOut,
    CostoNuevoCampaniaOut,
    EstadoPropuesta,
    Origen,
    PendienteIntervencionOut,
    PropuestaFraccion,
    RecalcularIn,
)

router = APIRouter(prefix="/api/imputacion", tags=["imputacion"])


def _usuario_actual(request: Request) -> str | None:
    """`NombreUsuario` de la sesión actual (016-autenticacion) — el token
    solo trae `idUsuario`, se resuelve el nombre para registrar quién
    aprobó (control interno, hallazgo de revisión financiera 2026-09-25)."""
    payload = getattr(request.state, "usuario", None)
    if not payload:
        return None
    return repository.nombre_usuario(payload["idUsuario"])


# Serializa check + insert mientras el trabajo corre fuera del event loop.
_lock_corridas = asyncio.Lock()


async def _asegurar_corrida(id_detalle_compra: int, origen: str | None) -> None:
    async with _lock_corridas:
        await run_in_threadpool(_asegurar_corrida_sync, id_detalle_compra, origen)


def _asegurar_corrida_sync(id_detalle_compra: int, origen: str | None) -> None:
    """Si el renglón todavía no tiene ninguna corrida, la calcula y la guarda
    (dentro de alcance, FR-014 — si está fuera de alcance no genera nada)."""
    if repository.corrida_vigente(id_detalle_compra) is not None:
        return

    if origen == "Contratista":
        fracciones, motivo = motor.evaluar_contratista(id_detalle_compra)
        if not fracciones:
            if motivo:
                repository.guardar_requiere_intervencion("Contratista", id_detalle_compra, motivo)
            return
        repository.guardar_corrida("Contratista", id_detalle_compra, fracciones)
        return

    fracciones, motivo = motor.evaluar_insumo(id_detalle_compra)
    if not fracciones:
        if motivo:
            repository.guardar_requiere_intervencion("Insumo", id_detalle_compra, motivo)
        return
    fracciones = repository.marcar_stock_sin_consumir_aprobada(fracciones)
    repository.guardar_corrida("Insumo", id_detalle_compra, fracciones)


@router.get("/propuestas", response_model=list[PropuestaFraccion])
async def listar_propuestas(
    idDetalleCompra: int | None = Query(default=None),
    estado: EstadoPropuesta | None = Query(default=None),
    origen: Origen | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=200),
) -> list[PropuestaFraccion]:
    if idDetalleCompra is not None:
        await _asegurar_corrida(idDetalleCompra, origen)
    filas = await run_in_threadpool(repository.listar_propuestas, estado, origen, idDetalleCompra, page, pageSize)
    return [PropuestaFraccion(**f) for f in filas]


@router.get("/propuestas/{idDetalleCompra}/trazabilidad")
async def trazabilidad(idDetalleCompra: int) -> list[dict]:
    return await run_in_threadpool(motor.trazabilidad_insumo, idDetalleCompra)


@router.post("/propuestas/{idCorrida}/aprobar")
async def aprobar_propuesta(idCorrida: str, body: AprobarPropuestaIn, request: Request) -> dict:
    correcciones = [c.model_dump() for c in body.correcciones] if body.correcciones else None
    usuario = await run_in_threadpool(_usuario_actual, request)
    try:
        await run_in_threadpool(repository.aprobar_corrida, idCorrida, correcciones, usuario)
    except CorridaNoVigente as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "ok"}


@router.post("/propuestas/aprobar-lote", response_model=AprobarLoteOut)
async def aprobar_lote(body: AprobarLoteIn, request: Request) -> AprobarLoteOut:
    """Aprueba varias corridas de una sola llamada, sin corrección — para el
    caso frecuente de aprobar en bloque las propuestas que ya están bien
    (UX, hallazgo de revisión 2026-09-25). Cada corrida se aprueba
    independiente: si una falla (ej. ya no es la vigente), las demás
    igual se procesan."""
    usuario = await run_in_threadpool(_usuario_actual, request)
    resultados: list[AprobarLoteResultado] = []
    for id_corrida in body.idCorridas:
        try:
            await run_in_threadpool(repository.aprobar_corrida, id_corrida, None, usuario)
            resultados.append(AprobarLoteResultado(idCorrida=id_corrida, ok=True))
        except CorridaNoVigente as exc:
            resultados.append(AprobarLoteResultado(idCorrida=id_corrida, ok=False, error=str(exc)))
        except ValueError as exc:
            resultados.append(AprobarLoteResultado(idCorrida=id_corrida, ok=False, error=str(exc)))
    aprobadas = sum(1 for r in resultados if r.ok)
    return AprobarLoteOut(resultados=resultados, aprobadas=aprobadas, fallidas=len(resultados) - aprobadas)


@router.get("/pendientes-intervencion", response_model=list[PendienteIntervencionOut])
async def pendientes_intervencion(
    page: int = Query(default=1, ge=1), pageSize: int = Query(default=50, ge=1, le=200)
) -> list[PendienteIntervencionOut]:
    filas = await run_in_threadpool(repository.pendientes_intervencion, page, pageSize)
    salida = []
    for f in filas:
        if f["origen"] == "Contratista":
            _fracciones, motivo_real = await run_in_threadpool(motor.evaluar_contratista, f["idDetalleCompra"])
        else:
            _fracciones, motivo_real = await run_in_threadpool(motor.evaluar_insumo, f["idDetalleCompra"])
        motivo = motivo_real or "repartoNoCierra"
        salida.append(
            PendienteIntervencionOut(
                idCorrida=f["idCorrida"],
                origen=f["origen"],
                idDetalleCompra=f["idDetalleCompra"],
                motivo=motivo,
                fechaCalculo=f["fechaCalculo"],
            )
        )
    return salida


@router.get("/documentos")
async def listar_documentos(
    idContacto: int | None = Query(default=None),
    fechaDesde: str | None = Query(default=None),
    fechaHasta: str | None = Query(default=None),
    estado: EstadoPropuesta | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Documentos comerciales con sus renglones e imputaciones (manual +
    motor) — informe/pantalla para la oficina del contador. `estado` filtra
    a los documentos que tienen al menos una fracción vigente en ese estado
    (ej. "solo lo que requiere intervención")."""
    documentos, total = await run_in_threadpool(repository.listar_documentos_con_imputacion, idContacto, fechaDesde, fechaHasta, estado, page, pageSize)
    lineas_por_compra = await run_in_threadpool(repository.lineas_con_imputacion_batch, tuple(d["idCompra"] for d in documentos))
    total_general = await run_in_threadpool(repository.total_general_documentos, idContacto, fechaDesde, fechaHasta, estado)

    for doc in documentos:
        lineas = lineas_por_compra.get(doc["idCompra"], [])
        for linea in lineas:
            linea["totalFracciones"] = round(sum(f["importe"] for f in linea["fracciones"]), 2)
        doc["lineas"] = lineas
        doc["totalDocumento"] = round(sum(l["totalFracciones"] for l in lineas), 2)

    return {"items": documentos, "total": total, "page": page, "pageSize": pageSize, "totalGeneral": round(total_general, 2)}


@router.get("/documentos/exportar")
async def exportar_documentos(
    idContacto: int | None = Query(default=None),
    fechaDesde: str | None = Query(default=None),
    fechaHasta: str | None = Query(default=None),
    estado: EstadoPropuesta | None = Query(default=None),
) -> Response:
    contenido = await run_in_threadpool(exportacion.informe_documentos_xlsx, idContacto, fechaDesde, fechaHasta, estado)
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="imputacion-documentos-{date.today().isoformat()}.xlsx"'},
    )


@router.get("/comparacion", response_model=ComparacionCampaniaOut)
async def comparacion(idCampania: int = Query(...)) -> ComparacionCampaniaOut:
    heredado = await run_in_threadpool(ordenes_resultado.resumen_campania_heredado, idCampania)
    fila = heredado[0] if heredado else {"campania": None, "totalCostoPesos": 0.0, "totalCostoDolares": None}
    nuevo = await run_in_threadpool(repository.costo_aprobado_por_campania, idCampania)

    total_heredado = float(fila.get("totalCostoPesos") or 0)
    total_nuevo = float(nuevo["totalAprobado"] or 0)
    diferencia = total_nuevo - total_heredado

    return ComparacionCampaniaOut(
        idCampania=idCampania,
        campania=fila.get("campania"),
        costoHeredado=CostoCampaniaOut(totalPesos=total_heredado, totalDolares=fila.get("totalCostoDolares")),
        costoNuevo=CostoNuevoCampaniaOut(
            totalPesos=total_nuevo, totalAprobado=total_nuevo, totalPendiente=float(nuevo["totalPendiente"] or 0)
        ),
        diferenciaPesos=round(diferencia, 2),
        diferenciaPorcentual=round(diferencia / total_heredado * 100, 2) if total_heredado else None,
        comparacionParcial=abs(float(nuevo["totalPendiente"] or 0)) > 1e-6,
    )


@router.post("/calcular-pendientes")
async def calcular_pendientes() -> dict:
    """Corre el motor sobre todas las facturas en alcance (insumo/contratista)
    que todavía no tienen ninguna corrida — botón de "activación" masiva en
    vez de tener que pedir cada propuesta una por una."""
    insumos_calculados = 0
    for id_detalle_compra in await run_in_threadpool(repository.candidatos_insumo_sin_corrida):
        await _asegurar_corrida(id_detalle_compra, "Insumo")
        insumos_calculados += 1

    contratistas_calculados = 0
    for id_compra in await run_in_threadpool(repository.candidatos_contratista_sin_corrida):
        await _asegurar_corrida(id_compra, "Contratista")
        contratistas_calculados += 1

    return {"insumosCalculados": insumos_calculados, "contratistasCalculados": contratistas_calculados}


@router.post("/recalcular")
async def recalcular(body: RecalcularIn) -> dict:
    if body.idDetalleCompra is None:
        raise ValueError("idDetalleCompra es requerido")
    vigente = await run_in_threadpool(repository.corrida_vigente, body.idDetalleCompra)
    origen = await run_in_threadpool(repository.origen_de_corrida, vigente or "") or "Insumo"
    id_corrida = await run_in_threadpool(motor.recalcular_si_corresponde, body.idDetalleCompra, origen)
    return {"idCorrida": id_corrida}
