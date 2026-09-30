"""Crea el esquema de la migración histórica de Cajas Giamigli
(027-migracion-cajas-giamigli). Idempotente: si las tablas/columnas ya
existen no hace nada. Nunca corre contra `LaHerencia`. Ver
specs/027-migracion-cajas-giamigli/data-model.md para el detalle de cada
columna.

Backup verificado de `WC` tomado antes de correr este script:
WC_pre_027_cajas_giamigli_20260929_221602.bak (RESTORE VERIFYONLY
confirmado, 2026-09-29).

Mismo patrón que `crear_tablas_cuentas_socios.py`: DDL con
`IF OBJECT_ID(...) IS NULL` / `IF COL_LENGTH(...) IS NULL`, sin flag
`--apply` (no hace falta).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tablas_cajas_efectivo
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

# 021: MovimientosCuentaSocio pasa a soportar 3 componentes de importe
# (pesos, USD, Kg de carne) en vez de solo pesos — la planilla "Cajas
# Giamigli.xlsx" lleva estos 3 saldos por separado, sin convertir entre
# ellos (spec 027, Clarifications).
DDL_ALTER_MOVIMIENTOS_CUENTA_SOCIO_USD = """
IF COL_LENGTH('dbo.MovimientosCuentaSocio', 'ImporteUSD') IS NULL
ALTER TABLE dbo.MovimientosCuentaSocio
    ADD ImporteUSD money NOT NULL CONSTRAINT DF_MovimientosCuentaSocio_ImporteUSD DEFAULT 0
"""

DDL_ALTER_MOVIMIENTOS_CUENTA_SOCIO_KG_CARNE = """
IF COL_LENGTH('dbo.MovimientosCuentaSocio', 'ImporteKgCarne') IS NULL
ALTER TABLE dbo.MovimientosCuentaSocio
    ADD ImporteKgCarne decimal(14,3) NOT NULL CONSTRAINT DF_MovimientosCuentaSocio_ImporteKgCarne DEFAULT 0
"""

# El CHECK original (Importe > 0) ya no alcanza: un movimiento puede ser
# 100% en USD o en Kg de carne (trueque puro), con Importe (pesos) = 0.
DDL_DROP_CHECK_IMPORTE = """
IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_MovimientosCuentaSocio_Importe'
      AND parent_object_id = OBJECT_ID('dbo.MovimientosCuentaSocio')
)
ALTER TABLE dbo.MovimientosCuentaSocio DROP CONSTRAINT CK_MovimientosCuentaSocio_Importe
"""

DDL_CHECK_IMPORTE_ALGUNO = """
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_MovimientosCuentaSocio_ImporteAlguno'
      AND parent_object_id = OBJECT_ID('dbo.MovimientosCuentaSocio')
)
ALTER TABLE dbo.MovimientosCuentaSocio
    ADD CONSTRAINT CK_MovimientosCuentaSocio_ImporteAlguno
    CHECK (Importe > 0 OR ImporteUSD > 0 OR ImporteKgCarne > 0)
"""

# Tabla genérica para las 2 cajas de efectivo nuevas (Giamigli SA y caja
# chica del campo) — mismo concepto (historial + saldo de una caja),
# distinto conjunto de columnas de contexto según `Caja`.
DDL_MOVIMIENTOS_CAJA_EFECTIVO = """
IF OBJECT_ID('dbo.MovimientosCajaEfectivo', 'U') IS NULL
CREATE TABLE dbo.MovimientosCajaEfectivo (
    IdMovimiento          int            NOT NULL IDENTITY PRIMARY KEY,
    Caja                  varchar(20)    NOT NULL,
    Fecha                 datetime2      NOT NULL,
    Concepto              nvarchar(255)  NULL,
    Detalle               nvarchar(255)  NULL,
    Importe               money          NOT NULL,
    Cuenta                varchar(20)    NULL,
    FormaPago             varchar(60)    NULL,
    IdContactoRelacionado int            NULL,
    NumeroDocumento       nvarchar(60)   NULL,
    Usuario               varchar(60)    NOT NULL,
    FechaCarga            datetime2      NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT CK_MovimientosCajaEfectivo_Caja CHECK (Caja IN ('GiamigliSA', 'CampoChica'))
)
"""

DDL_INDICE_CAJA_EFECTIVO = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_MovimientosCajaEfectivo_Caja' AND object_id = OBJECT_ID('dbo.MovimientosCajaEfectivo')
)
CREATE INDEX IX_MovimientosCajaEfectivo_Caja ON dbo.MovimientosCajaEfectivo (Caja, Fecha)
"""

# Cola de revisión: filas de la planilla que no se pudieron migrar
# automáticamente con confianza (sin fecha, sin ningún importe, etc.) —
# spec FR-005/FR-006, nunca se pierden en silencio.
DDL_MIGRACION_REVISION = """
IF OBJECT_ID('dbo.MigracionCajasGiamigliRevision', 'U') IS NULL
CREATE TABLE dbo.MigracionCajasGiamigliRevision (
    IdRevision  int            NOT NULL IDENTITY PRIMARY KEY,
    Hoja        varchar(30)    NOT NULL,
    NumeroFila  int            NOT NULL,
    Motivo      nvarchar(255)  NOT NULL,
    DatosCrudos nvarchar(max)  NULL,
    FechaCarga  datetime2      NOT NULL DEFAULT SYSUTCDATETIME(),
    Resuelto    bit            NOT NULL DEFAULT 0
)
"""


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        for ddl in (
            DDL_ALTER_MOVIMIENTOS_CUENTA_SOCIO_USD,
            DDL_ALTER_MOVIMIENTOS_CUENTA_SOCIO_KG_CARNE,
            DDL_DROP_CHECK_IMPORTE,
            DDL_CHECK_IMPORTE_ALGUNO,
            DDL_MOVIMIENTOS_CAJA_EFECTIVO,
            DDL_INDICE_CAJA_EFECTIVO,
            DDL_MIGRACION_REVISION,
        ):
            cursor.execute(ddl)
        print("OK: esquema de migración de Cajas Giamigli listo (creado o ya existente).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
