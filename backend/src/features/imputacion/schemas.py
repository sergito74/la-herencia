"""Schemas del motor de auto-clasificación (017-imputacion-automatica-costos)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Origen = Literal["Insumo", "Contratista"]
EstadoPropuesta = Literal["Pendiente", "Aprobada", "RequiereIntervencion"]


class ContextoComercial(BaseModel):
    producto: str | None = None
    idCompra: int | None = None
    proveedor: str | None = None
    tipoDocumento: str | None = None
    numeroDocumento: str | None = None
    fechaDocumento: datetime | None = None
    monedaDocumento: str | None = None


class PropuestaFraccion(ContextoComercial):
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
    cantidad: float | None = None
    unidad: str | None = None
    cultivo: str | None = None
    campania: str | None = None
    lote: str | None = None
    centroCosto: str | None = None
    estado: EstadoPropuesta
    fechaCalculo: datetime
    fechaAprobacion: datetime | None
    usuarioAprobacion: str | None = None


class CorreccionFraccion(BaseModel):
    idPropuesta: int
    idLote: int | None = None
    idCultivo: int | None = None
    idCampania: int | None = None
    importe: float | None = None


class AprobarPropuestaIn(BaseModel):
    correcciones: list[CorreccionFraccion] | None = None


class AprobarLoteIn(BaseModel):
    idCorridas: list[str]


class AprobarLoteResultado(BaseModel):
    idCorrida: str
    ok: bool
    error: str | None = None


class AprobarLoteOut(BaseModel):
    resultados: list[AprobarLoteResultado]
    aprobadas: int
    fallidas: int


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


class PendienteIntervencionOut(ContextoComercial):
    idCorrida: str
    origen: Origen
    idDetalleCompra: int
    motivo: Literal["sinOrdenVinculada", "repartoNoCierra", "fueraDeCalendarioAgricola"]
    fechaCalculo: datetime
