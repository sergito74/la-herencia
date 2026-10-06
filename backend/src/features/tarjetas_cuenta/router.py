"""Cuenta de tarjetas, control de integridad y cruces — 034-cuenta-corriente-tarjetas."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/tarjetas-cuenta", tags=["tarjetas-cuenta"])
