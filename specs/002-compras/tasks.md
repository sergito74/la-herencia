# Tasks: Compras como fuente de verdad de imputación (solo lectura)

**Input**: Design documents from `specs/002-compras/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/compras-api.md, quickstart.md

**Tests**: Incluidos — `plan.md`/`research.md` ya definieron pytest + httpx con fixtures como parte del contrato técnico (principio V de la constitución).

**Organization**: Tareas agrupadas por historia de usuario (spec.md) para permitir implementación y prueba independientes.

## Path Conventions

Aplicación web (backend + frontend), según `plan.md`: `backend/src/`, `backend/tests/`, `frontend/src/`.

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Crear estructura `backend/src/{db,features/compras}` y `backend/tests/contract` per `plan.md`
- [x] T002 Inicializar proyecto Python en `backend/` (`pyproject.toml` o `requirements.txt`) con `fastapi`, `pydantic`, `pyodbc`, `pytest`, `httpx`
- [x] T003 [P] Crear/verificar estructura `frontend/src/{app,components,services}` con Next.js, TypeScript, Tailwind CSS y TanStack Query per `plan.md`
- [x] T004 [P] Configurar linting/formato: `ruff`/`black` en `backend/`, `eslint`/`prettier` en `frontend/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: Ninguna historia de usuario puede comenzar hasta completar esta fase.

- [x] T005 Implementar conexión de solo lectura a SQL Server en `backend/src/db/connection.py` usando el DSN `SQL_LaHerencia` (pyodbc, `Trusted_Connection=Yes`, sin ejecutar `INSERT`/`UPDATE`/`DELETE`/`MERGE`/`TRUNCATE`/`ALTER`/`DROP`)
- [x] T006 Crear la app FastAPI en `backend/src/main.py` con montaje de routers por feature
- [x] T007 [P] Crear helper de paginación compartido (`page`, `pageSize` default 50 máx 200, `total`) en `backend/src/db/pagination.py` per `research.md`
- [x] T008 [P] Crear cliente base de API (fetch wrapper + `QueryClientProvider` de TanStack Query) en `frontend/src/services/apiClient.ts`
- [x] T009 Configurar manejo de errores y logging del backend en `backend/src/errors.py` (sin loguear credenciales ni datos sensibles, per constitución)

**Checkpoint**: Fundación lista — las historias de usuario pueden empezar.

---

## Phase 3: User Story 1 - Buscar y listar compras (Priority: P1) 🎯 MVP

**Goal**: Un usuario puede buscar compras por proveedor, número de documento o fecha, y ver un listado paginado.

**Independent Test**: Buscar "Rutas Sur" y verificar que aparecen sus compras ordenadas por fecha descendente (FR-001, FR-002).

### Tests for User Story 1

- [x] T010 [P] [US1] Contract test para `GET /api/compras` (búsqueda por proveedor/documento/fecha, paginación, caso sin resultados) en `backend/tests/contract/test_compras_list.py`, usando fixtures fijas per `contracts/compras-api.md`

### Implementation for User Story 1

- [x] T011 [P] [US1] Crear schema Pydantic `Compra` (`idCompra`, `fecha`, `proveedor.idContacto`, `proveedor.razonSocial`, `tipoDocumento`, `numeroDocumento`) en `backend/src/features/compras/schemas.py` per `data-model.md`
- [x] T012 [US1] Implementar consulta parametrizada de listado/búsqueda de compras (JOIN `Compras`/`Contactos`, filtros `proveedor`, `numeroDocumento`, `fechaDesde`, `fechaHasta`, orden por fecha descendente) en `backend/src/features/compras/repository.py`
- [x] T013 [US1] Implementar endpoint `GET /api/compras` en `backend/src/features/compras/router.py` (depende de T011, T012) per `contracts/compras-api.md`
- [x] T014 [US1] Registrar el router de compras en `backend/src/main.py` (depende de T013)
- [x] T015 [P] [US1] Crear página de listado/búsqueda de compras en `frontend/src/app/compras/page.tsx` consumiendo `GET /api/compras` vía TanStack Query
- [x] T016 [P] [US1] Crear componente de filtros + tabla de resultados en `frontend/src/components/compras/ComprasListado.tsx` (proveedor, número de documento, rango de fechas)
- [x] T017 [US1] Implementar estado vacío explícito ("sin resultados") en `ComprasListado.tsx` (depende de T016) per FR-012
- [x] T018 [US1] Implementar controles de paginación en `ComprasListado.tsx` (depende de T016) per FR-013

