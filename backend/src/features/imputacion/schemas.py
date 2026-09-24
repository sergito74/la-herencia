"""Schemas del motor de auto-clasificación (017-imputacion-automatica-costos)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Origen = Literal["Insumo", "Contratista"]
EstadoPropuesta = Literal["Pendiente", "Aprobada", "RequiereIntervencion"]


class PropuestaFraccion(BaseModel):
    idPropuesta: int
    idCorrida: str
    origen: Origen
    idDetalleCompra: int
    idOrdenTrabajo: int | None
    idLote: int | None
    idCultivo: int | None
    idCampania: int | None
    idCentroCosto: int | None
    esGanaderia: bool | None
    importe: float
    estado: EstadoPropuesta
    fechaCalculo: datetime
    fechaAprobacion: datetime | None


class CorreccionFraccion(BaseModel):
    idPropuesta: int
    idLote: int | None = None
    idCultivo: int | None = None
    idCampania: int | None = None
    importe: float | None = None


class AprobarPropuestaIn(BaseModel):
    correcciones: list[CorreccionFraccion] | None = None


class RecalcularIn(BaseModel):
    idDetalleCompra: int | None = None
    idOrdenTrabajo: int | None = None


class CostoCampaniaOut(BaseModel):
    totalPesos: float
    totalDolares: float | None = None


class CostoNuevoCampaniaOut(BaseModel):
    totalPesos: float
    totalAprobado: float
    totalPendiente: float


class ComparacionCampaniaOut(BaseModel):
    idCampania: int
    campania: str | None
    costoHeredado: CostoCampaniaOut
    costoNuevo: CostoNuevoCampaniaOut
    diferenciaPesos: float
    diferenciaPorcentual: float | None
    comparacionParcial: bool


class PendienteIntervencionOut(BaseModel):
    idCorrida: str
    origen: Origen
    idDetalleCompra: int
    motivo: Literal["sinOrdenVinculada", "repartoNoCierra", "fueraDeCalendarioAgricola"]
    fechaCalculo: datetime
