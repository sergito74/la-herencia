"""Crea `dbo.AuthRoles` y `dbo.AuthUsuarios` en `WC` (016-autenticacion).

Nombres `AuthRoles`/`AuthUsuarios` (no `Roles`/`Usuarios`) porque WC ya
tiene tablas `roles`/`usuarios` de origen desconocido, con un esquema
completamente distinto (uniqueidentifier, empresa_id, row_version — mismo
patrón que `rubros_compra`/`centros_costo`, ver specs/002-compras/data-model.md).
SQL Server no distingue mayúsculas en nombres de tabla, así que un
`CREATE TABLE dbo.Roles` colisiona con `dbo.roles` en vez de crear una
tabla nueva.

Idempotente: si las tablas ya existen no hace nada. Nunca corre contra
`LaHerencia`. No crea ningún usuario — eso lo hace
`backend/scripts/crear_usuario.py` (Clarifications Q2, sin usuario de
fábrica).
Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tablas_auth
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_ROLES = """
IF OBJECT_ID('dbo.AuthRoles', 'U') IS NULL
CREATE TABLE dbo.AuthRoles (
    IdRol  int          NOT NULL IDENTITY PRIMARY KEY,
    Nombre varchar(20)  NOT NULL UNIQUE
)
"""

SEED_ROLES = """
IF NOT EXISTS (SELECT 1 FROM dbo.AuthRoles WHERE Nombre = 'Administrador')
INSERT INTO dbo.AuthRoles (Nombre) VALUES ('Administrador');
IF NOT EXISTS (SELECT 1 FROM dbo.AuthRoles WHERE Nombre = 'Lectura')
INSERT INTO dbo.AuthRoles (Nombre) VALUES ('Lectura');
"""

DDL_USUARIOS = """
IF OBJECT_ID('dbo.AuthUsuarios', 'U') IS NULL
CREATE TABLE dbo.AuthUsuarios (
    IdUsuario     int           NOT NULL IDENTITY PRIMARY KEY,
    NombreUsuario varchar(60)   NOT NULL UNIQUE,
    PasswordHash  varchar(200)  NOT NULL,
    Nombre        nvarchar(120) NULL,
    IdRol         int           NOT NULL REFERENCES dbo.AuthRoles(IdRol),
    Activo        bit           NOT NULL DEFAULT 1,
    FechaCreacion datetime2     NOT NULL DEFAULT SYSUTCDATETIME()
)
"""


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute(DDL_ROLES)
        cursor.execute(SEED_ROLES)
        cursor.execute(DDL_USUARIOS)
    finally:
        conn.close()
    print(f"OK: dbo.AuthRoles y dbo.AuthUsuarios listas en {DATABASE} (roles Administrador/Lectura sembrados).")


if __name__ == "__main__":
    main()
