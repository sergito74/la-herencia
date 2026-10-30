# Modelo 046

OrdenesPago: identidad secuencial utilizada como número OP (puede haber saltos por rollback); proveedor, fechas, total decimal(18,2), moneda ARS, estado, usuario, timestamps y versión de edición.
OrdenesPago_Detalle: FK cabecera, compra única por OP, importe positivo.
OrdenesPago_Medios: FK cabecera, medio previsto, cuenta descriptiva, importe positivo.
RecibosProveedores: aviso único, hash único y proveedor/número únicos; fecha, total, moneda, PDF, OP opcional, usuario. Se registra al confirmar, antes permanece en DocumentosNuevos como pendiente.
RecibosProveedores_Aplicaciones: FK recibo/aplicación, una aplicación no respalda dos recibos.
OrdenesPago_Auditoria: acciones y snapshot JSON, usuario y fecha.
OrdenesPago.RetencionGanancias: suma de la retención confirmada; medios = facturas − retención.
OrdenesPago_Retenciones: una fila por régimen y OP (única): régimen, concepto, base del pago, pagos y retenciones anteriores del mes, alícuota, no sujeto, retención (≥0) y la respuesta del simulador como evidencia.
RecibosProveedores.Retencion / Anticipo / CertificadoRetencion: total = aplicaciones + retención + anticipo.
RetencionesGanancias_Padron: CUIT (PK), denominación, Ganancias (AC/NI/EX/NC), IVA, monotributo, empleador, fecha de actualización. Copia filtrada del padrón público de ARCA.
RetencionesGanancias_Conceptos: rubro (PK) → régimen (vacío = no retiene), estado Borrador/Validado contador/Ratificado estudio, observaciones, usuario, fecha.
RetencionesGanancias_Exclusiones: proveedor, vigencia desde/hasta (hasta ≥ desde), observaciones, usuario.

Las órdenes no afectan el libro del proveedor. Las aplicaciones usan la fuente 019/031 y no crean pagos; la confirmación completa corre bajo el bloqueo de conciliación compartido. Reservas de OP emitidas se descuentan solo en planificación, nunca en saldo contable.
