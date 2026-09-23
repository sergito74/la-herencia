"""Acceso a `dbo.AuthUsuarios`/`dbo.AuthRoles` en `WC` (016-autenticacion)."""

from __future__ import annotations

from src.db.connection import fetch_one


def get_usuario_por_nombre(nombre: str) -> dict | None:
    return fetch_one(
        """
        SELECT u.IdUsuario, u.NombreUsuario, u.PasswordHash, u.Nombre,
               u.Activo, r.IdRol, r.Nombre AS RolNombre
        FROM dbo.AuthUsuarios u
        JOIN dbo.AuthRoles r ON r.IdRol = u.IdRol
        WHERE u.NombreUsuario = ?
        """,
        (nombre,),
    )


def get_usuario_por_id(id_usuario: int) -> dict | None:
    return fetch_one(
        """
        SELECT u.IdUsuario, u.NombreUsuario, u.PasswordHash, u.Nombre,
               u.Activo, r.IdRol, r.Nombre AS RolNombre
        FROM dbo.AuthUsuarios u
        JOIN dbo.AuthRoles r ON r.IdRol = u.IdRol
        WHERE u.IdUsuario = ?
        """,
        (id_usuario,),
    )
