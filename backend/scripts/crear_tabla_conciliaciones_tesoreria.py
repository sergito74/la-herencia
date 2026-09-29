"""Crea el esquema del módulo de Conciliación de Tesorería (023) e integra
sus conciliaciones en `vw_MovimientosCuenta_Base`. Idempotente: si la tabla
ya existe no la recrea; el `ALTER VIEW` reemplaza la vista completa pero
solo agrega una rama nueva al `UNION ALL` existente — ninguna rama actual
se modifica (ver specs/023-conciliacion-tesoreria/research.md §3).

Backup verificado de `WC` tomado antes de correr este script: ver
specs/023-conciliacion-tesoreria/tasks.md T003 — backup + RESTORE VERIFYONLY
confirmados el 2026-09-28 (archivo
WC_pre_023_conciliacion_20260928_122324.bak en el Backup path de la
instancia SQL Server local).

`ConciliacionesTesoreria` es insert-only (nunca UPDATE/DELETE), mismo
patrón que `MovimientosCuentaSocio` (021) y `ReasignacionesContacto` (022):
cada fila es una "parte" de la conciliación de un movimiento; el saldo
pendiente y el estado (sin conciliar / parcial / conciliado) se calculan
sumando estas filas, nunca se guardan (specs/023-conciliacion-tesoreria/
data-model.md).

La rama nueva de la vista distingue dos formas de imputar el importe según
el medio (ver research.md/data-model.md):
- bna / galicia / mercado-libre: bidireccional, el signo del movimiento
  original decide Deuda vs Crédito (mismo criterio que sus propias ramas).
- efectivo / valores-propios / valores-recibidos: siempre Crédito (son
  instrumentos de pago — mismo criterio que ya usan las ramas existentes
  "Pagos efectivo" y "Pagos/Cobros Valores Recibidos", de una sola
  dirección).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.crear_tabla_conciliaciones_tesoreria
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

DDL_TABLA_CONCILIACIONES = """
IF OBJECT_ID('dbo.ConciliacionesTesoreria', 'U') IS NULL
CREATE TABLE dbo.ConciliacionesTesoreria (
    IdConciliacion  int NOT NULL IDENTITY PRIMARY KEY,
    Medio           varchar(20) NOT NULL,
    IdMovimiento    bigint NOT NULL,
    IdContacto      int NOT NULL,
    Importe         money NOT NULL,
    Usuario         nvarchar(100) NOT NULL,
    Fecha           datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_ConciliacionesTesoreria_Contacto FOREIGN KEY (IdContacto) REFERENCES dbo.Contactos (IdContacto),
    CONSTRAINT CK_ConciliacionesTesoreria_Medio CHECK (Medio IN (
        'bna', 'galicia', 'mercado-libre', 'efectivo', 'valores-propios', 'valores-recibidos'
    )),
    CONSTRAINT CK_ConciliacionesTesoreria_Importe CHECK (Importe > 0)
)
"""

DDL_INDICE_CONCILIACIONES = """
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_ConciliacionesTesoreria_Movimiento' AND object_id = OBJECT_ID('dbo.ConciliacionesTesoreria')
)
CREATE INDEX IX_ConciliacionesTesoreria_Movimiento ON dbo.ConciliacionesTesoreria (Medio, IdMovimiento)
"""

# Rama nueva del UNION ALL — se inserta dentro de la subconsulta `base` de
# vw_MovimientosCuenta_Base, justo antes de ") AS base". Nunca se ejecuta
# aislada: siempre como parte del ALTER VIEW completo (ver más abajo).
_RAMA_CONCILIACIONES = """
UNION ALL

