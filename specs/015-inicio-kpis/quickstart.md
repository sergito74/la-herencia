# Quickstart: validar los indicadores de inicio (015)

## Prerrequisitos

- Backend y frontend corriendo. Sin cambios de escritura — esta feature es 100% lectura.

## Escenario 1 — Indicadores reales

1. Abrir la pantalla de inicio (`/`).
2. Verificar "Deuda total a proveedores": comparar contra la suma manual de saldos negativos de `/finanzas/cuentas-corrientes/saldos` (014).
3. Verificar "Líneas de tarjeta sin conciliar": comparar contra el total de `/finanzas/tarjetas/conciliacion` (009).
4. Verificar el indicador de campaña: comparar contra `/produccion/resultado-cultivo` con la campaña actual preseleccionada (012).

**Resultado esperado**: SC-001, SC-002.

## Escenario 2 — Aislamiento de fallas

1. Simular que uno de los 3 endpoints falla (ej. cortar el backend momentáneamente mientras carga uno).
2. Verificar que el resto de la pantalla (menú de procesos, otros indicadores) sigue siendo usable.

**Resultado esperado**: SC-004, FR-005.

## Escenario 3 — Contenido actualizado

1. Comparar el menú de "Producción" y "Finanzas" de la pantalla de inicio contra `NavHeader.tsx`.
2. Verificar que no queda ningún mensaje de "próximamente" para un módulo ya migrado.

**Resultado esperado**: SC-003, FR-006, FR-007.
