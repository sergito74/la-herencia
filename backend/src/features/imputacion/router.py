"""Endpoints del motor de auto-clasificación (017-imputacion-automatica-costos)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.features.imputacion import motor, repository
from src.features.ordenes import resultado as ordenes_resultado
from src.features.imputacion.repository import CorridaNoVigente
from src.features.imputacion.schemas import (
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


def _asegurar_corrida(id_detalle_compra: int, origen: str | None) -> None:
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

    fracciones = motor.calcular_propuesta_insumo(id_detalle_compra)
    if not fracciones:
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
        _asegurar_corrida(idDetalleCompra, origen)
    filas = repository.listar_propuestas(estado, origen, idDetalleCompra, page, pageSize)
    return [PropuestaFraccion(**f) for f in filas]


@router.get("/propuestas/{idDetalleCompra}/trazabilidad")
async def trazabilidad(idDetalleCompra: int) -> list[dict]:
    return motor.trazabilidad_insumo(idDetalleCompra)


@router.post("/propuestas/{idCorrida}/aprobar")
async def aprobar_propuesta(idCorrida: str, body: AprobarPropuestaIn) -> dict:
    correcciones = [c.model_dump() for c in body.correcciones] if body.correcciones else None
    try:
        repository.aprobar_corrida(idCorrida, correcciones)
    except CorridaNoVigente as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "ok"}


@router.get("/pendientes-intervencion", response_model=list[PendienteIntervencionOut])
async def pendientes_intervencion(
    page: int = Query(default=1, ge=1), pageSize: int = Query(default=50, ge=1, le=200)
) -> list[PendienteIntervencionOut]:
    filas = repository.pendientes_intervencion(page, pageSize)
    salida = []
    for f in filas:
        motivo = "repartoNoCierra"
        if f["origen"] == "Contratista":
            _fracciones, motivo_real = motor.evaluar_contratista(f["idDetalleCompra"])
            motivo = motivo_real or motivo
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


@router.get("/comparacion", response_model=ComparacionCampaniaOut)
async def comparacion(idCampania: int = Query(...)) -> ComparacionCampaniaOut:
    heredado = ordenes_resultado.resumen_campania_heredado(idCampania)
    fila = heredado[0] if heredado else {"campania": None, "totalCostoPesos": 0.0, "totalCostoDolares": None}
    nuevo = repository.costo_aprobado_por_campania(idCampania)

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


@router.post("/recalcular")
async def recalcular(body: RecalcularIn) -> dict:
    if body.idDetalleCompra is None:
        raise ValueError("idDetalleCompra es requerido")
    origen = repository.origen_de_corrida(repository.corrida_vigente(body.idDetalleCompra) or "") or "Insumo"
    id_corrida = motor.recalcular_si_corresponde(body.idDetalleCompra, origen)
    return {"idCorrida": id_corrida}
