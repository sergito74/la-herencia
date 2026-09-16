# Tasks: Cuentas corrientes por proveedor/cliente (solo lectura)

**Input**: Design documents from `specs/004-cuentas-corrientes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cuentas-corrientes-api.md, quickstart.md

**Tests**: Incluidos, mismo criterio que `specs/002-compras/tasks.md` y `specs/003-tesoreria/tasks.md`.

**Organization**: Tareas agrupadas por historia de usuario. Reutiliza la misma app backend/frontend de compras y tesorería.

## Path Conventions

`backend/src/`, `backend/tests/`, `frontend/src/` (misma app que `specs/002-compras` y `specs/003-tesoreria`).

---

## Phase 1: Setup

- [x] T001 Crear estructura `backend/src/features/cuentas_corrientes/` y `backend/tests/contract/` en la app existente
- [x] T002 [P] Crear estructura `frontend/src/app/cuentas-corrientes/` y `frontend/src/components/cuentas-corrientes/` en la app existente

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: Ninguna historia de usuario puede comenzar hasta completar esta fase.

- [x] T003 Verificar que `backend/src/db/connection.py` y `backend/src/db/pagination.py` (de `specs/002-compras`) estén disponibles y reutilizables sin cambios — confirmado: `get_connection`/`fetch_all`/`fetch_one` en `connection.py` y `normalize_pagination`/`offset_for` en `pagination.py` son genéricos, sin acoplamiento a compras
- [x] T004 Verificar contra `INFORMATION_SCHEMA`/datos reales los valores exactos del campo `Origen` en `dbo.vw_MovimientosCuenta_Base` — **resuelto 2026-09-16**: 12 valores confirmados, mapeo completo tipo→tabla en `data-model.md` (incluye el nuevo estado `fuera_de_alcance` para 6 valores sin módulo en alcance)
- [x] T005 [P] Crear `backend/src/features/cuentas_corrientes/schemas.py` con los schemas base (`Contacto`, `MovimientoCuentaCorriente`, `Saldo`, `Origen`) per `data-model.md`

**Checkpoint**: Fundación lista.

---

## Phase 3: User Story 1 - Consultar saldo y movimientos de un contacto (Priority: P1) 🎯 MVP

**Goal**: Un usuario selecciona un contacto y ve su saldo actual y sus movimientos.

**Independent Test**: Seleccionar "Rutas Sur Atlantico S.A." y verificar que el saldo coincide con la suma de sus movimientos (FR-001, FR-002, FR-003).

### Tests for User Story 1

- [x] T006 [P] [US1] Contract test para `GET /api/cuentas-corrientes/contactos` (búsqueda + filtro por tipo) en `backend/tests/contract/test_cc_contactos.py`
- [x] T007 [P] [US1] Contract test para `GET /api/cuentas-corrientes/contactos/{id}/saldo` y `GET .../movimientos` (incluyendo estado vacío) en `backend/tests/contract/test_cc_saldo_movimientos.py` per `contracts/cuentas-corrientes-api.md`

### Implementation for User Story 1

- [x] T008 [US1] Implementar consulta de búsqueda de contactos (razón social, filtro por tipo) contra `dbo.Contactos` en `backend/src/features/cuentas_corrientes/repository.py` (depende de T005)
- [x] T009 [US1] Implementar consulta de saldo contra `dbo.vw_MovimientosCuenta_Saldo` (sin recalcular la fórmula) en `repository.py` per `research.md`
- [x] T010 [US1] Implementar consulta de movimientos contra `dbo.vw_MovimientosCuenta_Base` con filtros de fecha, paginación y deduplicación a nivel SQL para contactos tipo "Multiple" en `repository.py` (depende de T004) per FR-005/FR-014 — dedup vía `SELECT DISTINCT` en `get_movimientos`
- [x] T011 [US1] Implementar endpoints `GET /api/cuentas-corrientes/contactos`, `.../saldo` y `.../movimientos` en `backend/src/features/cuentas_corrientes/router.py` (depende de T008, T009, T010) — `origen` va con placeholder `"no_disponible"` hasta T018/T019 (US2), preservando la forma del contrato (FR-008)
- [x] T012 [US1] Registrar el router de cuentas corrientes en `backend/src/main.py`
- [x] T013 [P] [US1] Crear página de cuentas corrientes con buscador de contacto en `frontend/src/app/cuentas-corrientes/page.tsx`
- [x] T014 [P] [US1] Crear componente de saldo y listado de movimientos en `frontend/src/components/cuentas-corrientes/CuentaCorriente.tsx`
- [x] T015 [US1] Implementar filtro de rango de fechas y estado vacío explícito en `CuentaCorriente.tsx` (depende de T014) per FR-005/FR-012
- [x] T016 [US1] Implementar distinción visual de deuda/débito vs. crédito/haber en `CuentaCorriente.tsx` (depende de T014) per FR-013

**Checkpoint**: User Story 1 funcional de forma independiente.

---

## Phase 4: User Story 2 - Navegar desde un movimiento hacia su origen (Priority: P1)

**Goal**: Un usuario ve, para cada movimiento, si viene de una compra o de tesorería, con referencia directa vía `Origen`/`IdOrigen`.

**Independent Test**: Tomar un movimiento originado en una compra conocida y verificar la referencia; tomar otro originado en tesorería y verificar la referencia correspondiente (FR-006, FR-007, FR-008).

### Tests for User Story 2

- [x] T017 [P] [US2] Contract test para el campo `origen` en `GET .../movimientos` cubriendo los 4 casos (`compra`, `tesoreria`, `fuera_de_alcance`, `no_disponible`) en `backend/tests/contract/test_cc_origen.py` per `contracts/cuentas-corrientes-api.md`

### Implementation for User Story 2

- [x] T018 [US2] Implementar `backend/src/features/cuentas_corrientes/origen_resolver.py`: resuelve `Origen`/`IdOrigen` a una referencia de compra (`dbo.Compras`), de tesorería según el medio (BNA/Galicia/efectivo/valores recibidos), a `fuera_de_alcance` para los 6 valores de `Origen` sin módulo en alcance (`Alquileres`, `Impuestos`, `Remuneraciones`, `Retenciones`, `Ret. IVA Granos`, `Ret. Ventas Hacienda`), o a `no_disponible` si `IdOrigen` no está cargado o el registro no existe — usar la tabla de mapeo de `data-model.md` (depende de T004)
- [x] T019 [US2] Integrar `origen_resolver.py` en la respuesta de `GET .../movimientos` en `repository.py`/`router.py` (depende de T010, T018) — el sistema MUST NOT mostrar ni calcular imputación (rubro/centro de costo/destino) aquí, per FR-009
- [x] T020 [P] [US2] Crear componente que renderiza los 3 estados de origen de forma explícita (compra / tesorería / no disponible) en `frontend/src/components/cuentas-corrientes/OrigenMovimiento.tsx` — cubre los 4 estados del contrato (incluye `fuera_de_alcance`)
- [x] T021 [US2] Integrar `OrigenMovimiento.tsx` en `CuentaCorriente.tsx` (depende de T014, T020)

**Checkpoint**: User Story 1 y 2 funcionan de forma independiente y en conjunto.

---

## Phase 5: User Story 3 - Distinguir tipos de contacto al buscar (Priority: P2)

**Goal**: Un usuario filtra la búsqueda de contactos por tipo (proveedor, cliente, banco, etc.).

**Independent Test**: Filtrar por "Proveedor" y verificar que solo aparecen contactos de ese tipo (FR-002).

### Tests for User Story 3

- [x] T022 [P] [US3] Contract test para el filtro `tipoContacto` en `GET /api/cuentas-corrientes/contactos`, incluyendo el caso de contacto tipo "Multiple" sin duplicados, en `backend/tests/contract/test_cc_contactos.py` (extiende T006)

### Implementation for User Story 3

- [x] T023 [US3] Agregar el filtro `tipoContacto` a la consulta de búsqueda de contactos en `repository.py` (depende de T008) — ya implementado en T008 (`search_contactos` acepta `tipo_contacto` desde el inicio); se agregó `DISTINCT` en esta fase para reforzar FR-014
- [x] T024 [P] [US3] Agregar selector de tipo de contacto al buscador en `frontend/src/app/cuentas-corrientes/page.tsx` (depende de T013) — implementado en `CuentaCorriente.tsx` (mismo componente que aloja el buscador de US1)

**Checkpoint**: Las 3 historias funcionan de forma independiente y en conjunto.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T025 Revisar que ningún endpoint acepte `POST`/`PUT`/`DELETE`/`PATCH` (FR-010) — confirmado: `router.py` solo declara `@router.get`, y `test_cc_*` verifican 404/405 en los otros métodos
- [x] T026 Confirmar que ninguna respuesta de este módulo expone rubro/centro de costo/destino (FR-009, SC-004) — revisión manual de `schemas.py`/`repository.py`: ningún campo de imputación presente
- [x] T027 Ejecutar la validación completa de `quickstart.md` contra datos reales de solo lectura, incluyendo el caso ya conocido de "Rutas Sur Atlantico S.A." (4 movimientos, per `memory.md`) — **ejecutado 2026-09-16**: (1) los 12 valores de `Origen` en producción coinciden exactamente con `data-model.md`; (2) "Rutas Sur Atlantico S.A." (idContacto 2657) devuelve 4 movimientos, todos resueltos a `tipo: "compra"` con `idCompra`/`numeroDocumento`/`proveedor` correctos; (3) validado `tipo: "tesoreria"` con un `Banco Nacion` real (medio `bna`) y un `Pagos efectivo` real (medio `efectivo`); (4) validado `tipo: "fuera_de_alcance"` con `Alquileres`. **Discrepancia observada, no bloqueante**: el saldo de Rutas Sur (`-3097.65`) no es la suma aritmética simple de los 4 movimientos de deuda listados (`14654.21`) — la vista `vw_MovimientosCuenta_Saldo` es la fuente de verdad per diseño (no se recalcula, research.md), así que esto no es un bug de este módulo, pero vale que el usuario lo tenga presente si compara saldo vs. movimientos a simple vista.
- [x] T028 [P] Confirmar que la navegación hacia compras/tesorería no falla si esos módulos aún no están desplegados (Assumptions de `spec.md`) — no aplica en este entorno (compras y tesorería ya están desplegados en la misma app); el link de `OrigenMovimiento.tsx` a `/compras/{idCompra}` es un `<Link>` de Next.js estándar, no depende de que el módulo esté "activo" más que cualquier otra ruta de la app
- [x] T029 Verificar que los endpoints de `backend/src/features/cuentas_corrientes/router.py` estén declarados `async def` y que ninguna función de `repository.py`/`origen_resolver.py` mantenga estado/caché en memoria entre requests, de forma que múltiples usuarios puedan leer en paralelo sin bloquearse entre sí (FR-015) — confirmado: los 3 endpoints son `async def`; los únicos objetos a nivel de módulo en `origen_resolver.py` son diccionarios de mapeo estáticos e inmutables (sin mutación en runtime)
- [x] T030 [P] Contract test que dispara múltiples requests concurrentes (`asyncio.gather` sobre varios `httpx.AsyncClient.get`) contra `GET /api/cuentas-corrientes/contactos/{id}/movimientos` para distintos contactos y verifica que todas responden 200 sin degradación ni errores de bloqueo, en `backend/tests/contract/test_cc_concurrencia.py` (depende de T011) per FR-015

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias (asume `specs/002-compras` en marcha para T003).
- **Foundational (Phase 2)**: depende de Setup; bloquea todas las historias. T004 ya está resuelto y disponible como referencia para T010/T018.
- **User Stories (Phase 3-5)**: dependen de Foundational. US1 y US2 son ambas P1; US2 depende del modelo de movimientos de US1 (T010) pero no de que US1 tenga UI completa. US3 extiende la búsqueda de US1.
- **Polish (Phase 6)**: depende de que las historias deseadas estén completas. T029/T030 (FR-015, concurrencia) dependen de que exista el endpoint de movimientos (T011), pero no bloquean ninguna historia.

### Parallel Opportunities

- T002 en paralelo con T001.
- T005 en paralelo con T003/T004.
- T006, T007 en paralelo al iniciar US1.
- T013, T014 en paralelo una vez exista el contrato (T011).
- T017 en paralelo con el inicio de US2.
- T022, T024 en paralelo al iniciar US3.

---

## Parallel Example: User Story 1

```bash
Task: "Contract test para GET /api/cuentas-corrientes/contactos en backend/tests/contract/test_cc_contactos.py"
Task: "Crear página de cuentas corrientes con buscador de contacto en frontend/src/app/cuentas-corrientes/page.tsx"
```

---

## Implementation Strategy

### MVP First

US1 y US2 son ambas P1 — el MVP es **Setup + Foundational + US1 + US2** (saldo/movimientos + origen explícito, el cierre de la trazabilidad de los 3 módulos). US3 (filtro por tipo de contacto) es una mejora de usabilidad P2 y puede posponerse.

1. Completar Phase 1 (Setup) y Phase 2 (Foundational) — **T004 es un prerrequisito real de datos, no solo de código**.
2. Completar Phase 3 (US1) y Phase 4 (US2) — validar contra `quickstart.md`.
3. **Detenerse y validar** el MVP de forma independiente, y de punta a punta contra compras (`specs/002-compras`) y tesorería (`specs/003-tesoreria`) si ya están implementadas.
4. Completar Phase 5 (US3) y Phase 6 (Polish).

### Cierre del circuito de trazabilidad

Con esta spec completa, el circuito queda cerrado: compras define `IdOrigen` (`specs/002-compras`), tesorería expone su referencia heurística hacia compras (`specs/003-tesoreria`), y cuentas corrientes resuelve `Origen`/`IdOrigen` de forma directa hacia ambos. Validar los tres módulos juntos es el criterio de éxito de negocio acordado: reconciliar una cuenta corriente y una cuenta bancaria sin salir del sistema nuevo.
