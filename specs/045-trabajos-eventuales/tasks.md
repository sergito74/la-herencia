# Tareas 045 — Trabajos eventuales

## Preparación
- [x] T001 Relevar Excel y contratos existentes; documentar decisiones de Sergio en specs/045-trabajos-eventuales/spec.md y research.md.
- [x] T002 Definir plan, modelo, contrato y validación en specs/045-trabajos-eventuales/.

## Base compartida
- [ ] T003 Crear migración e importación idempotente en backend/scripts/trabajos_eventuales_045.py, con respaldo verificado, preservando 75 trabajos y total 2500558, estados y redondeos explícitos.
- [ ] T004 Crear modelos en backend/src/features/trabajos_eventuales/schemas.py: descripción 1..500, días >0 hasta 4 decimales, importes hasta 2 decimales, total >0.

## US1 — Administrar trabajos
- [ ] T005 [US1] Repositorio parametrizado de listado/detalle/alta/edición con auditoría en backend/src/features/trabajos_eventuales/repository.py.
- [ ] T006 [US1] Router y registro en backend/src/main.py con permisos existentes y errores/vacíos en español.
- [ ] T007 [US1] Listado, filtros, resumen y formulario en frontend/src/components/trabajos-eventuales/TrabajosEventuales.tsx y servicio tipado.

## US2 — Relacionar remuneraciones
- [ ] T008 [US2] Implementar candidatos, vínculo parcial y desvinculación atómicos en backend/src/features/trabajos_eventuales/repository.py; límites por ambos extremos, mismo trabajador y par único.
- [ ] T009 [US2] Integrar distribución en frontend/src/components/trabajos-eventuales/TrabajosEventuales.tsx y navegación exacta desde frontend/src/components/remuneraciones/RemuneracionesListado.tsx.

## US3 — Histórico
- [ ] T010 [US3] Aplicar migración/importación y registrar evidencia, contactos, respaldo, vínculos inequívocos y pendientes en specs/045-trabajos-eventuales/validacion.md.

## Verificación y cierre
- [ ] T011 Añadir comprobaciones de cálculos, límites, duplicados, permiso y contrato en backend/tests/test_trabajos_eventuales.py y backend/tests/contract/test_trabajos_eventuales_api.py.
- [ ] T012 Ejecutar pruebas enfocadas, build y verificación visual; registrar resultado y cambios en specs/045-trabajos-eventuales/validacion.md.

Dependencias: T001→T002→T003/T004→US1→US2→US3→T011/T012. Se implementa en una sesión sin delegación; no hay necesidad de trabajo paralelo de agentes. Cada fase mantiene uso verificable; no se da por completa una tarea hasta verificar su resultado.


## US4 — Adicional fuera de recibo de Sierra
- [ ] T013 [US4] Implementar fórmula Decimal y preservación de bonificación existente en backend/src/features/remuneraciones/adicional.py, contrato GET/POST /api/remuneraciones/{id}/adicional y tabla auxiliar en migración 045.
- [ ] T014 [US4] Mostrar componentes/redondeo automático a centena y guardar adicional en frontend/src/components/remuneraciones/AdicionalSierra.tsx, con pruebas en backend/tests/test_adicional_sierra.py y contrato simulado.
