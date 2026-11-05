IF OBJECT_ID('dbo.PagosEmitidosComprobantes') IS NULL
CREATE TABLE dbo.PagosEmitidosComprobantes (
    IdComprobante int IDENTITY(1,1) PRIMARY KEY,
    Archivo nvarchar(500) NOT NULL,
    Modificado datetime2 NOT NULL,
    Tipo varchar(20) NULL,              -- 'transferencia' | 'echeq' | NULL (no reconocido)
    Operacion varchar(40) NULL,
    NumeroCheque varchar(20) NULL,
    Fecha date NULL,                    -- envío (transferencia) o emisión (eCheq)
    FechaPago date NULL,                -- fecha en que debita el banco (eCheq: fecha de pago)
    Importe decimal(18,2) NULL,
    CuitDestino varchar(13) NULL,
    Destinatario nvarchar(200) NULL,
    Concepto nvarchar(300) NULL,
    IdContacto int NULL,
    Medio varchar(20) NULL,
    IdMovimiento int NULL,              -- débito del extracto que lo confirma
    Confirmado datetime2 NULL,
    Leido datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_PagosEmitidosComprobantes_Archivo UNIQUE (Archivo)
);
