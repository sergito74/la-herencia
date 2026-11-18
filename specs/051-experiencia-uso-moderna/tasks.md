# Tasks: Experiencia de uso moderna (051)

Plan resumido: solo frontend + un endpoint de lectura (`/api/inicio`) que reúne cálculos existentes, con caché de 10 min en segundo plano. Componentes nuevos en `frontend/src/components/ui`.

## US1 — Inicio "Para hacer hoy" (P1)
- [X] T001 [US1] Resumen de lectura con caché en segundo plano en backend/src/features/inicio/service.py y router.py (FR-001…006, FR-016)
- [X] T002 [US1] Test: fuente rota no tumba el Inicio, lo que da 0 no se muestra en backend/tests/test_inicio_051.py
- [X] T003 [US1] Pantalla de Inicio (pendientes, indicadores, flujo, campaña, accesos; esqueletos mientras calcula) en frontend/src/app/page.tsx (FR-001…007)

## US2 — Fechas con atajos de campaña (P2)
- [ ] T004 [US2] Componente RangoFechas con atajos en frontend/src/components/ui/RangoFechas.tsx (FR-008)
- [ ] T005 [US2] Reemplazar pares de fechas en Tesorería, Cuentas corrientes, Compras, Flujo de caja y Trabajos eventuales (FR-009)

## US3 — Panel lateral de detalle (P3)
- [ ] T006 [US3] DataTable con onRowClick y acciones de fila en menú (FR-010, FR-012)
- [ ] T007 [US3] Panel de detalle en Compras, Ventas de hacienda, Trabajos eventuales, Saldos y Órdenes, con Esc y acceso a pantalla completa (FR-010, FR-011)

## US4 — Búsqueda global Ctrl+K (P4)
- [ ] T008 [US4] Endpoint de búsqueda de lectura (contactos, compras por número, productos, lotes, órdenes) (FR-013)
- [ ] T009 [US4] Paleta de búsqueda con teclado, pantallas y acciones, montada en el layout (FR-013, FR-014)
