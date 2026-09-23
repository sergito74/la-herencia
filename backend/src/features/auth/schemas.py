from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    usuario: str
    password: str


class MeResponse(BaseModel):
    idUsuario: int
    usuario: str
    nombre: str | None
    rol: str
