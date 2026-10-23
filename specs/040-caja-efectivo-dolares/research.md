# Relevamiento y decisiones — 23/10/2026

- Entrada: traspaso e970633, leído con guía y Constitución. Working tree inicialmente limpio.
- Sergio confirmó caja física de tenencias/movimientos USD y socios 100% dólares sin reparto INMAG.
- Fuente leída con openpyxl read_only/data_only, sin guardarla: Cajas Giamigli.xlsx, hoja Caja Efectivo Dolares. 1.655 filas máximas, solo seis no vacías/fechadas. Columna F es contravalor en pesos: no es importe USD ni número de documento; columna G es movimiento USD, H saldo corrido. Saldo final comprobado US$360.
- Esquema real WC: dos CHECK de Caja limitaban a tres cajas. Se amplían con GiamigliUSD; no se crean tablas ni se modifica la vista de cuentas corrientes.
- Se reutiliza el coordinador atómico e idempotente 038. Las entradas/salidas físicas no crean pagos a contactos ni inferencias de socio. La equivalencia nominal para el socio usa dólar BNA a fecha, se conserva como dato separado y no afecta tenencia USD.
- Las operaciones existentes en pesos siguen igual. Cruces de monedas, conciliaciones bancarias y pagos fiscales USD requieren un contrato adicional antes de habilitarlos; no se conectan automáticamente por importe o nombres históricos.
- En el rediseño anterior, Corregir solo recuperaba campos básicos. Se extendió el formulario para recuperar también aplicaciones, contraparte, banco/evidencia, sueldo, compra particular y repartos de la Solicitud original; sigue exigiendo una previsualización nueva.
- El primer intento de inspección rechazó el patrón de búsqueda del CHECK, sin escrituras. Se corrigió a CHARINDEX con nombre de columna literal; la migración aplicada tiene respaldo previo, transacción SQL explícita y evidencia local.
- Para el navegador se actualizaron selectores del recorrido a los botones/pestañas actuales. El servidor previo compartía .next y producía recargas/404 intermitentes. Se agregó NEXT_DIST_DIR opcional para aislar la compilación UI; el funcionamiento normal conserva .next. Las pruebas interceptan todas las API y prohíben acceso a WC.
