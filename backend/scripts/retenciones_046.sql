IF OBJECT_ID('dbo.RetencionesGanancias_Padron') IS NULL
CREATE TABLE dbo.RetencionesGanancias_Padron (
 CUIT char(11) NOT NULL PRIMARY KEY, Denominacion nvarchar(40) NULL, Ganancias char(2) NULL, IVA char(2) NULL,
 Monotributo varchar(2) NULL, Empleador char(1) NULL, Actualizado date NOT NULL
);
IF OBJECT_ID('dbo.RetencionesGanancias_Conceptos') IS NULL
CREATE TABLE dbo.RetencionesGanancias_Conceptos (
 IdRubro int NOT NULL PRIMARY KEY, CodRegimen int NULL, Estado varchar(20) NOT NULL DEFAULT 'Borrador'
 CHECK(Estado IN ('Borrador','Validado contador','Ratificado estudio')),
 Observaciones nvarchar(300) NULL, Usuario nvarchar(100) NOT NULL, Modificado datetime2 NOT NULL DEFAULT SYSUTCDATETIME()
);
IF OBJECT_ID('dbo.RetencionesGanancias_Exclusiones') IS NULL
CREATE TABLE dbo.RetencionesGanancias_Exclusiones (
 IdExclusion int IDENTITY PRIMARY KEY, IdContacto int NOT NULL, Desde date NOT NULL, Hasta date NOT NULL,
 Observaciones nvarchar(300) NULL, Usuario nvarchar(100) NOT NULL, Creado datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 CHECK(Hasta>=Desde)
);
IF OBJECT_ID('dbo.OrdenesPago_Retenciones') IS NULL
CREATE TABLE dbo.OrdenesPago_Retenciones (
 IdRetencionOP int IDENTITY PRIMARY KEY, IdOrdenPago int NOT NULL REFERENCES dbo.OrdenesPago(IdOrdenPago),
 CodRegimen int NOT NULL, Concepto nvarchar(200) NOT NULL, BasePago decimal(18,2) NOT NULL,
 PagosAnteriores decimal(18,2) NOT NULL, RetencionesAnteriores decimal(18,2) NOT NULL,
 Alicuota decimal(9,4) NOT NULL, NoSujeto decimal(18,2) NOT NULL, Retencion decimal(18,2) NOT NULL CHECK(Retencion>=0),
 Simulador nvarchar(max) NOT NULL, UNIQUE(IdOrdenPago,CodRegimen)
);
IF COL_LENGTH('dbo.OrdenesPago','RetencionGanancias') IS NULL
ALTER TABLE dbo.OrdenesPago ADD RetencionGanancias decimal(18,2) NOT NULL CONSTRAINT DF_OrdenesPago_Retencion DEFAULT 0;
