# Tareas — 033 Alta de boletas de impuestos

- [X] T001 Catálogo de organismos y tipos filtrados en backend/src/features/impuestos/repository.py (FR-001, FR-002)
- [X] T002 Validación, duplicado y alta/edición/baja en backend/src/features/impuestos/repository.py (FR-003, FR-004, FR-005, FR-007)
- [X] T003 Esquemas y endpoints en backend/src/features/impuestos/schemas.py y router.py
- [X] T004 Tests en backend/tests/test_impuestos_alta.py
- [X] T005 Servicio frontend en frontend/src/services/impuestosApi.ts
- [X] T006 Formulario frontend/src/components/impuestos/ImpuestoForm.tsx y rutas nueva/editar
- [X] T007 Botón "Nueva boleta" y enlace a edición en el listado (FR-006)
- [X] T008 Suite completa, build del frontend y reinicio de servicios

## Notas de implementación (2026-10-02)

- La boleta del pago de ARBA que motivó el pedido ya existía (1047,
  Inmobiliario 2023-2, $312.351,20); se vinculó con la línea de tarjeta.
- Hallazgo: `vw_MovimientosCuenta_Base` no mostraba los consumos de tarjeta
  vinculados a boletas de impuestos (025). Se agregó la rama
  'Tarjeta impuesto' (`backend/scripts/vista_tarjeta_impuestos.py`).
- Tests de contrato de 005 actualizados: el POST de boletas ahora existe.
