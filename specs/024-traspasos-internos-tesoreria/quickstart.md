# Quickstart: Traspasos internos de Tesorería

## Prerrequisitos

- Backup verificado de `WC` antes de crear `TraspasosInternosTesoreria` y
  de modificar `esta_resuelto`/023 para consultarla (Constitution Check —
  cambio de esquema en producción).
- Backend con `--reload`, frontend reconstruido (`npm run build` + reinicio
  — `next start` no tiene hot-reload, ver sesión anterior).

## Escenario 1 — Vincular el caso real conocido (Historia 1)

1. Ir a Tesorería → Mercado Libre, movimiento `IdMovimiento=25`
   ("Ingreso de dinero Cuenta Banco de Galicia", $17.595,82, 2024-10-10).
   Cronometrar desde acá — SC-001 pide menos de 1 minuto hasta el paso 4.
2. Abrir la acción de traspaso interno — debe sugerir automáticamente
   Galicia `IdMovimiento=2151` ("Debito Debin Preautorizado", mismo
   importe, misma fecha) como candidata (research.md §3, verificado real).
3. Confirmar el vínculo.
4. Verificar: ambos movimientos (ML 25 y Galicia 2151) aparecen como
   `traspaso_interno` en sus listados respectivos.
5. Verificar que ningún saldo de cuenta corriente ni de caja cambió (SC-003)
   — comparar totales antes/después con `test_cuentas_corrientes_saldos.py`.

## Escenario 2 — No permitir doble resolución (Historia 2)

1. Elegir un movimiento Galicia que YA tenga contacto reconocido.
2. Intentar vincularlo como traspaso interno (como iniciador) → rechazado.
3. Elegir un movimiento sin resolver e intentar vincularlo usando como
   contraparte el movimiento del paso 1 (ya reconocido) → también
   rechazado (validación simétrica, Clarifications 2026-09-28).
4. Sobre el vínculo del Escenario 1, intentar conciliarlo (023) a un
   contacto → rechazado con 409.

## Escenario 3 — Deshacer un vínculo

1. Sobre el vínculo del Escenario 1, deshacerlo (`DELETE`).
2. Verificar: ambos movimientos vuelven a `sin_conciliar`, y el historial
   (`GET`, o una consulta directa a `TraspasosInternosTesoreria`) muestra
   las dos filas (`Vincular` y `Deshacer`) con usuario y fecha de cada una.
3. Volver a vincularlos (repetir Escenario 1) para confirmar que un
   movimiento previamente deshecho puede vincularse de nuevo sin quedar
   bloqueado por el vínculo viejo.

## Verificación de no regresión

- Correr toda la suite de 023-conciliacion-tesoreria — ningún test debe
  cambiar de resultado por la existencia de este módulo nuevo.
- Confirmar que `Tarjetas` sigue sin ofrecer esta acción en ningún listado.
