"""Pydantic contract models for the Contactos module.

Master data used by every other module (Compras, Ventas, Finanzas,
Personal) for contact selection. Reads are safe against either database;
writes (create/update) go exclusively to `WC` via `execute_write`
(golden rule, ver memory.md).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# 8 valores reales confirmados contra `WC`/`LaHerencia`
# (INFORMATION_SCHEMA + `SELECT DISTINCT [Tipo Contacto]`, 2026-09-17).
# `Tipo Contacto` es `nvarchar(20)` libre en el origen, no una FK — se
# restringe acá a estos 8 valores para evitar variantes/typos nuevos.
TIPOS_CONTACTO = (
    "Banco",
    "Comprador",
    "Consignatario",
    "Empleado",
    "Multiple",
    "Organismo",
    "Proveedor",
    "Tarjeta de Credito",
)

TipoContacto = Literal[
    "Banco",
    "Comprador",
    "Consignatario",
    "Empleado",
    "Multiple",
    "Organismo",
    "Proveedor",
    "Tarjeta de Credito",
]


class Contacto(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    tipoContacto: str | None = None
    cuit: str | None = None
    esContratistaLabores: bool | None = None


class ContactosListResponse(BaseModel):
    items: list[Contacto]
    page: int
    pageSize: int
    total: int


class ContactoCreateRequest(BaseModel):
    razonSocial: str
    tipoContacto: TipoContacto
    cuit: str | None = None
    esContratistaLabores: bool = False


class ContactoUpdateRequest(BaseModel):
    razonSocial: str
    tipoContacto: TipoContacto
    cuit: str | None = None
    esContratistaLabores: bool = False
