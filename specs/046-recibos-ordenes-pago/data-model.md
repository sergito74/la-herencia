# Modelo 046

OrdenesPago: identidad secuencial utilizada como número OP (puede haber saltos por rollback); proveedor, fechas, total decimal(18,2), moneda ARS, estado, usuario, timestamps y versión de edición.
OrdenesPago_Detalle: FK cabecera, compra única por OP, importe positivo.
OrdenesPago_Medios: FK cabecera, medio previsto, cuenta descriptiva, importe positivo.
RecibosProveedores: aviso único, hash único y proveedor/número únicos; fecha, total, moneda, PDF, OP opcional, usuario. Se registra al confirmar, antes permanece en DocumentosNuevos como pendiente.
RecibosProveedores_Aplicaciones: FK recibo/aplicación, una aplicación no respalda dos recibos.
OrdenesPago_Auditoria: acciones y snapshot JSON, usuario y fecha.

Las órdenes no afectan el libro del proveedor. Las aplicaciones usan la fuente 019/031 y no crean pagos; la confirmación completa corre bajo el bloqueo de conciliación compartido. Reservas de OP emitidas se descuentan solo en planificación, nunca en saldo contable.
