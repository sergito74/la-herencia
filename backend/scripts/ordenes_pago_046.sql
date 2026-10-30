IF OBJECT_ID('dbo.OrdenesPago') IS NULL
CREATE TABLE dbo.OrdenesPago (
 IdOrdenPago int IDENTITY PRIMARY KEY, IdContacto int NOT NULL,
 Fecha date NOT NULL, FechaPago date NOT NULL, ImporteTotal decimal(18,2) NOT NULL CHECK(ImporteTotal>0),
 Moneda varchar(3) NOT NULL DEFAULT 'ARS' CHECK(Moneda='ARS'),
 Estado varchar(12) NOT NULL DEFAULT 'Borrador' CHECK(Estado IN ('Borrador','Emitida','Pagada','Anulada')),
 Observaciones nvarchar(1000) NULL, Creado datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 CreadoPor nvarchar(100) NOT NULL, Modificado datetime2 NOT NULL DEFAULT SYSUTCDATETIME(), Version int NOT NULL DEFAULT 1
);
IF OBJECT_ID('dbo.OrdenesPago_Detalle') IS NULL
CREATE TABLE dbo.OrdenesPago_Detalle (
 IdDetalle int IDENTITY PRIMARY KEY, IdOrdenPago int NOT NULL REFERENCES dbo.OrdenesPago(IdOrdenPago),
 IdCompra int NOT NULL, Importe decimal(18,2) NOT NULL CHECK(Importe>0), UNIQUE(IdOrdenPago,IdCompra)
);
IF OBJECT_ID('dbo.OrdenesPago_Medios') IS NULL
CREATE TABLE dbo.OrdenesPago_Medios (
 IdMedio int IDENTITY PRIMARY KEY, IdOrdenPago int NOT NULL REFERENCES dbo.OrdenesPago(IdOrdenPago),
 Medio nvarchar(30) NOT NULL, Cuenta nvarchar(150) NOT NULL, Importe decimal(18,2) NOT NULL CHECK(Importe>0)
);
IF OBJECT_ID('dbo.RecibosProveedores') IS NULL
CREATE TABLE dbo.RecibosProveedores (
 IdRecibo int IDENTITY PRIMARY KEY, IdDocumentoNuevo int NOT NULL UNIQUE,
 IdContacto int NOT NULL, Numero nvarchar(50) NOT NULL, Fecha date NOT NULL,
 Total decimal(18,2) NOT NULL CHECK(Total>0), Moneda varchar(3) NOT NULL DEFAULT 'ARS' CHECK(Moneda='ARS'),
 RutaPdf nvarchar(400) NOT NULL, Sha256 char(64) NOT NULL UNIQUE,
 IdOrdenPago int NULL REFERENCES dbo.OrdenesPago(IdOrdenPago),
 Usuario nvarchar(100) NOT NULL, Creado datetime2 NOT NULL DEFAULT SYSUTCDATETIME(), UNIQUE(IdContacto,Numero)
);
IF OBJECT_ID('dbo.RecibosProveedores_Aplicaciones') IS NULL
CREATE TABLE dbo.RecibosProveedores_Aplicaciones (
 IdRecibo int NOT NULL REFERENCES dbo.RecibosProveedores(IdRecibo),
 IdAplicacion int NOT NULL UNIQUE REFERENCES dbo.AplicacionesPago(IdAplicacion), PRIMARY KEY(IdRecibo,IdAplicacion)
);
IF OBJECT_ID('dbo.OrdenesPago_Auditoria') IS NULL
CREATE TABLE dbo.OrdenesPago_Auditoria (
 IdAuditoria int IDENTITY PRIMARY KEY, IdOrdenPago int NULL, IdRecibo int NULL,
 Accion nvarchar(40) NOT NULL, Datos nvarchar(max) NOT NULL, Usuario nvarchar(100) NOT NULL,
 Fecha datetime2 NOT NULL DEFAULT SYSUTCDATETIME()
);
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name='CK_DocumentosNuevos_Modulo')
ALTER TABLE dbo.DocumentosNuevos DROP CONSTRAINT CK_DocumentosNuevos_Modulo;
ALTER TABLE dbo.DocumentosNuevos ADD CONSTRAINT CK_DocumentosNuevos_Modulo
CHECK(Modulo IN ('compras','impuestos','ventas','tesoreria','cuentas_corrientes','sin_clasificar','pagos'));
