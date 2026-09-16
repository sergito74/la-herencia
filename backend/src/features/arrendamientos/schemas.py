"""Pydantic contract models for the Arrendamientos module (read-only).

UI-facing term is "Arrendamiento", never "Alquiler", even though the
underlying SQL tables are named `Alquileres`/`Detalle Cobro Alquiler`
(terminology decision from the agro-erp-frontend-specialist consultation,
see specs/005-egresos-y-ventas-menores/plan.md).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class CobroAlquiler(BaseModel):
    idCobroAlquiler: int
    numeroCuota: int | None = None
    importeCuota: float | None = None
    estado: str | None = None
    fechaVencimiento: date | None = None


class Arrendamiento(BaseModel):
    idAlquiler: int
    fecha: date | None = None
    inicioPeriodo: date | None = None
    finPeriodo: date | None = None
    # Label real en el formulario Access: "Arrendatario" (quien renta el
    # campo), confirmado inspeccionando el formulario "Alquileres".
    idContacto: int | None = None
    contacto: str | None = None
    importeTotalContrato: float | None = None
    cantidadCuotas: int | None = None
    tipoDePago: str | None = None
    superficieTotal: float | None = None
    retencionGanancias: float | None = None
    cobros: list[CobroAlquiler]


class ArrendamientosListResponse(BaseModel):
    items: list[Arrendamiento]
    page: int
    pageSize: int
    total: int
