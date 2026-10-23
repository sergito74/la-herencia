# Plan
Extender el módulo 038 sin un libro paralelo. Slug giamigli-dolares, valor SQL GiamigliUSD. La moneda se deriva de la caja (no del cliente). Ampliar CHECKs existentes con respaldo y transacción. Reutilizar operaciones auditadas y arqueos; entradas/salidas USD no crean Pagos efectivo ni aplicaciones. Aportes/retiros crean MovimientoSocio con ImporteUSD exacto y kg=0, y equivalencia nominal pesos BNA trazable. Importador reconoce la hoja dólar, cuenta A/B y columna G.

Contratos primero: validación rechaza cruces de monedas y circuitos en pesos en caja USD. GETs existentes aceptan nuevo slug; POSTs usan ingreso_dolares / egreso_dolares o los tipos de socio existentes. Ningún total suma distintas monedas.
