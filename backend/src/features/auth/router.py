"""`POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
(016-autenticacion, FR-002/FR-003).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from src.auth.passwords import verify_password
from src.auth.tokens import crear_token, verificar_token
from src.features.auth.repository import get_usuario_por_id, get_usuario_por_nombre
from src.features.auth.schemas import LoginRequest, MeResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "la_herencia_session"


@router.post("/login")
async def login(body: LoginRequest, response: Response) -> MeResponse:
    usuario = get_usuario_por_nombre(body.usuario)
    if (
        usuario is None
        or not usuario["Activo"]
        or not verify_password(body.password, usuario["PasswordHash"])
    ):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    token = crear_token(id_usuario=usuario["IdUsuario"], rol=usuario["RolNombre"])
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=12 * 3600,
    )
    return MeResponse(
        idUsuario=usuario["IdUsuario"],
        usuario=usuario["NombreUsuario"],
        nombre=usuario["Nombre"],
        rol=usuario["RolNombre"],
    )


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)
    return {"status": "ok"}


@router.get("/me")
async def me(request: Request) -> MeResponse:
    token = request.cookies.get(COOKIE_NAME)
    payload = verificar_token(token) if token else None
    if payload is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")

    usuario = get_usuario_por_id(payload["idUsuario"])
    if usuario is None or not usuario["Activo"]:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")

    return MeResponse(
        idUsuario=usuario["IdUsuario"],
        usuario=usuario["NombreUsuario"],
        nombre=usuario["Nombre"],
        rol=usuario["RolNombre"],
    )
