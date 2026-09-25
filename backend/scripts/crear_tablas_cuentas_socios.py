"""Crea el esquema del módulo de cuentas de socios/directores y condominio
(021-cuentas-socios). Idempotente: si las tablas ya existen no hace nada.
Nunca corre contra `LaHerencia`. Ver specs/021-cuentas-socios/data-model.md
para el detalle de cada columna.

Mismo patrón que `crear_tabla_aplicaciones_pago.py`: DDL con
`IF OBJECT_ID(...) IS NULL`, sin flag `--apply` (no hace falta).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tablas_cuentas_socios
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_SOCIOS = """
IF OBJECT_ID('dbo.Socios', 'U') IS NULL
CREATE TABLE dbo.Socios (
    IdSocio int NOT NULL IDENTITY PRIMARY KEY,
    Nombre  varchar(100) NOT NULL
)
"""

# Catálogo cerrado (spec FR-001) — 4 filas fijas, cargadas una sola vez.
SOCIOS_INICIALES = ["Sergio", "Lucy", "Cond LSC", "Ceci"]

DDL_MOVIMIENTOS_CUENTA_SOCIO = """
IF OBJECT_ID('dbo.MovimientosCuentaSocio', 'U') IS NULL
CREATE TABLE dbo.MovimientosCuentaSocio (
    IdMovimiento     int           NOT NULL IDENTITY PRIMARY KEY,
    IdSocio          int           NOT NULL,
    Tipo             varchar(20)   NOT NULL,
    Importe          money         NOT NULL,
    Fecha            datetime2     NOT NULL DEFAULT SYSUTCDATETIME(),
    Origen           varchar(20)   NULL,
    IdOrigen         int           NULL,
    Medio            varchar(60)   NULL,
    Motivo           nvarchar(255) NULL,
    Usuario          varchar(60)   NOT NULL,
    Anulada          bit           NOT NULL DEFAULT 0,
    MotivoAnulacion  nvarchar(255) NULL,
    UsuarioAnulacion varchar(60)   NULL,
    FechaAnulacion   datetime2     NULL,
    CONSTRAINT CK_MovimientosCuentaSocio_Tipo CHECK (Tipo IN ('AsignacionGasto', 'Devolucion')),
    CONSTRAINT CK_MovimientosCuentaSocio_Importe CHECK (Importe > 0)
)
"""

DDL_INDICE_SOCIO = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_MovimientosCuentaSocio_Socio' AND object_id = OBJECT_ID('dbo.MovimientosCuentaSocio')
)
CREATE INDEX IX_MovimientosCuentaSocio_Socio ON dbo.MovimientosCuentaSocio (IdSocio)
"""

# FR-009: impide una segunda asignación vigente sobre el mismo origen.
DDL_INDICE_UNICO_ORIGEN = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_MovimientosCuentaSocio_Origen' AND object_id = OBJECT_ID('dbo.MovimientosCuentaSocio')
)
CREATE UNIQUE INDEX UX_MovimientosCuentaSocio_Origen ON dbo.MovimientosCuentaSocio (Origen, IdOrigen)
WHERE Anulada = 0 AND Origen IS NOT NULL AND Tipo = 'AsignacionGasto'
"""

DDL_AUDITORIA_REFLEJO_SOCIO = """
IF OBJECT_ID('dbo.AuditoriaReflejoSocio', 'U') IS NULL
CREATE TABLE dbo.AuditoriaReflejoSocio (
    IdAuditoria int           NOT NULL IDENTITY PRIMARY KEY,
    Accion      varchar(30)   NOT NULL,
    IdMovimiento int          NOT NULL,
    IdSocio     int           NOT NULL,
    Usuario     varchar(60)   NOT NULL,
    Fecha       datetime2     NOT NULL DEFAULT SYSUTCDATETIME(),
    Detalle     nvarchar(255) NULL,
    CONSTRAINT CK_AuditoriaReflejoSocio_Accion CHECK (
        Accion IN ('Asignacion', 'ReversionAsignacion', 'Devolucion', 'ReversionDevolucion')
    )
)
"""


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        for ddl in (
            DDL_SOCIOS,
            DDL_MOVIMIENTOS_CUENTA_SOCIO,
            DDL_INDICE_SOCIO,
            DDL_INDICE_UNICO_ORIGEN,
            DDL_AUDITORIA_REFLEJO_SOCIO,
        ):
            cursor.execute(ddl)

        cursor.execute("SELECT COUNT(*) FROM dbo.Socios")
        if cursor.fetchone()[0] == 0:
            for nombre in SOCIOS_INICIALES:
                cursor.execute("INSERT INTO dbo.Socios (Nombre) VALUES (?)", (nombre,))
            print(f"OK: {len(SOCIOS_INICIALES)} socios iniciales cargados.")
        else:
            print("Socios ya tenía datos, no se volvió a cargar el catálogo inicial.")

        print("OK: esquema de cuentas de socios listo (creado o ya existente).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
