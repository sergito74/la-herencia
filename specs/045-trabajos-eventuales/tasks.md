# Tareas 045 — Trabajos eventuales

## Preparación
- [x] T001 Relevar Excel y contratos existentes; documentar decisiones de Sergio en specs/045-trabajos-eventuales/spec.md y research.md.
- [x] T002 Definir plan, modelo, contrato y validación en specs/045-trabajos-eventuales/.

## Base compartida
- [x] T003 Crear migración e importación idempotente en backend/scripts/trabajos_eventuales_045.py, con respaldo verificado, preservando los trabajos (78 trabajos reales, total $2.893.758), estados y redondeos explícitos.
- [x] T004 Crear modelos en backend/src/features/trabajos_eventuales/schemas.py: descripción 1..500, días >0 hasta 4 decimales, importes hasta 2 decimales, total >0.

## US1 — Administrar trabajos
- [x] T005 [US1] Repositorio parametrizado de listado/detalle/alta/edición con auditoría en backend/src/features/trabajos_eventuales/repository.py.
- [x] T006 [US1] Router y registro en backend/src/main.py con permisos existentes y errores/vacíos en español.
- [x] T007 [US1] Listado, filtros, resumen y formulario en frontend/src/components/trabajos-eventuales/TrabajosEventuales.tsx y servicio tipado.

## US2 — Relacionar remuneraciones
- [x] T008 [US2] Implementar candidatos, vínculo parcial y desvinculación atómicos en backend/src/features/trabajos_eventuales/repository.py; límites por ambos extremos, mismo trabajador y par único.
- [x] T009 [US2] Integrar distribución en frontend/src/components/trabajos-eventuales/TrabajosEventuales.tsx y navegación exacta desde frontend/src/components/remuneraciones/RemuneracionesListado.tsx.

## US3 — Histórico
- [x] T010 [US3] Aplicar migración/importación y registrar evidencia, contactos, respaldo, vínculos inequívocos y pendientes en specs/045-trabajos-eventuales/validacion.md.

## Verificación y cierre
- [x] T011 Añadir comprobaciones de cálculos, límites, duplicados, permiso y contrato en backend/tests/test_trabajos_eventuales.py y backend/tests/contract/test_trabajos_eventuales_api.py.
- [x] T012 Ejecutar pruebas enfocadas, build y verificación visual; registrar resultado y cambios en specs/045-trabajos-eventuales/validacion.md.

## US4 — Adicional fuera de recibo de Sierra
- [x] T013 [US4] Implementar fórmula Decimal y preservación de bonificación existente en backend/src/features/remuneraciones/adicional.py, contrato GET/POST /api/remuneraciones/{id}/adicional y tabla auxiliar en migración 045.
- [x] T014 [US4] Mostrar componentes/redondeo automático a centena y guardar adicional en frontend/src/components/remuneraciones/AdicionalSierra.tsx, con pruebas en backend/tests/test_adicional_sierra.py y contrato simulado.
