IF COL_LENGTH('dbo.Compras','CanjeGrano') IS NULL ALTER TABLE dbo.Compras ADD CanjeGrano nvarchar(30) NULL;