**Checkpoint**: User Story 1 funcional y verificable de forma independiente.

---

## Phase 4: User Story 2 - Ver el detalle e imputación de una compra (Priority: P1)

**Goal**: Un usuario abre una compra y ve sus líneas con imputación (rubro, centro de costo, destino) explícita.

**Independent Test**: Abrir una compra conocida y verificar que cada línea muestra rubro y, cuando exista, centro de costo/destino, o indica explícitamente que no está asignado (FR-004, FR-006).

### Tests for User Story 2

- [x] T019 [P] [US2] Contract test para `GET /api/compras/{idCompra}` cubriendo el caso `imputacion: null` explícito (FR-006) y el caso 404 en `backend/tests/contract/test_compras_detalle.py` per `contracts/compras-api.md`

### Implementation for User Story 2

- [x] T020 [P] [US2] Crear schemas Pydantic `LineaCompra` e `Imputacion` (`idRubro`/`rubro`, `idCentroCosto`/`centroCosto`, `idDestino`/`destino`, `idCampania`/`campania`, todos nullable — si son `NULL` el campo MUST devolverse explícito, nunca omitido, per FR-006) en `backend/src/features/compras/schemas.py` per `data-model.md`
- [x] T021 [US2] Implementar consulta de detalle (JOIN `Compras`/`Det_Compras`/`Rubros`/`[Centro de costos]`/`DestinoCompras`, usando los nombres reales confirmados el 2026-09-16 en `data-model.md`) en `backend/src/features/compras/repository.py` (depende de T020)
- [x] T022 [US2] Implementar endpoint `GET /api/compras/{idCompra}` con `404` si no existe en `backend/src/features/compras/router.py` (depende de T021)
- [x] T023 [P] [US2] Crear página de detalle de compra en `frontend/src/app/compras/[idCompra]/page.tsx`
- [x] T024 [US2] Crear componente de líneas de compra mostrando imputación o "sin imputar" explícito en `frontend/src/components/compras/DetalleCompra.tsx` (depende de T023) per FR-006
- [x] T025 [US2] Mostrar `conceptosNoGravados` e `ingresosBrutos` diferenciados de las líneas gravadas en `DetalleCompra.tsx` (depende de T024) per FR-007

**Checkpoint**: User Story 1 y 2 funcionan de forma independiente y en conjunto.

---

## Phase 5: User Story 3 - Navegar hacia los movimientos de cuenta corriente y tesorería (Priority: P2)

**Goal**: Desde una compra, ver la referencia a los movimientos de cuenta corriente/tesorería que generó, vía `IdOrigen`.

**Independent Test**: Tomar una compra con pagos registrados y verificar que se muestra la referencia a sus movimientos, o el estado "sin movimientos asociados" si no tiene (FR-008, FR-009).

### Tests for User Story 3

- [x] T026 [P] [US3] Contract test para `GET /api/compras/{idCompra}/trazabilidad` cubriendo el caso con movimientos y el caso vacío explícito en `backend/tests/contract/test_compras_trazabilidad.py` per `contracts/compras-api.md`

### Implementation for User Story 3

- [x] T027 [US3] Implementar consulta de movimientos donde `IdOrigen = idCompra` contra `vw_MovimientosCuenta_Base` en `backend/src/features/compras/repository.py`
- [x] T028 [US3] Implementar endpoint `GET /api/compras/{idCompra}/trazabilidad` en `backend/src/features/compras/router.py` (depende de T027)
- [x] T029 [US3] Agregar sección de trazabilidad al detalle de compra mostrando movimientos o "sin movimientos asociados todavía" en `frontend/src/components/compras/TrazabilidadCompra.tsx` (depende de T023) per FR-009

