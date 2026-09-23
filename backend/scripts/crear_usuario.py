"""Alta o reseteo de un usuario de `WC` (016-autenticacion, Clarifications Q2).

Sin endpoint público de alta ni usuario de fábrica: el usuario real corre
este script una sola vez para crear su propia cuenta con su propia
contraseña. Si el usuario ya existe, resetea la contraseña y el rol.
Nunca imprime ni loguea la contraseña en texto plano.

Uso (desde backend/):
  .venv\\Scripts\\python.exe -m scripts.crear_usuario --usuario admin --password "..." --nombre "Sergio" --rol Administrador
"""

from __future__ import annotations

import argparse

from src.auth.passwords import hash_password
from src.db.connection import _assert_target_is_wc, execute_write, fetch_one

ROLES_VALIDOS = {"Administrador", "Lectura"}


def crear_o_actualizar_usuario(usuario: str, password: str, nombre: str | None, rol: str) -> str:
    if rol not in ROLES_VALIDOS:
        raise ValueError(f"Rol inválido: {rol!r} (válidos: {sorted(ROLES_VALIDOS)})")

    _assert_target_is_wc()

    fila_rol = fetch_one("SELECT IdRol FROM dbo.AuthRoles WHERE Nombre = ?", (rol,))
    if fila_rol is None:
        raise ValueError(f"Rol {rol!r} no existe en dbo.AuthRoles — correr crear_tablas_auth.py primero")
    id_rol = fila_rol["IdRol"]

    password_hash = hash_password(password)
    existente = fetch_one("SELECT IdUsuario FROM dbo.AuthUsuarios WHERE NombreUsuario = ?", (usuario,))

    if existente is None:
        execute_write(
            "INSERT INTO dbo.AuthUsuarios (NombreUsuario, PasswordHash, Nombre, IdRol, Activo) "
            "VALUES (?, ?, ?, ?, 1)",
            (usuario, password_hash, nombre, id_rol),
        )
        return f"Usuario '{usuario}' creado con rol '{rol}'."

    execute_write(
        "UPDATE dbo.AuthUsuarios SET PasswordHash = ?, Nombre = ?, IdRol = ?, Activo = 1 "
        "WHERE NombreUsuario = ?",
        (password_hash, nombre, id_rol, usuario),
    )
    return f"Usuario '{usuario}' actualizado (contraseña reseteada, rol '{rol}')."


def main() -> None:
    parser = argparse.ArgumentParser(description="Alta o reseteo de un usuario de La Herencia")
    parser.add_argument("--usuario", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--nombre", default=None)
    parser.add_argument("--rol", required=True, choices=sorted(ROLES_VALIDOS))
    args = parser.parse_args()

    mensaje = crear_o_actualizar_usuario(args.usuario, args.password, args.nombre, args.rol)
    print(mensaje)


if __name__ == "__main__":
    main()
