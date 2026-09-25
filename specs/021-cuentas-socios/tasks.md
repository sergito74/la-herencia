---

description: "Task list for 021-cuentas-socios"
---

# Tasks: Cuentas corrientes de socios/directores y condominio

**Input**: Design documents from `/specs/021-cuentas-socios/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, contracts/schema-script.md, quickstart.md

**Tests**: incluidos (Constitución, Principio V; mismo criterio que 004/019/020 — tests unitarios con monkeypatch, validación manual contra `WC` real para el flujo completo).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: US1 (marcar gasto como de un socio), US2 (consultar cuenta corriente del socio), US3 (registrar devolución)

## Phase 1: Setup

**Purpose**: esquema y estructura de módulo compartidos por todas las historias.

- [X] T001 Creado `backend/scripts/crear_tablas_cuentas_socios.py` (DDL idempotente, `Socios`/`MovimientosCuentaSocio`/`AuditoriaReflejoSocio` + insert idempotente de los 4 socios)
- [X] T002 Índice único filtrado `UX_MovimientosCuentaSocio_Origen` e índice simple `IX_MovimientosCuentaSocio_Socio` incluidos en el mismo script
- [X] T003 Ejecutado contra `WC` (backup previo: `backups/WC_pre_cuentas_socios_20260926.bak`) — verificado con `INFORMATION_SCHEMA`/`sys.indexes`: 3 tablas, columnas, índice único filtrado y 4 socios (Sergio, Lucy, Cond LSC, Ceci) creados correctamente
- [X] T004 [P] Estructura del módulo `backend/src/features/cuentas_socios/` creada (`__init__.py`, `repository.py`, `router.py`, `schemas.py`)
- [X] T005 [P] `cuentas_socios.router` registrado en `backend/src/main.py`

**Checkpoint**: esquema listo, módulo montado — puede arrancar cualquier historia.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: la función compartida de "importe bruto de compra particular" (research.md §3), necesaria para US1, extraída sin duplicar la lógica ya corregida en tarjetas.

- [X] T006 Extraída a `backend/src/features/compras/particular.py`: `APLICA_PARTICULAR_JOIN` (fragmento SQL, no función per-row — se decidió así para no introducir un N+1 en los listados masivos de `tarjetas_resumenes`; ver nota en el propio archivo) + `importe_bruto_compra_particular(id_compra)` para lookups puntuales (usado por `cuentas_socios`)
- [X] T007 `tarjetas_resumenes/repository.py` actualizado: `_APLICA_PARTICULAR = APLICA_PARTICULAR_JOIN` (importado), ya no mantiene su propia copia del SQL. Verificado: mismos resultados (`buscar_documentos('cumo')` idéntico a antes) y toda la suite de tarjetas en verde
- [X] T008 [P] `backend/tests/test_compras_particular.py` — 4 tests, reconoce ambas formas (Precio Unitario / Cantidad negativa) contra datos reales de `WC` (2JM control negativo, Cumo Store + otros 2 casos reales, Agüero Shamaim control negativo)

**Checkpoint**: función compartida lista y verificada — US1 puede implementarse sin re-derivar la fórmula.

---

## Phase 3: User Story 1 - Marcar un gasto como perteneciente a un socio (Priority: P1) 🎯 MVP

**Goal**: permitir elegir una compra "particular" candidata y asignarla a un socio, generando automáticamente el movimiento de deuda en su cuenta corriente, con reversión en un solo paso y auditoría completa.

**Independent Test**: tomar la compra real de Cumo Store ($29.699,10), asignarla a un socio vía la API, y verificar que aparece un movimiento `AsignacionGasto` en su cuenta por ese importe, con su fila correspondiente en `AuditoriaReflejoSocio`.

### Tests for User Story 1

- [X] T009 [P] [US1] `test_listar_compras_particulares_candidatas_filtra_asignadas` en `test_cuentas_socios_repository.py`
- [X] T010 [P] [US1] `test_asignar_gasto_inserta_movimiento_y_auditoria_en_una_transaccion` — **corregido durante la implementación**: la primera versión usaba `execute_insert_returning_id` + `execute_write_transaction` en dos llamadas separadas (dos transacciones), lo que rompía la garantía de "100% trazable" si la segunda fallaba tras la primera. Reescrito para usar un único `execute_write_transaction` con statement dependiente (mismo patrón callable `lambda resultados: (...)` que usan otras features)
- [X] T011 [P] [US1] `test_asignar_gasto_rechaza_si_ya_tiene_asignacion_vigente`
- [X] T012 [P] [US1] `test_anular_movimiento_marca_anulada_sin_tocar_importe`
- [X] T013 [P] [US1] `test_permite_reasignar_tras_anular`
- [X] T014 [P] [US1] 8 tests de endpoints en `test_cuentas_socios_endpoints.py` (todos mockeados sobre `repository`)

### Implementation for User Story 1

- [X] T015 [US1] `listar_compras_particulares_candidatas` implementada
- [X] T016 [US1] `asignar_gasto` implementada (con la corrección de transacción única de T010)
- [X] T017 [US1] `anular_movimiento` implementada, válida para `AsignacionGasto` y `Devolucion`
- [X] T018 [US1] Schemas Pydantic en `schemas.py`
- [X] T019 [US1] Endpoints implementados y registrados en `src/main.py`
- [ ] T020 [US1] Acción de frontend "Asignar a un socio…" — **pendiente**, backend validado end-to-end contra datos reales (ver resultados abajo)

**Validado contra datos reales de `WC` (2026-09-26)**, tras backup verificado (`backups/WC_pre_cuentas_socios_20260926.bak`):

- `listar_compras_particulares_candidatas('Cumo')` devolvió la compra real ($29.699,10).
- **Asignación real ejecutada**: Cumo Store → Sergio (motivo: validación MVP), generó `IdMovimiento=1` + `IdAuditoria=1` (`Accion='Asignacion'`) en una sola transacción. Saldo de Sergio pasó a $29.699,10; los otros 3 socios en $0 (FR-010).
- La compra ya no aparece en `listar_compras_particulares_candidatas` (correctamente filtrada tras la asignación).
- Reintentar la asignación (a otro socio) fue rechazado correctamente (FR-009).
- FR-011 (huérfano) verificado con un movimiento apuntando a una compra inexistente → `huerfano: true`; anulado después para no dejar datos de prueba permanentes.
- Suite completa del backend: 521 tests en verde (502 previos + 19 nuevos), sin regresiones en `tarjetas_resumenes` tras T006/T007.

**Checkpoint**: el flujo completo de asignar y revertir funciona de punta a punta para un socio, a nivel backend. Falta la acción de frontend (T020) para que no dependa de llamar a la API a mano.

---

## Phase 4: User Story 2 - Consultar la cuenta corriente de un socio (Priority: P1)

**Goal**: ver el saldo y el detalle de movimientos de cada socio, y el listado de los 4 con su saldo.

**Independent Test**: con la asignación de US1 ya hecha, consultar `GET /api/cuentas-socios` y `GET /api/cuentas-socios/{idSocio}/movimientos` y verificar que el saldo y el detalle son correctos, incluidos los movimientos anulados (visibles, no ocultos).

### Tests for User Story 2

- [ ] T021 [P] [US2] Test en `test_cuentas_socios_repository.py`: `calcular_saldo(id_socio)` = `SUM(CASE WHEN Tipo='AsignacionGasto' THEN Importe ELSE -Importe END) WHERE Anulada=0` (data-model.md, Entidades derivadas)
- [ ] T022 [P] [US2] Test: `listar_socios_con_saldo()` devuelve los 4 socios del catálogo, incluido uno sin ningún movimiento con saldo `0.0` (FR-010) — nunca ausente del listado
- [ ] T023 [P] [US2] Test: `listar_movimientos(id_socio)` devuelve los movimientos ordenados por fecha, incluidos los `Anulada=1` (con su motivo de anulación visible) — nunca los oculta
- [ ] T024 [P] [US2] Test de endpoints: `GET /api/cuentas-socios` y `GET /api/cuentas-socios/{idSocio}/movimientos` (mockeado sobre `repository`)

### Implementation for User Story 2

- [ ] T025 [US2] Implementar `calcular_saldo(id_socio)` y `listar_socios_con_saldo()` en `repository.py`
- [ ] T026 [US2] Implementar `listar_movimientos(id_socio)` en `repository.py`, incluyendo para cada `AsignacionGasto` el proveedor/número de documento de la compra de origen (join a `Compras`/`Contactos` vía `IdOrigen`)
- [ ] T026a [P] [US2] Test: `listar_movimientos` marca `huerfano: true` en un movimiento cuyo `IdOrigen` ya no existe en `Compras` (LEFT JOIN, no INNER — nunca debe desaparecer del historial, FR-011)
- [ ] T026b [US2] Agregar el campo `huerfano: bool` a `listar_movimientos` y al schema `MovimientoCuentaSocio` (`contracts/api.md`); en el frontend (`CuentaSocio.tsx`, T030), mostrar un aviso visible (no bloqueante) en la fila correspondiente
- [ ] T027 [US2] Definir schema `SocioConSaldo`/`DetalleSocioResponse` en `schemas.py` (según `contracts/api.md`)
- [ ] T028 [US2] Implementar `GET /api/cuentas-socios` y `GET /api/cuentas-socios/{idSocio}/movimientos` en `router.py`
- [ ] T029 [US2] Crear `frontend/src/services/cuentasSociosApi.ts` con los tipos y funciones `fetchSocios`, `fetchMovimientosSocio`
- [ ] T030 [US2] Crear `frontend/src/components/cuentas-socios/SociosListado.tsx` (los 4 socios + saldo, análogo a `SaldosListado.tsx` de 004) y `CuentaSocio.tsx` (detalle: saldo + movimientos, cada `AsignacionGasto` navegable hacia su compra de origen)
- [ ] T031 [US2] Crear páginas `frontend/src/app/finanzas/cuentas-socios/page.tsx` (listado) y `frontend/src/app/finanzas/cuentas-socios/[idSocio]/page.tsx` (detalle), con su link de entrada desde el área de Finanzas

**Checkpoint**: US1 y US2 funcionan juntas — se puede asignar un gasto y verlo reflejado en la cuenta del socio correspondiente.

---

## Phase 5: User Story 3 - Registrar una devolución/compensación de un socio (Priority: P2)

**Goal**: permitir registrar manualmente que un socio devolvió/compensó dinero a la empresa, reduciendo su saldo.

**Independent Test**: sobre un socio con saldo deudor (de US1), registrar una devolución parcial y verificar que el saldo se reduce en el monto exacto.

### Tests for User Story 3

- [ ] T032 [P] [US3] Test en `test_cuentas_socios_repository.py`: `registrar_devolucion(id_socio, importe, fecha, medio, motivo, usuario)` inserta un `MovimientosCuentaSocio` (`Tipo='Devolucion'`, `Importe > 0` — CHECK de `data-model.md`) y una fila en `AuditoriaReflejoSocio` (`Accion='Devolucion'`) en la misma transacción
- [ ] T033 [P] [US3] Test: una devolución mayor al saldo deudor actual se acepta igual, dejando al socio con saldo negativo (a favor del socio) — Edge Case de la spec, no se rechaza
- [ ] T034 [P] [US3] Test: anular una devolución (reutilizando `anular_movimiento` de US1) genera `Accion='ReversionDevolucion'` en la auditoría, y el saldo del socio vuelve a subir
- [ ] T035 [P] [US3] Test de endpoint: `POST /api/cuentas-socios/{idSocio}/devolucion` (mockeado)

### Implementation for User Story 3

- [ ] T036 [US3] Implementar `registrar_devolucion(id_socio, importe, fecha, medio, motivo, usuario)` en `repository.py`
- [ ] T037 [US3] Definir schema `DevolucionRequest` en `schemas.py`
- [ ] T038 [US3] Implementar `POST /api/cuentas-socios/{idSocio}/devolucion` en `router.py`
- [ ] T039 [US3] Agregar a `CuentaSocio.tsx` (frontend) el formulario de "Registrar devolución" (monto, fecha, medio, motivo) y el botón de anular sobre cualquier movimiento (reutilizando el endpoint de anulación de US1)

**Checkpoint**: las 3 historias funcionan de forma independiente y en conjunto — asignar, consultar, y compensar.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T040 [P] Ejecutar los 6 escenarios de `quickstart.md` contra datos reales de `WC` (con backup verificado) y documentar resultado, incluido el caso real de Cumo Store
- [ ] T041 Ejecutar `pytest backend/tests/test_cuentas_socios_*.py backend/tests/test_compras_particular.py backend/tests/test_conciliacion_documentos.py backend/tests/test_cuentas_corrientes_saldos.py` y confirmar 100% en verde (los dos últimos, para confirmar que extraer la función compartida de T006/T007 no rompió nada de tarjetas)
- [ ] T042 [P] Revisar formato de números y convenciones de UX (memoria `feedback_formato_numeros`) en las pantallas de listado y detalle de socios — `formatMoneda`, nunca `type=number`/`toLocaleString`
- [ ] T043 `tsc --noEmit` y `eslint` sobre los archivos nuevos del frontend

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA US1 (no hay forma de calcular el importe a asignar sin T006).
- **User Stories (Phase 3-5)**: todas dependen de Foundational. US2 depende de que existan movimientos reales para mostrar (de US1) para ser demostrable en la práctica, aunque sus endpoints en sí son independientes (pueden probarse con datos mockeados). US3 reutiliza `anular_movimiento` de US1 — implementar US1 antes.
- **Polish (Phase 6)**: depende de que las historias que se vayan a entregar estén completas.

### Parallel Opportunities

- T004/T005 (Setup) en paralelo con T001-T003 una vez decidido el esquema.
- Todos los tests marcados [P] de una misma historia en paralelo entre sí, antes de su implementación.
- T008 (test de la función compartida) puede escribirse en paralelo con T007 (verificación de que tarjetas sigue igual).

---

## Implementation Strategy

### MVP First (User Story 1)

1. Setup + Foundational.
2. US1 — demostrable: asignar la compra real de Cumo Store a un socio vía API y ver el movimiento generado.
3. **Parar y validar** con el usuario el resultado contra el caso real antes de construir la UI completa (US2/US3).

### Incremental Delivery

1. Setup + Foundational → esquema y función compartida listos.
2. US1 → asignación de gastos funcionando (backend + acción mínima de frontend).
3. US2 → pantallas de consulta (listado + detalle por socio).
4. US3 → devoluciones/compensaciones.
5. Polish → validación contra `quickstart.md` con datos reales, confirmar que tarjetas (008/009) sigue sin regresiones.
