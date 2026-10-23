# 040 — Caja de efectivo en dólares de Giamigli

Estado: implementada y verificada. Autorizado por Sergio el 23/10/2026.

## Decisiones confirmadas
- Caja física de tenencias y movimientos de billetes en dólares. Saldo, importes y arqueos siempre en US$; no es una conversión de la caja en pesos.
- Aportes y retiros a cuenta de socios: 100% US$, cero kg INMAG (respuesta expresa de Sergio). La equivalencia nominal en pesos del asiento de socio se informa por separado con dólar BNA a fecha, sin alterar los dólares físicos.
- Se agrega al menú Cajas y socios. Las otras hojas (Sindicatos, Elisabet, Sueldo) no fueron autorizadas como cajas.
- Historial: hoja Caja Efectivo Dolares del libro existente. Tiene 1.655 filas de formato pero solo seis movimientos fechados, del 30/01 al 27/04/2023; saldo US$360. Preservar fila, concepto, detalle e importes originales. No inferir aportes de socios de los nombres en ventas de dólares.

## Alcance y aceptación
1. Consultar saldo, libro paginado, filtros y detalle en US$ de una caja independiente.
2. Registrar entradas/salidas físicas en US$, aportes/retiros de socios y retiros de ganancias; previsualizar, advertir saldo negativo, guardar con idempotencia, anular y corregir manteniendo auditoría.
3. Arqueos por denominaciones en US$, con el mismo control de versiones de 038.
4. Comparar/importar la hoja de dólares sin duplicados, usando columna G (US$), nunca F (pesos).
5. Cargar los seis movimientos históricos una sola vez, con respaldo verificado, sin efectos nuevos en bancos, caja en pesos, cuentas de contactos ni socios.
6. No permitir que una operación en US$ use circuitos de pago, costos o bancos diseñados exclusivamente en pesos ni transferencias 1:1 entre monedas. El cambio de billetes por pesos no genera automáticamente una contrapartida monetaria sin contrato explícito de cambio y evidencia; registrar cada tenencia sin inventar relaciones históricas.
7. Rol Lectura conserva consulta e impide escrituras.

## Validación
Pruebas simuladas de contrato, moneda, socios, importación, idempotencia y anulación; compilación/lint frontend y navegador con API interceptada. Lectura real del esquema y saldos; pruebas sin escrituras reales.