SELECT
    COALESCE(b.[Fecha / Hora Mov#], g.Fecha, ml.Fecha, pe.Fecha, vp.[Fecha emision], vr.[Fecha Emision]) AS Fecha,
    ct.IdContacto,
    co.[Razon Social],
    'Conciliación Tesorería' AS Documento,
    CAST(ct.IdMovimiento AS varchar(50)) AS [Nro Documento],
    CASE
        WHEN ct.Medio = 'bna' AND ISNULL(b.Importe, 0) > 0 THEN ct.Importe
        WHEN ct.Medio = 'galicia' AND ISNULL(g.[Créditos], 0) > ISNULL(g.[Débitos], 0) THEN ct.Importe
        WHEN ct.Medio = 'mercado-libre' AND ISNULL(ml.Importe, 0) > 0 THEN ct.Importe
        ELSE 0
    END AS Deuda,
    CASE
        WHEN ct.Medio = 'bna' AND ISNULL(b.Importe, 0) < 0 THEN ct.Importe
        WHEN ct.Medio = 'galicia' AND ISNULL(g.[Débitos], 0) > ISNULL(g.[Créditos], 0) THEN ct.Importe
        WHEN ct.Medio = 'mercado-libre' AND ISNULL(ml.Importe, 0) < 0 THEN ct.Importe
        WHEN ct.Medio IN ('efectivo', 'valores-propios', 'valores-recibidos') THEN ct.Importe
        ELSE 0
    END AS Credito,
    CAST('Conciliación Tesorería' AS varchar(50)) AS Origen,
    CAST(ct.IdConciliacion AS bigint) AS IdOrigen
FROM dbo.ConciliacionesTesoreria AS ct
INNER JOIN dbo.Contactos AS co ON co.IdContacto = ct.IdContacto
LEFT JOIN dbo.[Movimientos BNA] AS b ON ct.Medio = 'bna' AND b.IdMovimientoBNA = ct.IdMovimiento
LEFT JOIN dbo.[Movimientos Galicia] AS g ON ct.Medio = 'galicia' AND g.IdMovimiento = ct.IdMovimiento
LEFT JOIN dbo.[Movimientos Mercado Libre] AS ml ON ct.Medio = 'mercado-libre' AND ml.IdMovimiento = ct.IdMovimiento
LEFT JOIN dbo.[Pagos efectivo] AS pe ON ct.Medio = 'efectivo' AND pe.IdPagoEfectivo = ct.IdMovimiento
LEFT JOIN dbo.[Valores propios] AS vp ON ct.Medio = 'valores-propios' AND vp.IdValor = ct.IdMovimiento
LEFT JOIN dbo.[Valores Recibidos] AS vr ON ct.Medio = 'valores-recibidos' AND vr.IdValor = ct.IdMovimiento
"""

_MARCA_CIERRE_BASE = ") AS base"


def _construir_alter_view(definicion_actual: str) -> str:
    """Toma la definición VIGENTE de vw_MovimientosCuenta_Base (leída en
    caliente de sys, no hardcodeada) e inserta `_RAMA_CONCILIACIONES` justo
    antes del cierre de la subconsulta `base` — todo lo demás queda
    byte-a-byte igual, incluido el OUTER APPLY de 022 que envuelve el
    resultado completo (research.md §3: ya es genérico por
    (Origen, IdOrigen), no necesita cambios)."""
    if _MARCA_CIERRE_BASE not in definicion_actual:
        raise ValueError(
            "No se encontró ') AS base' en la definición vigente de la vista — "
            "puede haber cambiado de forma inesperada, revisar antes de continuar."
        )
    if "Conciliación Tesorería" in definicion_actual:
        raise ValueError(
            "La vista ya tiene una rama 'Conciliación Tesorería' — no reintentar el ALTER VIEW dos veces."
        )
    cuerpo = definicion_actual.replace(
        _MARCA_CIERRE_BASE, f"{_RAMA_CONCILIACIONES}\n{_MARCA_CIERRE_BASE}", 1
    )
    cuerpo = cuerpo.replace("CREATE VIEW dbo.vw_MovimientosCuenta_Base", "ALTER VIEW dbo.vw_MovimientosCuenta_Base", 1)
    return cuerpo


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()

        cursor.execute(DDL_TABLA_CONCILIACIONES)
        cursor.execute(DDL_INDICE_CONCILIACIONES)
        print("OK: tabla dbo.ConciliacionesTesoreria lista (creada o ya existente).")

        cursor.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))")
        definicion_actual = cursor.fetchone()[0]

        if "Conciliación Tesorería" in definicion_actual:
            print("OK: vw_MovimientosCuenta_Base ya tiene la rama de Conciliación Tesorería — nada que hacer.")
            return

        ddl_alter = _construir_alter_view(definicion_actual)
        cursor.execute(ddl_alter)
        print("OK: vw_MovimientosCuenta_Base ahora incluye dbo.ConciliacionesTesoreria.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
