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
    idContacto: int | None = None
    empleado: str | None = None
    fechaPago: date | None = None
    periodoLiquidado: str | None = None
    importe: float | None = None
    # Valor crudo de `dbo.Remuneraciones.Recibo` (formato roto "ruta#ruta#",
    # mismo patrón que `documentoOriginal` en Compras/Ventas — ver
    # `documentoLocal.ts`). El frontend lo normaliza igual que ese campo;
    # cuando es NULL o "SIN RECIBO"/"SIN COPIA", cae al matching por
    # nombre de archivo de `GET /api/remuneraciones/{id}/recibo`.
    recibo: str | None = None


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


class NuevaLiquidacionRequest(BaseModel):
    """Alta de una liquidación (028). Todos los conceptos monetarios se
    cargan siempre en positivo, tal como figuran en el recibo real — el
    backend resta internamente los de descuento (ver
    `repository.calcular_importe_neto`, research.md §1)."""

    idContacto: int
    fechaPago: date
    periodoLiquidado: str
    sueldoBasico: float = 0
    antiguedad: float = 0
    adicFuturosAumentos: float = 0
    diaGremio: float = 0
    aguinaldo: float = 0
    vacaciones: float = 0
    ajuste: float = 0
    ajusteNoRemunerativo: float = 0
    redondeo: float = 0
    bonificacionAdicional: float = 0
    jubilacion: float = 0
    ley19032: float = 0
    obraSocial: float = 0
    obraSocialAcuerdos: float = 0
    aporteSindical: float = 0
    servicioDeSepelio: float = 0
    confirmarDuplicado: bool = False


class NuevaLiquidacionResponse(BaseModel):
    idSalario: int
    importeNeto: float
    recibo: str | None = None


class AdjuntarReciboResponse(BaseModel):
    idSalario: int
    recibo: str
