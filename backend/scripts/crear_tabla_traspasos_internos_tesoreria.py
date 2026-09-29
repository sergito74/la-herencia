"""Crea el esquema del módulo de Traspasos internos de Tesorería (024).
Idempotente (`IF OBJECT_ID(...) IS NULL`). A diferencia de 023, este módulo
nunca toca `vw_MovimientosCuenta_Base` — por diseño (FR-004) no genera
ningún efecto contable, así que no hace falta ningún `ALTER VIEW`.

Backup verificado de `WC` tomado antes de correr este script: reusado el
backup del mismo día (2026-09-29) del fix de tarjetas
(WC_backup_20260929_100632.bak) — no hubo ningún otro cambio de esquema
entremedio, sigue siendo representativo (Constitución Principio II).

`TraspasosInternosTesoreria` es insert-only (nunca UPDATE/DELETE), mismo
patrón que `ConciliacionesTesoreria` (023) y `ReasignacionesContacto` (022):
cada fila es un evento (`Vincular`/`Deshacer`); el vínculo activo de un
movimiento se calcula siempre a partir de la fila de mayor `IdEvento` para
ese par (specs/024-traspasos-internos-tesoreria/data-model.md).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tabla_traspasos_internos_tesoreria
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_TABLA = """
IF OBJECT_ID('dbo.TraspasosInternosTesoreria', 'U') IS NULL
CREATE TABLE dbo.TraspasosInternosTesoreria (
    IdEvento        int NOT NULL IDENTITY PRIMARY KEY,
    MedioA          varchar(20) NOT NULL,
    IdMovimientoA   bigint NOT NULL,
    MedioB          varchar(20) NOT NULL,
    IdMovimientoB   bigint NOT NULL,
    Accion          varchar(10) NOT NULL,
    Usuario         nvarchar(100) NOT NULL,
    Fecha           datetime NOT NULL DEFAULT getdate(),
    CONSTRAINT CK_TraspasosInternosTesoreria_MedioA CHECK (MedioA IN (
        'bna', 'galicia', 'mercado-libre', 'efectivo', 'valores-propios', 'valores-recibidos'
    )),
    CONSTRAINT CK_TraspasosInternosTesoreria_MedioB CHECK (MedioB IN (
        'bna', 'galicia', 'mercado-libre', 'efectivo', 'valores-propios', 'valores-recibidos'
    )),
    CONSTRAINT CK_TraspasosInternosTesoreria_Accion CHECK (Accion IN ('Vincular', 'Deshacer'))
)
"""

DDL_INDICE_A = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_TraspasosInternosTesoreria_A' AND object_id = OBJECT_ID('dbo.TraspasosInternosTesoreria')
)
CREATE INDEX IX_TraspasosInternosTesoreria_A ON dbo.TraspasosInternosTesoreria (MedioA, IdMovimientoA)
"""

DDL_INDICE_B = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_TraspasosInternosTesoreria_B' AND object_id = OBJECT_ID('dbo.TraspasosInternosTesoreria')
)
CREATE INDEX IX_TraspasosInternosTesoreria_B ON dbo.TraspasosInternosTesoreria (MedioB, IdMovimientoB)
"""


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute(DDL_TABLA)
        cursor.execute(DDL_INDICE_A)
        cursor.execute(DDL_INDICE_B)
        print("OK: tabla dbo.TraspasosInternosTesoreria lista (creada o ya existente).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
