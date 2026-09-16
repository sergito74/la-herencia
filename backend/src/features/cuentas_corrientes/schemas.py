"""Pydantic contract models for the Cuentas corrientes module (read-only).

This module MUST NOT expose imputacion (rubro/centro de costo/destino) —
that data lives exclusively in `src.features.compras` (FR-009). It also
MUST NOT accept writes (FR-010).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Contacto(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    tipoContacto: str | None = None


class ContactosListResponse(BaseModel):
    items: list[Contacto]


class Saldo(BaseModel):
    idContacto: int
    saldoParcial: float | None = None


class Origen(BaseModel):
    """Referencia resuelta de un movimiento, per data-model.md.

    `tipo` determina qué otros campos están poblados:
    - "compra": idCompra, numeroDocumento, proveedor
    - "tesoreria": medio, idMovimiento, fecha, importe
    - "impuesto": idImpuesto, tipoImpuesto, importe
    - "retencion": idRetencion, numeroCertificado, importe
    - "remuneracion": idSalario, periodoLiquidado, empleado
    - "arrendamiento": idAlquiler, contacto, importeTotalContrato
    - "venta_hacienda": idRetencion, numeroDocumento, importe (referencia a la
      retención, no a la venta — ver specs/005-egresos-y-ventas-menores)
    - "fuera_de_alcance": origenTipo
    - "no_disponible": motivo
    """

    tipo: str
    idCompra: int | None = None
    proveedor: str | None = None
    medio: str | None = None
    idMovimiento: int | None = None
    fecha: date | None = None
    importe: float | None = None
    numeroDocumento: str | None = None
    origenTipo: str | None = None
    motivo: str | None = None
    idImpuesto: int | None = None
    tipoImpuesto: str | None = None
    idRetencion: int | None = None
    numeroCertificado: str | None = None
    idSalario: int | None = None
    periodoLiquidado: str | None = None
    empleado: str | None = None
    idAlquiler: int | None = None
    contacto: str | None = None
    importeTotalContrato: float | None = None


class MovimientoCuentaCorriente(BaseModel):
    fecha: date | None = None
    documento: str | None = None
    numeroDocumento: str | None = None
    deuda: float | None = None
    credito: float | None = None
    origen: Origen


class MovimientosListResponse(BaseModel):
    items: list[MovimientoCuentaCorriente]
    page: int
    pageSize: int
    total: int
