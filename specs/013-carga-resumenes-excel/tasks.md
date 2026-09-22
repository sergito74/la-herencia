---

description: "Task list for Confirmar la carga de resúmenes bancarios (BNA/Galicia) desde Excel"
---

# Tasks: Confirmar la carga de resúmenes bancarios (BNA/Galicia) desde Excel

**Input**: Design documents from `/specs/013-carga-resumenes-excel/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/carga-resumenes-api.md, quickstart.md

**Tests**: se incluyen tests focalizados (constitución, Principio V) para la lógica de mayor riesgo de error silencioso: deduplicación (US2) y la transacción atómica de persistencia (US1/US2), siguiendo el estándar del proyecto (mock de `connection.py`, sin tocar `WC` en tests automatizados).

**Organization**: agrupadas por historia de usuario de `spec.md`, en orden de dependencia real: US1 (confirmar) y US2 (no duplicar) son inseparables en la práctica — no tiene sentido persistir sin deduplicar primero — así que se implementan juntas en la Fase 3, seguidas por US3 (ver el resumen antes de confirmar, que solo expone lo que US1/US2 ya calculan) y US4 (trazabilidad, extensión aditiva).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: A qué historia de usuario pertenece (US1-US4, spec.md)

## Path Conventions

Web app existente: `backend/src/`, `frontend/src/` — mismo layout que 003-tesoreria (ver `plan.md` → Project Structure).

---

## Phase 1: Setup

**Purpose**: Tablas nuevas de infraestructura, sin lógica todavía

- [X] T001 Implementar `backend/scripts/crear_tablas_carga_resumenes.py`: script idempotente (`IF OBJECT_ID(...) IS NULL CREATE TABLE ...`, mismo patrón que `backend/scripts/crear_tabla_estado_lineas.py` de 009) que crea `dbo.CargasResumenBancario` (`IdCarga` int identity PK, `Banco` varchar(20) NOT NULL, `NombreArchivo` nvarchar(260) NOT NULL, `FechaHoraCarga` datetime2 NOT NULL default `SYSUTCDATETIME()`, `CantidadInsertados` int NOT NULL, `CantidadOmitidosDuplicado` int NOT NULL, `CantidadOmitidosIncompletos` int NOT NULL) y `dbo.CargasResumenBancario_Movimientos` (`IdCarga` int NOT NULL FK → `CargasResumenBancario.IdCarga`, `Banco` varchar(20) NOT NULL, `IdMovimiento` int NOT NULL, PK compuesta `(Banco, IdMovimiento)`) contra `WC` (data-model.md)
- [X] T002 Ejecutar `crear_tablas_carga_resumenes.py` contra `WC` y verificar con `INFORMATION_SCHEMA.TABLES` que ambas tablas existen con las columnas esperadas

**Checkpoint**: tablas de infraestructura listas en `WC`, sin funcionalidad todavía.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Lógica de deduplicación reutilizada por US1/US2/US3 — nada puede persistir hasta que esto exista

**⚠️ CRITICAL**: Ninguna historia puede completarse hasta que esta fase esté completa

- [X] T003 Implementar `backend/src/features/tesoreria/confirmacion_carga.py::_normalizar_concepto(texto) -> str` (mayúsculas, `strip`, espacios colapsados a uno) y `_clave_movimiento(banco, fila) -> tuple`: fecha + importe (BNA) o débito/crédito (Galicia) + concepto/descripción normalizado + comprobante si existe (research.md §2)
- [X] T004 Implementar `confirmacion_carga.py::detectar_duplicados(banco, movimientos_preview) -> dict[int, bool]`: consulta `Movimientos BNA`/`Movimientos Galicia` acotada al rango `[MIN(fecha), MAX(fecha)]` de los movimientos del preview, calcula `_clave_movimiento` de cada fila existente y de cada fila del preview, y devuelve qué índices del preview son duplicados (depende de T003)
- [X] T005 [P] Test `backend/tests/test_tesoreria_confirmacion_carga.py`: `_normalizar_concepto` colapsa espacios/mayúsculas; `detectar_duplicados` marca coincidencia exacta (fecha+importe+concepto+comprobante) y no marca falsos positivos (mismo importe, concepto distinto; mismo concepto, fecha distinta) — mock de `fetch_all` (depende de T003, T004)

**Checkpoint**: la lógica de "qué es nuevo y qué es duplicado" está probada y lista para usarse desde persistencia (US1/US2) y desde previsualización (US3).

---

## Phase 3: User Story 1 + User Story 2 — Confirmar una carga sin duplicar (Priority: P1)

**Goal**: El usuario confirma un Excel ya validado y los movimientos nuevos quedan en `WC`; si el archivo (o parte de él) ya estaba cargado, esos movimientos se omiten sin duplicarse (spec.md Historias 1 y 2).

**Independent Test**: Confirmar un Excel real y verificar que sus movimientos aparecen en el listado de tesorería (003 US1) con los mismos valores de la vista previa; volver a confirmar el mismo archivo y verificar que no se inserta nada nuevo (SC-001, SC-002).

### Implementation for User Story 1 + 2

- [X] T006 [US1] Implementar `confirmacion_carga.py::confirmar_carga(banco, filename, contenido) -> dict`: reprocesa el archivo con `excel_import.validar_y_previsualizar` (FR-002, nunca reusa un preview cacheado), rechaza si `valido=False` (FR-010), corre `detectar_duplicados` (T004), y arma las filas a insertar (depende de T004)
- [X] T007 [US1] Extender `backend/src/features/tesoreria/repository.py` con `insertar_movimientos_bna(filas) -> list[int]` e `insertar_movimientos_galicia(filas) -> list[int]`: `INSERT` con `IdContacto`/`Contacto` `NULL` (FR-006, Clarifications Q1), devolviendo los `IdMovimientoBNA`/`IdMovimiento` generados
- [X] T008 [US2] Extender `repository.py` con `registrar_carga(banco, filename, insertados, omitidos_duplicado, omitidos_incompletos, ids_movimiento) -> int`: `INSERT` en `CargasResumenBancario` + `CargasResumenBancario_Movimientos` (uno por `IdMovimiento` insertado) dentro de la misma transacción que T007, usando `execute_write_transaction` con el rango de fechas del archivo bloqueado (`WITH (UPDLOCK, SERIALIZABLE)`, FR-005, research.md §4) — depende de T007
- [X] T009 [US1] Completar `confirmacion_carga.py::confirmar_carga` para que, tras T006, llame a T007+T008 dentro de una única transacción y devuelva `{banco, idCarga, insertados, omitidosDuplicado, omitidosIncompletos, total}` (depende de T006, T007, T008)
- [X] T010 [US1] Agregar endpoint `POST /api/tesoreria/excel/confirmar` en `backend/src/features/tesoreria/router.py` (multipart, mismo patrón que `/excel/validar`), devolviendo 422 con los mismos `errores` si `confirmar_carga` rechaza el archivo (depende de T009)
- [X] T011 [P] [US1] Test `backend/tests/test_tesoreria_cargas_endpoints.py`: `POST /excel/confirmar` con archivo válido inserta y devuelve conteos correctos; archivo inválido devuelve 422 sin llamar a ninguna función de escritura (mock); confirmar el mismo archivo dos veces (mock de `detectar_duplicados` devolviendo todo duplicado en la segunda llamada) inserta 0 la segunda vez (depende de T010)
- [X] T012 [US1] Extender `frontend/src/services/tesoreriaApi.ts` con `confirmarCargaExcel(banco, archivo)` tipado según `contracts/carga-resumenes-api.md`
- [X] T013 [US1] Extender `frontend/src/components/tesoreria/CargaExcel.tsx`: tras la vista previa existente (003), agregar botón "Confirmar carga" que llama a T012, muestra el resultado (insertados/omitidos) y refresca el listado de movimientos del banco (depende de T012)

**Checkpoint**: US1 + US2 funcionan de punta a punta — confirmar inserta, repetir no duplica.

---

## Phase 4: User Story 3 — Ver nuevos vs. omitidos antes de confirmar (Priority: P1)

**Goal**: Antes de escribir nada, el usuario ve cuántos movimientos son nuevos y cuántos se van a omitir (spec.md Historia 3).

**Independent Test**: Subir un archivo con superposición parcial conocida y verificar que el conteo mostrado antes de confirmar coincide exactamente con el resultado real después de confirmar (FR-004).

### Implementation for User Story 3

- [X] T014 [US3] Implementar `confirmacion_carga.py::previsualizar_confirmacion(filename, contenido) -> dict`: reusa `excel_import.validar_y_previsualizar` + `detectar_duplicados` (T004, sin persistir nada) y devuelve cada movimiento con `estado: "nuevo" | "omitidoDuplicado"` más el resumen de conteos (depende de T004)
- [X] T015 [US3] Agregar endpoint `POST /api/tesoreria/excel/previsualizar-confirmacion` en `router.py` según `contracts/carga-resumenes-api.md` (depende de T014)
- [X] T016 [P] [US3] Test en `backend/tests/test_tesoreria_cargas_endpoints.py`: `previsualizar_confirmacion` no llama a ninguna función de escritura (mock) y el conteo `nuevos`/`omitidosDuplicado` coincide con lo que luego confirma `confirmar_carga` sobre el mismo archivo (depende de T014)
- [X] T017 [US3] Extender `tesoreriaApi.ts` con `previsualizarConfirmacion(banco, archivo)` (depende de T012)
- [X] T018 [US3] Extender `CargaExcel.tsx` para mostrar el conteo "N nuevos / M ya existentes" (T017) antes de habilitar el botón "Confirmar carga" (T013) — depende de T013, T017

**Checkpoint**: el usuario nunca confirma a ciegas — el conteo previo y el resultado final siempre coinciden.

---

## Phase 5: User Story 4 — Trazabilidad de la carga (Priority: P2)

**Goal**: Cada movimiento importado por esta vía es identificable hasta el archivo/carga que lo originó (spec.md Historia 4).

**Independent Test**: Confirmar una carga, consultar su historial y verificar que un movimiento de esa carga expone `idCarga`; un movimiento histórico (no importado por Excel) expone `idCarga: null` (SC-004).

### Implementation for User Story 4

- [X] T019 [US4] Extender `repository.py::listar_movimientos` (BNA/Galicia, usado por `GET /{medio}/movimientos` de 003) con un `LEFT JOIN` contra `CargasResumenBancario_Movimientos` para exponer `idCarga: number | null` en cada fila (depende de T008)
- [X] T020 [US4] Agregar `repository.py::listar_cargas(banco) -> list[dict]`: `SELECT` de `CargasResumenBancario` filtrado por banco, ordenado por `FechaHoraCarga DESC`
- [X] T021 [US4] Agregar endpoint `GET /api/tesoreria/{medio}/cargas` en `router.py` según `contracts/carga-resumenes-api.md` (depende de T020)
- [X] T022 [P] [US4] Test en `backend/tests/test_tesoreria_cargas_endpoints.py`: `GET /{medio}/cargas` devuelve las cargas ordenadas; un movimiento con carga asociada trae `idCarga` correcto, uno sin carga trae `null` (depende de T019, T021)
- [X] T023 [US4] Extender `tesoreriaApi.ts` con `fetchCargas(banco)`, y mostrar `idCarga`/origen en el listado de movimientos de tesorería donde ya se muestra la referencia de origen (003 US2) cuando corresponda (depende de T019)

**Checkpoint**: todas las historias completas — cualquier movimiento importado es auditable hasta su archivo de origen.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificación final, después de que las 4 historias funcionan de punta a punta

- [X] T024 Aplicar formato numérico y monetario del sistema (miles `.`, decimales `,`, `$`) en los conteos/importes mostrados por `CargaExcel.tsx`, usando los helpers ya existentes (nunca `type=number` ni `toLocaleString`, regla de memoria del proyecto)
- [ ] T025 Ejecutar los 6 escenarios de `quickstart.md` de punta a punta sobre el sistema integrado (contra `WC` real) y confirmar los 4 criterios de éxito de `spec.md` (SC-001 a SC-005, incluyendo SC-005 de concurrencia si es practicable)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — arranca de inmediato
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA todas las historias (la deduplicación es prerequisito de persistir y de previsualizar)
- **US1+US2 (Phase 3)**: depende de Foundational; es la base de escritura (`confirmacion_carga.py::confirmar_carga`) que reutiliza US3
- **US3 (Phase 4)**: depende de Foundational (T004) y comparte servicio con US1/US2 (T014 llama a la misma `detectar_duplicados`), pero no depende de que US1/US2 estén ya expuestas por endpoint — puede implementarse en paralelo a partir de T004
- **US4 (Phase 5)**: depende de que existan cargas persistidas (T008 de US1/US2) para tener datos que rastrear
- **Polish (Phase 6)**: depende de que las 4 historias estén completas

### Parallel Opportunities

- T001 y T002 son secuenciales (crear tabla, luego verificar) — no paralelas
- T005 en paralelo con el resto una vez completo T003/T004
- T011, T016, T022 (tests) en paralelo entre sí una vez completos sus endpoints respectivos
- US3 (T014 en adelante) puede desarrollarse en paralelo a US1/US2 (T006 en adelante) una vez cerrada la Fase 2, ya que ambas parten de `detectar_duplicados` sin depender una de la otra

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Completar Phase 1 (Setup) y Phase 2 (Foundational)
2. Completar Phase 3 (US1+US2) — confirmar sin duplicar
3. **Parar y validar**: Escenarios 1 y 2 de `quickstart.md`
4. Demostrar si está listo

### Entrega incremental

1. Setup + Foundational → deduplicación lista y probada
2. US1+US2 → confirmar carga sin duplicar (MVP)
3. US3 → ver el conteo antes de confirmar
4. US4 → trazabilidad completa
5. Polish → formato numérico, validación final end-to-end
