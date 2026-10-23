# Modelo
Se reutilizan las tablas y relaciones de 038. El nuevo valor de Caja es GiamigliUSD, moneda USD fija. Se amplían únicamente los CHECK de MovimientosCajaEfectivo y ArqueosCajaEfectivo; no se cambia el significado de las cajas anteriores.

OperacionesCajaEfectivo.Solicitud y Contexto preservan tipo, moneda derivada por caja y cotización del socio cuando corresponde. EfectosOperacionCaja enlaza el movimiento de socio; la anulación existente revierte sus efectos. Los ingresos/egresos físicos no crean Pagos efectivo.

Las seis filas históricas se guardan en MovimientosCajaEfectivo con FilaPlanilla 2–7, Usuario Migracion040: Caja Efectivo Dolares, cuenta B y concepto/detalle originales. No tienen operación nueva ni vínculo inferido a socios. El script es idempotente por Caja+FilaPlanilla y valida contenido previo exacto, saldo corrido de la fuente y que ninguna caja en pesos cambie. La fuente permanece intacta.
