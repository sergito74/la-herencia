# Quickstart: validar los informes de Cuentas Corrientes y Valores Propios (014)

## Prerrequisitos

- Backend y frontend corriendo igual que 004/003.
- Conexión de solo lectura a `WC` — esta feature no escribe nada.

## Escenario 1 — Exportar la cuenta corriente de un proveedor

1. Abrir la cuenta corriente de un proveedor con movimientos reales.
2. Exportar. Verificar que el `.xlsx` tiene una fila por movimiento, con los mismos valores que la pantalla.
3. Aplicar un filtro de fechas y exportar de nuevo — verificar que el Excel respeta el filtro.
4. Exportar un proveedor sin movimientos — verificar que el Excel se genera igual, sin filas de datos, sin error.

**Resultado esperado**: SC-001, FR-001.

## Escenario 2 — Saldos de todos los proveedores

1. Consultar `GET /api/cuentas-corrientes/saldos`. Verificar que aparecen todos los contactos con movimientos, incluidos los de saldo $0.
2. Elegir 5 contactos al azar del listado y comparar su saldo contra `GET /api/cuentas-corrientes/{idContacto}/movimientos` (saldo de la última fila) — deben coincidir exactamente.
3. Exportar el listado y verificar que el Excel tiene las mismas filas que la consulta.

**Resultado esperado**: SC-002, SC-003, FR-002, FR-003, FR-004.

## Escenario 3 — Valores propios

1. Consultar el listado de valores propios (medio `valores-propios` en tesorería). Verificar que ahora incluye `comentarios`.
2. Exportar a Excel y verificar que incluye todos los campos (número de cheque, fechas, importe, estado, número de cuenta, comentarios).
3. Aplicar un filtro de fechas y exportar de nuevo — verificar que el Excel respeta el filtro.

**Resultado esperado**: SC-004, FR-005, FR-006.

## Escenario 4 — Solo lectura

1. Revisar el código de los 3 endpoints nuevos y confirmar que ninguno usa `execute_write`/`execute_write_transaction`/`execute_insert_returning_id`.

**Resultado esperado**: SC-005, FR-007, FR-008.
