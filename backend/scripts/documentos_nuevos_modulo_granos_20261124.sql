-- 24/11/2026: módulo de avisos propio para Ventas de granos. Las liquidaciones de granos que baja la bóveda
-- (Cargill) aparecían en Ventas de hacienda. Se agrega 'granos' a los módulos válidos y se mueven los avisos
-- de liquidaciones de Cargill que estaban en 'ventas'.
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name='CK_DocumentosNuevos_Modulo')
ALTER TABLE dbo.DocumentosNuevos DROP CONSTRAINT CK_DocumentosNuevos_Modulo;
ALTER TABLE dbo.DocumentosNuevos ADD CONSTRAINT CK_DocumentosNuevos_Modulo
CHECK(Modulo IN ('compras','impuestos','ventas','granos','tesoreria','cuentas_corrientes','sin_clasificar','pagos'));

UPDATE dbo.DocumentosNuevos
SET ModuloAnterior = Modulo, Modulo = 'granos', ModuloCambiado = SYSDATETIME(), ModuloCambiadoPor = 'sistema'
WHERE Modulo = 'ventas' AND Tipo = 'liquidacion' AND (IdPortal = 6 OR IdContacto = 258);