**Checkpoint**: Las 3 historias funcionan de forma independiente y en conjunto.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T030 Verificar contra `INFORMATION_SCHEMA.COLUMNS` de `Det_Compras` los nombres reales de las columnas de centro de costo/destino y actualizar `data-model.md`/`schemas.py` si difieren de lo asumido (per `quickstart.md` paso 1) — **resuelto 2026-09-16**: `IdCentroCostos`→`[Centro de costos].IdCentro`, `IdDestino`→`DestinoCompras.IdDestino`, `IdRubro`→`Rubros.IdRubro`; ver `data-model.md`
- [x] T031 Revisar que ningún endpoint del módulo acepte `POST`/`PUT`/`DELETE`/`PATCH` (FR-010) — revisión manual de `backend/src/features/compras/router.py`
- [x] T032 Ejecutar la validación completa de `quickstart.md` (backend + frontend + contract tests) contra datos reales de solo lectura — **verificado 2026-09-15**: 15/15 contract tests OK, `next build` sin advertencias, backend real contra DSN devolvió compras/detalle/trazabilidad correctos para "Rutas Sur Atlantico S.A." — **corrección posterior (mismo día, durante validación de 003-tesoreria)**: se detectó que `fechaDesde`/`fechaHasta` nunca se habían probado contra la base real; `cmp.Fecha` es `datetime` en SQL Server y pyodbc rechaza bindear un `datetime.date` contra esa columna (`HYC00 SQLBindParameter`). Se agregó `backend/src/db/params.py::as_sql_datetime` y se aplicó en `repository.py`; regresión cubierta en `backend/tests/test_db_params.py`
- [x] T033 [P] Documentar en `backend/src/features/compras/` un comentario breve sobre la regla de imputación única (FR-005) para futuros mantenedores
- [x] T034 Verificar que los endpoints de `backend/src/features/compras/router.py` estén declarados `async def` y que ninguna función de `repository.py` mantenga estado/caché en memoria entre requests, de forma que múltiples usuarios puedan leer en paralelo sin bloquearse entre sí (FR-014) — **corregido 2026-09-15**: las funciones de `repository.py` eran síncronas (pyodbc bloqueante) y se llamaban directo dentro de `async def`, lo cual bloqueaba el event loop entero por request. Se envolvieron todas las llamadas con `starlette.concurrency.run_in_threadpool` en `router.py`; `repository.py` no mantiene estado ni caché entre requests (cada función abre su propia conexión vía `get_connection()`)
- [x] T035 [P] Contract test que dispara múltiples requests concurrentes (`asyncio.gather` sobre varios `httpx.AsyncClient.get`) contra `GET /api/compras` y `GET /api/compras/{idCompra}` y verifica que todas responden 200 sin degradación ni errores de bloqueo, en `backend/tests/contract/test_compras_concurrencia.py` (depende de T013, T022) per FR-014

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; bloquea todas las historias.
- **User Stories (Phase 3-5)**: dependen de Foundational. US1 y US2 son ambas P1 y pueden avanzar en paralelo si hay capacidad; US3 depende de que exista al menos el modelo de `Compra` (T011) pero es independiente de US2.
- **Polish (Phase 6)**: depende de que las historias deseadas estén completas. **T030 debe resolverse antes de implementar T020/T021** (bloquea el modelo real de imputación). T034/T035 (FR-014, concurrencia) dependen de que existan endpoints de US1 y US2 (T013, T022) para poder probarlos, pero no bloquean ninguna historia — solo el cierre de Polish.

### Parallel Opportunities

- T003, T004 en paralelo con T002 (Setup).
- T007, T008 en paralelo con T005/T006 (Foundational).
- T010, T011 en paralelo al iniciar US1.
- T015, T016 en paralelo entre sí (frontend) una vez exista el contrato de API (T013).
- T019, T020 en paralelo al iniciar US2.
- T026 en paralelo con el inicio de US3.

---

## Parallel Example: User Story 1

```bash
Task: "Contract test para GET /api/compras en backend/tests/contract/test_compras_list.py"
Task: "Crear schema Pydantic Compra en backend/src/features/compras/schemas.py"
```

---

## Implementation Strategy

### MVP First

Dado que US1 y US2 son ambas P1, el MVP mínimo razonable es **Setup + Foundational + US1 + US2** (buscar/listar y ver detalle con imputación). US3 (trazabilidad hacia tesorería/cuenta corriente) agrega valor de auditoría pero no es indispensable para que el módulo sea útil por sí solo.

1. Completar Phase 1 (Setup) y Phase 2 (Foundational).
2. Completar Phase 3 (US1) y Phase 4 (US2) — validar ambas contra `quickstart.md` pasos 2-5.
3. **Detenerse y validar** el MVP de forma independiente.
4. Completar Phase 5 (US3) para cerrar la trazabilidad completa.
5. Completar Phase 6 (Polish), incluyendo la verificación de esquema real (T030) si no se hizo antes de US2.

### Nota sobre T030

T030 (verificar columnas reales de imputación) está en Polish por convención de plantilla, pero en la práctica **debe resolverse antes de T020/T021** — se lista temprano en esta sección para que no se pierda de vista.
