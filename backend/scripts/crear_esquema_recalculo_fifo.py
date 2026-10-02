"""Esquema del recálculo FIFO de cuentas corrientes (032).

Crea las tablas `RecalculoFifo*` y `ContactoDuplicado` (data-model.md),
agrega `Compras.Suspendida` (FR-025) y amplía el CHECK de
`AplicacionesPago.Origen` para aceptar 'fifo-032'.

Es idempotente: cada sentencia comprueba primero si el objeto ya existe.
Antes de tocar nada hace un respaldo verificado de WC (Constitución II).
Nunca corre contra `LaHerencia`.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.crear_esquema_recalculo_fifo
"""

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

DDL = [
    """
IF OBJECT_ID('dbo.RecalculoFifoEjecucion', 'U') IS NULL
CREATE TABLE dbo.RecalculoFifoEjecucion (
    IdEjecucion   int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    Tipo          varchar(20)   NOT NULL CONSTRAINT CK_RFE_Tipo CHECK (Tipo IN ('simulacion','aplicacion','continua')),
    Estado        varchar(20)   NOT NULL CONSTRAINT CK_RFE_Estado CHECK (Estado IN ('simulada','aplicada','revertida','descartada')),
    Alcance       nvarchar(max) NOT NULL,
    FechaInicio   datetime2     NOT NULL DEFAULT SYSDATETIME(),
    FechaFin      datetime2     NULL,
    Usuario       nvarchar(100) NOT NULL,
    BackupArchivo nvarchar(400) NULL,
    Resumen       nvarchar(max) NULL
)
""",
    """
IF OBJECT_ID('dbo.RecalculoFifoContacto', 'U') IS NULL
CREATE TABLE dbo.RecalculoFifoContacto (
    IdEjecucion       int            NOT NULL,
    IdContacto        int            NOT NULL,
    ContactoUnificado int            NULL,
    Nombre            nvarchar(200)  NULL,
    Moneda            char(3)        NOT NULL,
    FacturadoAntes    decimal(18,2)  NOT NULL,
    PagadoAntes       decimal(18,2)  NOT NULL,
    AplicadoAntes     decimal(18,2)  NOT NULL,
    AplicadoDespues   decimal(18,2)  NOT NULL,
    AnticipoAbierto   decimal(18,2)  NOT NULL,
    Saldo             decimal(18,2)  NOT NULL,
    Volumen           decimal(18,2)  NOT NULL,
    CerrabaAntes      bit            NOT NULL,
    CierraDespues     bit            NOT NULL,
    Tendencia         varchar(10)    NOT NULL CONSTRAINT CK_RFC_Tendencia CHECK (Tendencia IN ('igual','mejora','empeora')),
    Controles         nvarchar(max)  NOT NULL,
    Marcas            nvarchar(max)  NOT NULL,
    Huella            char(64)       NOT NULL,
    EstadoExcepcion   varchar(20)    NOT NULL CONSTRAINT CK_RFC_Excepcion CHECK (EstadoExcepcion IN ('ninguna','pendiente','resuelta')),
    NotaExcepcion     nvarchar(500)  NULL,
    CONSTRAINT PK_RecalculoFifoContacto PRIMARY KEY (IdEjecucion, IdContacto),
    CONSTRAINT FK_RFC_Ejecucion FOREIGN KEY (IdEjecucion) REFERENCES dbo.RecalculoFifoEjecucion (IdEjecucion)
)
""",
    """
IF OBJECT_ID('dbo.RecalculoFifoAplicacion', 'U') IS NULL
CREATE TABLE dbo.RecalculoFifoAplicacion (
    IdRenglon          int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    IdEjecucion        int            NOT NULL,
    IdContacto         int            NOT NULL,
    OrigenCredito      varchar(40)    NOT NULL,
    IdCredito          bigint         NOT NULL,
    OrigenDebito       varchar(40)    NOT NULL,
    IdDebito           bigint         NOT NULL,
    NroCuota           int            NULL,
    ImporteAplicado    decimal(18,2)  NOT NULL,
    Moneda             char(3)        NOT NULL,
    ImporteArs         decimal(18,2)  NOT NULL,
    TipoCambio         decimal(18,6)  NULL,
    DiferenciaCambio   decimal(18,2)  NOT NULL DEFAULT 0,
    Regla              varchar(20)    NOT NULL CONSTRAINT CK_RFA_Regla CHECK (Regla IN
        ('cadena','eleccion','nota-origen','ajuste-tc','compensacion','fifo','anticipo','diferencia-cambio','reintegro')),
    FechaCredito       date           NULL,
    FechaVencimiento   date           NULL,
    CONSTRAINT FK_RFA_Ejecucion FOREIGN KEY (IdEjecucion) REFERENCES dbo.RecalculoFifoEjecucion (IdEjecucion)
)
""",
    """
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_RFA_Ejecucion_Contacto')
CREATE INDEX IX_RFA_Ejecucion_Contacto ON dbo.RecalculoFifoAplicacion (IdEjecucion, IdContacto)
""",
    """
IF OBJECT_ID('dbo.RecalculoFifoSaldoInicial', 'U') IS NULL
CREATE TABLE dbo.RecalculoFifoSaldoInicial (
    IdContacto        int            NOT NULL PRIMARY KEY,
    Importe           decimal(18,2)  NOT NULL,
    Moneda            char(3)        NOT NULL,
    Fecha             date           NOT NULL,
    Estado            varchar(20)    NOT NULL CONSTRAINT CK_RFSI_Estado CHECK (Estado IN ('estimado','confirmado','rechazado')),
    Usuario           nvarchar(100)  NULL,
    FechaConfirmacion datetime2      NULL
)
""",
    """
IF OBJECT_ID('dbo.RecalculoFifoCola', 'U') IS NULL
CREATE TABLE dbo.RecalculoFifoCola (
    IdContacto    int          NOT NULL PRIMARY KEY,
    Motivo        varchar(40)  NOT NULL,
    FechaEncolado datetime2    NOT NULL DEFAULT SYSDATETIME()
)
""",
    """
IF OBJECT_ID('dbo.ContactoDuplicado', 'U') IS NULL
CREATE TABLE dbo.ContactoDuplicado (
    IdContacto          int          NOT NULL,
    IdContactoPrincipal int          NOT NULL,
    Criterio            varchar(20)  NOT NULL CONSTRAINT CK_CD_Criterio CHECK (Criterio IN ('cuit','nombre')),
    Estado              varchar(20)  NOT NULL CONSTRAINT CK_CD_Estado CHECK (Estado IN ('propuesto','confirmado','descartado')),
    CONSTRAINT PK_ContactoDuplicado PRIMARY KEY (IdContacto, IdContactoPrincipal)
)
""",
    """
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.Compras') AND name = 'Suspendida')
ALTER TABLE dbo.Compras ADD Suspendida bit NOT NULL CONSTRAINT DF_Compras_Suspendida DEFAULT 0
""",
    # Amplía el CHECK de Origen para aceptar los vínculos generados por 032.
    """
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_AplicacionesPago_Origen_Conciliacion'
           AND definition NOT LIKE '%fifo-032%')
BEGIN
    ALTER TABLE dbo.AplicacionesPago DROP CONSTRAINT CK_AplicacionesPago_Origen_Conciliacion;
    ALTER TABLE dbo.AplicacionesPago ADD CONSTRAINT CK_AplicacionesPago_Origen_Conciliacion CHECK (
        Origen IN ('manual', 'automatica-exacta', 'automatica-mejor-esfuerzo', 'correccion-031', 'fifo-032'));
END
""",
    # Cuentas que Sergio marcó para revisar más adelante (2026-10-01).
    """
IF OBJECT_ID('dbo.CuentasARevisar', 'U') IS NULL
CREATE TABLE dbo.CuentasARevisar (
    IdContacto   int           NOT NULL PRIMARY KEY,
    Motivo       nvarchar(500) NOT NULL,
    FechaMarca   datetime2     NOT NULL DEFAULT SYSDATETIME(),
    Resuelta     bit           NOT NULL DEFAULT 0
)
""",
    # Orígenes que solo genera el recálculo: retenciones y compensaciones
    # documento↔documento (la NC o la venta que cancela una compra).
    """
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_AplicacionesPago_Origen'
           AND definition NOT LIKE '%comp-compra%')
BEGIN
    ALTER TABLE dbo.AplicacionesPago DROP CONSTRAINT CK_AplicacionesPago_Origen;
    ALTER TABLE dbo.AplicacionesPago ADD CONSTRAINT CK_AplicacionesPago_Origen CHECK (OrigenMovimiento IN (
        'bna', 'galicia', 'efectivo', 'valores-recibidos', 'valores-propios', 'tarjetas',
        'retenciones', 'ret-iva-granos', 'ret-ventas-hacienda',
        'comp-compra', 'comp-venta-granos', 'comp-venta-hacienda'));
END
""",
]


def main() -> None:
    _assert_target_is_wc()
    ruta = backup_verificado("032-esquema")
    print(f"Respaldo verificado: {ruta}")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        if cursor.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Este script solo corre sobre WC")
        for ddl in DDL:
            cursor.execute(ddl)
        print("Esquema 032 creado o ya existente.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
