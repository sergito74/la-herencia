# Validación del módulo 014 — 2026-09-22

## Completado

- 391 tests de backend pasan (la única falla, `test_db_connection.py::test_execute_write_refuses_target_laherencia_case_insensitive`, es preexistente y no relacionada — ya confirmado en 013).
- `tsc --noEmit` del frontend pasa sin errores.
- **Escenario 1 (export cuenta corriente)**: `cuenta_corriente_xlsx(258, None, None)` (Cargill, mayor deuda real) generó un `.xlsx` de 617 filas con el saldo final `-454.876.182,64` idéntico al de `get_saldo(258)`.
- **Escenario 2 (saldos de todos los proveedores)**: `get_saldos_todos` devolvió 513 contactos reales de `WC`; 217 con saldo ~$0 (confirmando que no se filtran). Comparados 5 contactos al azar contra `get_saldo` individual: coinciden exactamente. Orden por `saldo` puso a Cargill (`-454.876.182,64`) primero, mayor deuda primero, correcto.
- **Escenario 3 (valores propios)**: `valores_propios_xlsx` exportó 1142 filas reales con el campo `comentarios` (antes no expuesto) poblado correctamente (ej. "Madelan").
- **Escenario 4 (solo lectura)**: confirmado por grep — ningún archivo nuevo de esta spec (`cuentas_corrientes/exportacion.py`, `cuentas_corrientes/repository.py::get_saldos_todos`, `tesoreria/exportacion.py`) usa `execute_write`/`execute_write_transaction`/`execute_insert_returning_id`.

## Bugs encontrados y corregidos durante la implementación

- Los índices de columna del helper `_cerrar(ws, formatos)` (reusado de `ordenes/exportacion.py`) son **0-based**, no 1-based — se detectó al ejecutar el test (`IndexError: tuple index out of range`) antes de llegar a tocar `WC`. Corregido en `cuentas_corrientes/exportacion.py` (`cuenta_corriente_xlsx`, `saldos_xlsx`).

## Pendiente

- No se probó visualmente en navegador (Playwright no disponible en este entorno, mismo límite que 013). La lógica de negocio y los 3 endpoints están verificados contra `WC` real por debajo de la UI.
