"""Cuerpos de entrada de los endpoints de Planificación Agrícola."""

from __future__ import annotations

from pydantic import BaseModel


class PlanAgricolaIn(BaseModel):
    idLote: int
    idCultivo: int
    idCampania: int
