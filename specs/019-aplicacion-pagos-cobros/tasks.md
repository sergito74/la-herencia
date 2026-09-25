---

description: "Task list for 019-aplicacion-pagos-cobros"
---

# Tasks: Aplicación de pagos y cobros (cuenta corriente)

**Input**: Design documents from `/specs/019-aplicacion-pagos-cobros/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-aplicaciones-pago.md, quickstart.md

**Tests**: incluidos — mismo criterio que 018 (plan: pytest; constitución Principio V).

**Organization**: por historia de usuario (spec.md), prioridad P1→P2.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Web app existente: `backend/src/`, `frontend/src/`.

---

## Phase 1: Setup

- [X] T001 Crear esqueleto backend: `backend/src/features/aplicaciones_pago/__init__.py`, `documentos.py`, `sugerencia.py`, `repository.py`, `router.py`, `schemas.py` (vacíos con docstring de propósito)
- [X] T002 [P] Crear esqueleto frontend: `frontend/src/components/aplicaciones-pago/AplicarPagoPanel.tsx`, `frontend/src/services/aplicacionesPagoApi.ts` (vacíos que compilan)

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: ninguna historia puede implementarse hasta que esta fase esté completa.

- [X] T003 Escribir `backend/scripts/crear_tabla_aplicaciones_pago.py` (idempotente, `_assert_target_is_wc`, patrón de `crear_tablas_imputacion.py`/`separar_cuentas_bna.py`) con el DDL de `AplicacionesPago` de data-model.md (columnas, CHECK de `TipoDocumento`/`OrigenMovimiento`/`ImporteAplicado > 0`, índices `(OrigenMovimiento, IdMovimientoOrigen)` y `(TipoDocumento, IdDocumentoAplicado)`)
- [X] T004 Ejecutar el script contra `WC` (crear la tabla real) y verificar con una lectura que existe vacía — **pedir confirmación explícita de Sergio antes de correrlo**, mismo hábito que en 018 (`separar_cuentas_bna.py`), aunque el riesgo de crear una tabla nueva sea bajo (hallazgo P1 de `/speckit-analyze`)
- [X] T005 Definir `TOLERANCIA_REDONDEO_APLICACION = 1.0` como constante nombrada en `backend/src/features/aplicaciones_pago/repository.py` (research.md §4)
- [X] T006 Implementar `documentos_pendientes(id_contacto, tipo)` en `backend/src/features/aplicaciones_pago/documentos.py`: para `tipo='compra'`, `importeTotal` desde `vw_Cns_Total_Compra.GranTotal`; para `tipo='venta'`, reusa `ventas_hacienda.repository.{get_venta_cabecera,get_lineas_venta,calcular_totales}` para Hacienda y `[Importe Neto a percibir]` para Granos (research.md §1/§2) — en ambos casos resta `SUM(ImporteAplicado) WHERE Anulada=0` de `AplicacionesPago` para el `saldoPendiente`, y excluye documentos con `saldoPendiente <= TOLERANCIA_REDONDEO_APLICACION`
- [X] T007 Implementar en `backend/src/features/aplicaciones_pago/repository.py`: `estado_documento(tipo_documento, id_documento)`, `estado_movimiento(origen_movimiento, id_movimiento_origen)`, `insertar_aplicaciones(origen_movimiento, id_movimiento_origen, aplicaciones: list, usuario)` (valida no sobre-aplicación de cada documento y del movimiento antes de insertar, FR-008), `anular_aplicacion(id_aplicacion, motivo, usuario)` (nunca edita `ImporteAplicado`, solo marca `Anulada`)
- [X] T008 [P] Definir schemas Pydantic (`DocumentoPendiente`, `SugerenciaAplicacion`, `AplicacionConfirmada`, `EstadoDocumento`, `EstadoMovimiento`) en `backend/src/features/aplicaciones_pago/schemas.py` según `contracts/api-aplicaciones-pago.md`

**Checkpoint**: tabla creada, cálculo de documentos pendientes y estado listos — las historias pueden empezar.

---

## Phase 3: User Story 1 - Aplicar un pago a facturas de compra pendientes (Priority: P1) 🎯 MVP

**Goal**: aplicar un pago real contra una o más compras pendientes del mismo proveedor, con sugerencia FIFO editable.

**Independent Test**: quickstart.md Escenario 1 — sugerencia FIFO, edición, confirmación, estado resultante correcto.

### Tests for User Story 1

- [X] T009 [P] [US1] Test de sugerencia FIFO en `backend/tests/test_aplicaciones_pago_sugerencia.py`: dado un contacto con 2 compras pendientes (una más vieja que otra) y un importe que solo alcanza para cubrir la primera entera y parte de la segunda, la sugerencia asigna en ese orden y dedo dejar `saldoSinAsignar = 0`
- [X] T010 [P] [US1] Contract test en `backend/tests/test_aplicaciones_pago_endpoints.py`: `POST /api/aplicaciones-pago` con una aplicación editada (distinta a la sugerencia) se guarda tal cual quedó; `GET /api/aplicaciones-pago/documento/CompraDeuda/{id}` refleja el estado `Parcial`/`Total` correcto
- [X] T010b [P] [US1] Contract test en `backend/tests/test_aplicaciones_pago_endpoints.py`: `POST /api/aplicaciones-pago` con un `importeAplicado` que deja un documento o el movimiento sobre-aplicado (más allá de `TOLERANCIA_REDONDEO_APLICACION`) devuelve 400 y no inserta ninguna fila (FR-008/SC-002 — hallazgo C1 de `/speckit-analyze`)
- [X] T010c [P] [US1] Contract test en `backend/tests/test_aplicaciones_pago_endpoints.py`: `POST /api/aplicaciones-pago` aceptando un `idDocumento` de un contacto DISTINTO al del movimiento no rechaza la operación (FR-006 — hallazgo C2 de `/speckit-analyze`)

### Implementation for User Story 1

- [X] T011 [US1] Implementar `sugerir(origen_movimiento, id_movimiento_origen)` en `backend/src/features/aplicaciones_pago/sugerencia.py`: obtiene contacto/importe/signo del movimiento (mismo patrón de anclaje que `tesoreria/matching._ANCHOR_BY_MEDIO`, reusar si aplica), busca documentos pendientes del tipo correspondiente (compra si es egreso) vía `documentos.documentos_pendientes`, y arma la sugerencia FIFO (research.md §3)
- [X] T012 [US1] Implementar `POST /api/aplicaciones-pago/sugerir` en `backend/src/features/aplicaciones_pago/router.py`
- [X] T013 [US1] Implementar `GET /api/aplicaciones-pago/documentos-pendientes`
- [X] T014 [US1] Implementar `POST /api/aplicaciones-pago` (confirmar aplicación) — usa `repository.insertar_aplicaciones`, 400 si sobre-aplica (FR-008)
- [X] T015 [US1] Implementar `GET /api/aplicaciones-pago/documento/{tipoDocumento}/{idDocumento}`
- [X] T016 [US1] Registrar `aplicaciones_pago_router` en `backend/src/main.py`
- [X] T017 [US1] Implementar `fetchSugerencia`/`fetchDocumentosPendientes`/`confirmarAplicacion` en `frontend/src/services/aplicacionesPagoApi.ts` y el panel `AplicarPagoPanel.tsx` (sugerencia editable en grilla, botón confirmar)
- [X] T017b [US1] En `AplicarPagoPanel.tsx`, agregar un buscador de "aplicar a otro contacto" (adicional a la sugerencia automática, que solo busca documentos del mismo contacto que el movimiento) — permite elegir un contacto distinto y ver sus documentos pendientes, mostrando aviso visible de que difiere del contacto del movimiento (FR-006 — hallazgo C2 de `/speckit-analyze`)

**Checkpoint**: User Story 1 funcional de forma independiente.

---

## Phase 4: User Story 2 - Aplicar un cobro a documentos de venta pendientes (Priority: P1)

**Goal**: mismo mecanismo que US1, pero para cobros contra Venta Hacienda/Venta Granos (hoy sin ningún equivalente en el sistema).

**Independent Test**: quickstart.md Escenario 3.

### Tests for User Story 2

- [X] T018 [P] [US2] Test en `backend/tests/test_aplicaciones_pago_sugerencia.py`: `documentos_pendientes(id_contacto, 'venta')` devuelve tanto ventas de Hacienda (con `importeTotal` = `calcular_totales(...)["importeTotal"]`) como de Granos (`[Importe Neto a percibir]`), ordenadas por fecha

### Implementation for User Story 2

- [X] T019 [US2] Completar en `documentos.py` la rama `tipo='venta'` de T006 si quedó pendiente (Hacienda + Granos combinadas, ordenadas por fecha para FIFO)
- [X] T020 [US2] Confirmar que `sugerencia.sugerir` (T011) funciona igual para movimientos de ingreso (importe positivo) buscando documentos de venta, sin código duplicado respecto a compras
- [X] T021 [US2] Adaptar `AplicarPagoPanel.tsx` para mostrar el tipo de documento correcto (compra o venta) según si el movimiento es egreso o ingreso

**Checkpoint**: User Stories 1 y 2 funcionan — aplicación de pagos y cobros completa.

---

## Phase 5: User Story 3 - Ver el estado de aplicación de un documento (Priority: P2)

**Goal**: consultar y auditar el estado de cualquier documento o movimiento, incluida la anulación no destructiva.

**Independent Test**: quickstart.md Escenario 2.

### Tests for User Story 3

- [X] T022 [P] [US3] Test en `backend/tests/test_aplicaciones_pago_endpoints.py`: anular una aplicación vigente recalcula el estado del documento al valor anterior, y el historial sigue mostrando la fila anulada con su motivo (nunca desaparece)

### Implementation for User Story 3

- [X] T023 [US3] Implementar `POST /api/aplicaciones-pago/{idAplicacion}/anular` — usa `repository.anular_aplicacion`, sin restricción de rol (FR-011)
- [X] T024 [US3] Implementar `GET /api/aplicaciones-pago/movimiento/{origenMovimiento}/{idMovimientoOrigen}`
- [X] T025 [US3] Mostrar historial de aplicaciones (vigentes y anuladas) en el panel/detalle del frontend

**Checkpoint**: estado y auditoría completos.

---

## Phase 6: User Story 4 - El flujo de caja por rubro usa la aplicación (Priority: P2)

**Goal**: una vez aplicado, el Rubro/Centro de Costos del flujo de caja (018 v2) sale de la aplicación real, no del matching exacto; y se distinguen explícitamente "aplicado" / "pendiente de aplicar" (posterior al corte) / "histórico sin aplicar" (anterior a 2015-09-01).

**Independent Test**: quickstart.md Escenarios 5 y 6.

### Tests for User Story 4

- [X] T026 [P] [US4] Test en `backend/tests/test_flujo_caja_atribucion.py` (o extender `test_flujo_caja_clasificacion.py`): un movimiento con aplicaciones vigentes usa el Rubro/Centro de Costos del documento aplicado (ponderado si hay más de una aplicación con rubros distintos), NO el matching exacto, aunque este último también daría resultado
- [X] T027 [P] [US4] Test: un movimiento sin aplicación anterior a 2025-09-01 → "Histórico sin aplicar"; uno sin aplicación posterior a esa fecha → "Pendiente de aplicar" (dos etiquetas distintas, nunca la misma)

### Implementation for User Story 4

- [X] T028 [US4] Extender `atribuir_egreso`/`atribuir_ingreso` en `backend/src/features/flujo_caja/atribucion.py`: antes del matching exacto actual, consultar `aplicaciones_pago.repository.estado_movimiento` — si hay aplicaciones vigentes, derivar Rubro/Centro de Costos de los documentos aplicados (ponderado por `ImporteAplicado`); si no las hay, aplicar la regla de fecha de corte (FR-010)
- [X] T029 [US4] Actualizar `agregar_por_rubro` en `backend/src/features/flujo_caja/repository.py` para reflejar las 3 categorías explícitas en vez de una única "Sin rubro asignado"
- [ ] T030 [US4] Actualizar `TablaFlujoCaja.tsx`/vista "por rubro" del frontend para distinguir visualmente las 3 categorías (aplicado / pendiente de aplicar / histórico sin aplicar) — **diferida**: el backend (`GET /api/flujo-caja/por-rubro`, ya en producción desde 018 v2) ya devuelve las 3 categorías correctamente (validado con datos reales), pero todavía no existe ninguna pantalla propia de "flujo de caja por rubro" en el frontend para mostrarlas — falta construir esa pantalla desde cero, no es un ajuste de una vista existente. Mientras tanto, se agregó un botón "Aplicar a factura/venta…" en el detalle de movimientos de `/finanzas/flujo-caja-real` (vista por cuenta) para que la aplicación de pagos ya sea usable end-to-end (T017).

**Checkpoint**: las 4 historias funcionan de forma independiente y en conjunto.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T031 [P] Ejecutar los 6 escenarios de `quickstart.md` contra datos reales de `WC` y documentar resultado
- [X] T032 Ejecutar `pytest backend/tests/test_aplicaciones_pago_*.py backend/tests/test_flujo_caja_*.py` y confirmar 100% en verde
- [X] T033 [P] Revisar formato de números y convenciones de UX (memoria `feedback_formato_numeros`) en el panel de aplicación

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA todas las historias (en particular, la tabla debe existir antes de cualquier lectura/escritura real).
- **User Stories (Phase 3-6)**: todas dependen de Foundational. US1 y US2 son P1 y comparten casi todo el código (`sugerencia.py`, `documentos.py`) — conviene hacerlas en ese orden, no en paralelo por distintas personas, para no duplicar la lógica de FIFO. US3 depende de que existan aplicaciones reales (de US1/US2) para tener algo que anular/consultar en la práctica, aunque los endpoints en sí son independientes. US4 depende de que la tabla `AplicacionesPago` tenga datos reales para ser útil, y toca directamente `flujo_caja/atribucion.py` (018) — coordinar si se sigue tocando 018 en paralelo por otro motivo.
- **Polish (Phase 7)**: depende de que las historias que se vayan a entregar estén completas.

### Parallel Opportunities

- T002 (Setup frontend) en paralelo con T001.
- T008 (schemas) en paralelo con T006/T007 una vez que T003/T004/T005 están listos.
- Los contract tests marcados [P] de cada historia en paralelo con su implementación.
- T026/T027 (US4) pueden escribirse en paralelo con T028-T030 de la misma historia, ya que son de solo lectura sobre datos que ya van a existir.

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Setup + Foundational.
2. US1 (compras) — ya es demostrable: aplicar un pago real y ver el estado de la factura.
3. US2 (ventas) — comparte casi todo el código con US1, bajo costo incremental, y es la pieza que hoy no existe en absoluto del lado de clientes.
4. **Parar y validar** con el dueño antes de seguir — recién ahí decidir si vale la pena encarar el backlog histórico 2015-2026 (fuera de alcance de esta feature, decisión aparte).

### Incremental Delivery

1. Setup + Foundational → tabla lista.
2. US1 + US2 → aplicación de pagos y cobros funcionando (MVP).
3. US3 → auditoría/consulta de estado.
4. US4 → el flujo de caja por rubro empieza a reflejar la realidad en vez de "Sin rubro asignado" genérico.
5. Polish → validación final contra quickstart.md.
