IF COL_LENGTH('dbo.OrdenesContratistaFacturas','UsuarioConfirmacion') IS NULL
    ALTER TABLE dbo.OrdenesContratistaFacturas ADD UsuarioConfirmacion nvarchar(100) NOT NULL CONSTRAINT DF_OCF_Usuario DEFAULT N'';
IF COL_LENGTH('dbo.OrdenesContratistaFacturas','FechaConfirmacion') IS NULL
    ALTER TABLE dbo.OrdenesContratistaFacturas ADD FechaConfirmacion datetime2 NOT NULL CONSTRAINT DF_OCF_Fecha DEFAULT SYSUTCDATETIME();
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_OrdenesContratistaFacturas')
    ALTER TABLE dbo.OrdenesContratistaFacturas ADD CONSTRAINT UQ_OrdenesContratistaFacturas UNIQUE (IdOrdenTrabajo, IdCompra);
IF COL_LENGTH('dbo.ImputacionPropuestas','Origen') < 20
    ALTER TABLE dbo.ImputacionPropuestas ALTER COLUMN Origen varchar(20) NOT NULL;
IF OBJECT_ID('dbo.OrdenesContratistaSinOrden') IS NULL
CREATE TABLE dbo.OrdenesContratistaSinOrden (
    IdCompra int NOT NULL PRIMARY KEY,
    Motivo nvarchar(400) NOT NULL,
    Usuario nvarchar(100) NOT NULL,
    Fecha datetime2 NOT NULL CONSTRAINT DF_OCSO_Fecha DEFAULT SYSUTCDATETIME()
);
