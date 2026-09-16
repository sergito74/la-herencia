"""Pydantic contract models for the Remuneraciones module (read-only).

`Pagos Remuneraciones.IdEmpleado` is NOT a foreign key into `Contactos`
(confirmed against real data 2026-09-17: its values, 1-6, resolve to
"Proveedor" contacts, while real employees in `Remuneraciones.IdContacto`
range 46-632 — a completely different ID space). There is no reliable
link from a payment to an employee or to a specific liquidación, so
`PagoRemuneracion` is modeled and queried as an independent entity, never
nested under `Remuneracion` (same pattern as Retención de Venta de
Hacienda in specs/005-egresos-y-ventas-menores).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Remuneracion(BaseModel):
    idSalario: int
    empleado: str | None = None
    fechaPago: date | None = None
    periodoLiquidado: str | None = None
    importe: float | None = None


class RemuneracionesListResponse(BaseModel):
    items: list[Remuneracion]
    page: int
    pageSize: int
    total: int


class PagoRemuneracion(BaseModel):
    idPago: int
    fecha: date | None = None
    cuenta: str | None = None
    caja: str | None = None
    importe: float | None = None


class PagosRemuneracionListResponse(BaseModel):
    items: list[PagoRemuneracion]
    page: int
    pageSize: int
    total: int
