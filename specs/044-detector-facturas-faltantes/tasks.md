# Tasks: Detector de facturas faltantes de proveedores

**Input**: Design documents from `specs/044-detector-facturas-faltantes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: incluidos (Constitución V: contrato verificado antes de la UI).

## Phase 1: Setup

- [x] T001 Crear el módulo vacío backend/src/features/facturas_faltantes/__init__.py y registrar el router en backend/src/main.py
- [x] T002 Script DDL idempotente con respaldo verificado previo en backend/scripts/crear_esquema_detector_044.py: FacturasFaltantesPerfil (IdContacto int PK, CicloDias int NULL, SinCiclo bit, MargenDias int NULL, DadoDeBaja bit, PreguntaBajaFecha datetime2 NULL), FacturasFaltantesAlarmas (Clave nvarchar(120) UNIQUE, Decision nvarchar(20), Motivo nvarchar(255) obligatorio), FacturasFaltantesMarcas (Estado 'abierta'/'cerrada', índice único filtrado de marca abierta por OrigenPago+IdPago)

## Phase 2: Foundational

- [x] T003 Motor puro (sin SQL) en backend/src/features/facturas_faltantes/motor.py: ciclo por mediana de distancias de las últimas 12–24 facturas (mínimo 6 en 24 meses, ±25%, ≥70% de distancias en rango), casilleros de período por secuencia, estados llegó/pendiente/atrasada/baja (margen 15/25 días, 3 ciclos), monto esperado (mediana últimas 3) y cambio de monto >30%
- [x] T004 [P] Pruebas del motor con fixtures en backend/tests/test_facturas_faltantes_motor_044.py: mensual con dos comprobantes en un mes (Movistar jun-2025), bimestral sin falsos atrasos, fecha errónea aislada, menos de 6 facturas = sin ciclo, 3 ciclos = baja
- [x] T005 Lecturas en bloque en backend/src/features/facturas_faltantes/repository.py: comprobantes de compra por contacto (fecha, número, tipo, importe en pesos), pagos de vw_MovimientosCuenta_Saldo, vínculos de features/vinculos/fuente, retenciones, remitos sin factura; exclusiones (San Justo, socios 375/390/549/5670, contacto 0)

## Phase 3: User Story 1 - Tablero de facturas esperadas (P1) 🎯 MVP

**Goal**: estados del período por proveedor recurrente. **Independent Test**: tablero real con Movistar jun-2025 faltante y Coop. Eléctrica sin falsos atrasos.

- [x] T006 [US1] Servicio del tablero con cache de 10 min en backend/src/features/facturas_faltantes/service.py
- [x] T007 [US1] Schemas y GET /api/facturas-faltantes/tablero en backend/src/features/facturas_faltantes/{schemas,router}.py según contracts/api.md
- [x] T008 [US1] Prueba de contrato del tablero en backend/tests/test_facturas_faltantes_contrato_044.py (antes de la UI)
- [x] T009 [P] [US1] Cliente API en frontend/src/services/facturasFaltantesApi.ts
- [x] T010 [US1] Página frontend/src/app/finanzas/facturas-esperadas/page.tsx y componente frontend/src/components/facturas-faltantes/TableroFacturasEsperadas.tsx (rótulo "a verificar", sin ids, enlaces a cuenta y a cargar compra) y entrada en NavHeader

## Phase 4: User Story 2 - Alarmas no recurrentes (P2)

- [x] T011 [US2] Señales en motor.py y service.py: pago sin factura compatible (±60 días, igual o suma de hasta 3), saldo a favor >90 días, retención sin factura ±30 días, remito sin factura >60 días; clave estable por señal
- [x] T012 [US2] GET /alarmas paginado (pageSize ≤ 200) y POST /alarmas/{clave}/descartar (motivo 1–255) con prueba de contrato
- [x] T013 [US2] Componente frontend/src/components/facturas-faltantes/AlarmasFaltantes.tsx (pestaña del tablero, descartar con motivo, SoloLectura)

## Phase 5: User Story 3 - Marcas "a cuenta, falta factura" (P2)

- [x] T014 [US3] GET/POST/DELETE /marcas (409 si ya hay una abierta para el pago) y cierre automático con factura compatible en service.py; prueba de contrato y control saldo antes = después
- [x] T015 [US3] Acción "Marcar falta factura" desde la alarma y lista de marcas en la UI

## Phase 6: User Story 4 - Aviso al cargar un pago sin factura (P3)

- [x] T016 [US4] GET /pago-sin-factura y aviso no bloqueante con opción de marcar en el formulario de pagos existente

## Phase 7: User Story 5 - Cierre de mes y perfil (P3)

- [x] T017 [US5] PUT /perfil/{idContacto}, POST /perfil/{idContacto}/baja y edición de ciclo en la fila del tablero
- [x] T018 [US5] GET /resumen-mensual e integración en el resumen de la rutina 043 (backend/src/features/documentos_nuevos/router.py y su banner)

## Phase 8: Polish

- [x] T019 Validación con datos reales (quickstart.md), tsc/eslint, recorrido UI con API interceptada; registrar evidencia en quickstart.md
- [x] T020 Revisar diff, commit y push

## Dependencies

Setup → Foundational (T003–T005) → US1 → (US2, US3 en paralelo; US3 usa alarmas de US2 para la acción) → US4, US5 → Polish.

## Parallel Examples

T004 junto con T005; T009 junto con T006–T008.

## Implementation Strategy

MVP = US1 (tablero). Luego alarmas y marcas, y por último aviso de pagos y rutina 043.

## Registro de implementación — 28/10/2026

- Esquema creado con respaldo verificado (`WC_esquema-detector-044_20261028_220617`).
- Ajustes surgidos con datos reales: las facturas que llegan con menos de 10 días de diferencia se agrupan como un envío (Sancor, Allianz, Coop. Eléctrica); "pago sin factura" solo cuando no hay ningún comprobante de deuda del contacto (compras, boletas de impuestos, sueldos) en ±60 días; faltantes históricos de los últimos 24 meses, descartables con motivo.
- US4: el aviso se muestra en el formulario de pagos de caja (los pagos bancarios entran por importación); el endpoint `/pago-sin-factura` queda para otros formularios.
- `DELETE /marcas/{id}` pasó a `POST /marcas/{id}/anular` (el cliente HTTP no envía cuerpo en DELETE); contrato actualizado.
