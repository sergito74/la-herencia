# Tasks: Recibos de Proveedores y Órdenes de Pago (046)

**Branch**: `046-recibos-ordenes-pago` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Tareas de Implementación

### Fase 1: Base de Datos y Repositorio de Órdenes de Pago
- [X] **T001**: Tomar respaldo verificado de la base de datos `WC` con `COPY_ONLY` y `CHECKSUM` según constitución.
- [X] **T002**: Crear las tablas `dbo.OrdenesPago`, `dbo.OrdenesPago_Detalle` y `dbo.OrdenesPago_Medios` mediante script de migración SQL.
- [X] **T003**: Implementar `backend/src/features/ordenes_pago/schemas.py` con los modelos Pydantic de solicitud y respuesta de Órdenes de Pago.
- [X] **T004**: Implementar `backend/src/features/ordenes_pago/repository.py` (consulta de facturas pendientes con saldo, creación y edición de OP, emisión y anulación).
- [X] **T005**: Implementar tests unitarios y de contrato para el repositorio en `backend/tests/test_ordenes_pago_repository.py`.

### Fase 2: Ingesta y Clasificación de Recibos de Proveedores
- [X] **T006**: Configurar en `backend/src/features/documentos_nuevos/clasificador.py` el enrutamiento de tipo `recibo` hacia el módulo `pagos` (en vez de `compras`).
- [X] **T007**: Actualizar `backend/src/features/documentos_nuevos/carpetas.py` y `router.py` para admitir el módulo `pagos` con enlaces al nuevo panel.
- [X] **T008**: Validar la ingesta con tests en `backend/tests/documentos_nuevos/test_clasificador.py` y `test_carpetas.py`.

### Fase 3: Endpoints de la API y Vinculación
- [X] **T009**: Crear `backend/src/features/ordenes_pago/router.py` e incluirlo en `backend/src/main.py`.
- [X] **T010**: Implementar endpoint para vincular Recibo Oficial contra OP / débitos bancarios y generar las aplicaciones en `dbo.AplicacionesPago`.
- [X] **T011**: Ejecutar suite de pruebas de API en `backend/tests/test_ordenes_pago_api.py`.

### Fase 4: Frontend y Flujo de Usuario
- [X] **T012**: Crear servicio de cliente API en `frontend/src/services/ordenesPagoApi.ts`.
- [X] **T013**: Crear la vista principal `frontend/src/app/finanzas/ordenes-pago/page.tsx` con listado de Órdenes de Pago y bandeja de Recibos pendientes.
- [X] **T014**: Implementar el modal/formulario interactivo `FormularioOrdenPago.tsx` para confeccionar la OP seleccionando facturas de compra pendientes y medios de pago.
- [X] **T015**: Implementar el componente de vinculación de recibo (`VincularReciboModal.tsx`) con previsualización del PDF original.
- [X] **T016**: Agregar el acceso en el menú principal `frontend/src/components/layout/NavHeader.tsx` bajo Finanzas.
- [X] **T017**: Ejecutar build del frontend y pruebas de integración finales.


### Pendiente (fuera de esta entrega)
- [ ] **T018**: Cálculo de retenciones de Ganancias al preparar la OP con el simulador público RG 830 de ARCA (https://servicioscf.afip.gob.ar/calc-rg830/, sin login; Sergio 30/10/2026). Endpoints JSON `default.aspx/conceptosalcliente` y `default.aspx/CalcularRetencion` (sesión con GET previo). Base: pagos del mes al proveedor + pago actual, neto de IVA, menos retenciones ya practicadas en el mes; falta guardar por proveedor el concepto (bienes 78 / servicios 94) y si está inscripto.
- [ ] **T019**: Recibos con anticipos sin factura y con retenciones (vistos en Bayá Casal): hoy quedan pendientes en la bandeja; definir su aplicación.
