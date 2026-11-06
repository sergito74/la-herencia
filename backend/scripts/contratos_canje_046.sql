IF OBJECT_ID('dbo.ContratosCanje') IS NULL
CREATE TABLE dbo.ContratosCanje (
    IdContratoCanje int IDENTITY(1,1) PRIMARY KEY,
    IdContacto int NOT NULL,
    Numero nvarchar(30) NOT NULL,
    Fecha date NULL,
    Grano nvarchar(30) NOT NULL,
    Campania nvarchar(10) NULL,
    Kilos decimal(18,2) NULL,
    EntregaDesde date NULL,
    EntregaHasta date NULL,
    FijarHasta date NULL,
    Archivo nvarchar(500) NULL,
    CONSTRAINT UQ_ContratosCanje UNIQUE (IdContacto, Numero)
);
IF COL_LENGTH('dbo.Compras','IdContratoCanje') IS NULL ALTER TABLE dbo.Compras ADD IdContratoCanje int NULL;
