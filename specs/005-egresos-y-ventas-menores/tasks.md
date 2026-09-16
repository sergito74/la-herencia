# Tasks: Impuestos, remuneraciones, arrendamientos y ventas de hacienda (solo lectura)

**Input**: Design documents from `specs/005-egresos-y-ventas-menores/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/egresos-y-ventas-menores-api.md, quickstart.md

**Tests**: Incluidos, mismo criterio que `specs/002-004`.

**Organization**: Tareas agrupadas por historia de usuario. Reutiliza la misma app backend/frontend de compras/tesorería/cuentas corrientes.

## Path Conventions

`backend/src/`, `backend/tests/`, `frontend/src/` (misma app que `specs/002-004`).

---

## Phase 1: Setup

- [x] T001 Crear estructura `backend/src/features/impuestos/`, `.../remuneraciones/`, `.../arrendamientos/`, `.../ventas_hacienda/` (con `__init__.py`) en la app existente
- [x] T002 [P] Crear estructura `frontend/src/app/impuestos/`, `.../remuneraciones/`, `.../arrendamientos/`, `.../ventas-hacienda/` y `frontend/src/components/{impuestos,remuneraciones,arrendamientos,ventas-hacienda}/` en la app existente

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: Ninguna historia de usuario puede comenzar hasta completar esta fase.

- [x] T003 Crear `backend/src/features/impuestos/schemas.py` con `Impuesto`, `ImpuestosListResponse`, `Retencion`, `RetencionesListResponse` per `data-model.md`
- [x] T004 [P] Crear `backend/src/features/remuneraciones/schemas.py` con `Remuneracion` (incluye lista `pagos: list[PagoRemuneracion]`, MUST ser lista vacía si no hay pagos, nunca `null`) y `PagoRemuneracion` per `data-model.md`
- [x] T005 [P] Crear `backend/src/features/arrendamientos/schemas.py` con `Arrendamiento` (incluye lista `cobros: list[CobroAlquiler]`, MUST ser lista vacía si no hay cobros) y `CobroAlquiler` per `data-model.md`
- [x] T006 [P] Crear `backend/src/features/ventas_hacienda/schemas.py` con `VentaHacienda` (incluye lista `lineas: list[LineaVentaHacienda]`, MUST tener al menos un elemento per contrato), `LineaVentaHacienda` y `RetencionVentaHacienda` (entidad independiente, sin campo de venta) per `data-model.md`

**Checkpoint**: Fundación lista — schemas de las 4 features nuevas.

---

## Phase 3: User Story 1 - Consultar movimientos de Impuestos y Retenciones (Priority: P1)

**Goal**: Un usuario ve los movimientos de impuestos y retenciones con tipo, fecha, importe y organismo/contacto asociado.

**Independent Test**: Listar los movimientos de impuestos del organismo "ARBA" (contacto real conocido, `IdOrganismo = 12`, ver `research.md`) y verificar tipo de impuesto, fecha e importe.

### Tests for User Story 1

- [x] T007 [P] [US1] Contract test para `GET /api/impuestos` (búsqueda por organismo, filtro de fechas, estado vacío) en `backend/tests/contract/test_impuestos_api.py`
- [x] T008 [P] [US1] Contract test para `GET /api/impuestos/retenciones` (búsqueda por contacto, estado vacío) — combinado en `backend/tests/contract/test_impuestos_api.py` (un solo archivo por feature, mismo módulo que T007)

### Implementation for User Story 1

- [x] T009 [US1] Implementar `search_impuestos` en `backend/src/features/impuestos/repository.py`: join `Impuestos` → `Tipo Impuesto` (por `IdTipoImpuesto`) → `Contactos` (por `IdOrganismo`, nullable) (depende de T003)
- [x] T010 [US1] Implementar `search_retenciones` en `repository.py`: join `Retenciones` → `Contactos` (por `IdContacto`) (depende de T003)
- [x] T011 [US1] Implementar endpoints `GET /api/impuestos` y `GET /api/impuestos/retenciones` en `backend/src/features/impuestos/router.py` (depende de T009, T010)
- [x] T012 [US1] Registrar el router de impuestos en `backend/src/main.py`
- [x] T013 [P] [US1] Crear `frontend/src/services/impuestosApi.ts` (tipos + `fetchImpuestos`, `fetchRetenciones`)
- [x] T014 [P] [US1] Crear `frontend/src/app/impuestos/page.tsx` y `frontend/src/components/impuestos/ImpuestosListado.tsx` (listado de impuestos con estado vacío explícito)
- [x] T015 [US1] Crear `frontend/src/components/impuestos/RetencionesListado.tsx` e integrarlo en la página de impuestos (sección o tab separado) (depende de T014)
- [x] T016 [US1] Agregar la entrada "Impuestos" al submenú "Otros movimientos" en `frontend/src/components/layout/NavHeader.tsx` (crear el submenú si todavía no existe, per Nota UX de `plan.md`) y su tarjeta en `frontend/src/app/page.tsx`

**Checkpoint**: User Story 1 funcional de forma independiente.

---

## Phase 4: User Story 2 - Consultar liquidaciones de Remuneraciones y pagos efectivos (Priority: P1)

**Goal**: Un usuario ve las liquidaciones de remuneraciones de cada empleado, y consulta por separado los pagos efectivos de remuneraciones.

**Independent Test**: Listar las liquidaciones de un empleado conocido, y por separado listar los pagos de remuneraciones registrados.

**Nota de corrección (2026-09-17)**: el diseño original (liquidación + pagos anidados) se revirtió durante la implementación al confirmar contra datos reales que `Pagos Remuneraciones.IdEmpleado` no es una FK hacia `Contactos` (ver `research.md`). Las tareas de esta fase reflejan el diseño corregido: dos listados independientes.

### Tests for User Story 2

- [x] T017 [P] [US2] Contract test para `GET /api/remuneraciones` (búsqueda por empleado/período, estado vacío, caso sin empleado identificado) y `GET /api/remuneraciones/pagos` (listado independiente, sin campo de empleado) en `backend/tests/contract/test_remuneraciones_api.py`

### Implementation for User Story 2

- [x] T018 [US2] Implementar en `backend/src/features/remuneraciones/repository.py`: `search_remuneraciones` (join `Remuneraciones` → `Contactos` por `IdContacto`) — el campo `importe` MUST calcularse en SQL como la suma de todas las columnas monetarias de concepto de la fila (`Sueldo basico`, `Adic futuros aumentos`, `Ajuste`, `Vacaciones`, `Dia Gremio`, `Antiguedad`, `Ajuste No Remunerativo`, `Aguinaldo`, `Jubilacion`, `Ley 19032`, `Obra Social`, `Obra Social Acuerdos`, `Aporte Sindical`, `Servicio de Sepelio`, `Redondeo`, `Bonificacion adicional`), no en Python (per Nota de implementación de `data-model.md`) — y `search_pagos_remuneracion(page, page_size)` como listado independiente, SIN join a `Contactos` (confirmado: `IdEmpleado` no es una FK real) (depende de T004)
- [x] T019 [US2] Implementar endpoints `GET /api/remuneraciones` y `GET /api/remuneraciones/pagos` en `backend/src/features/remuneraciones/router.py` (depende de T018)
- [x] T020 [US2] Registrar el router de remuneraciones en `backend/src/main.py`
- [x] T021 [P] [US2] Crear `frontend/src/services/remuneracionesApi.ts`
- [x] T022 [P] [US2] Crear `frontend/src/app/remuneraciones/page.tsx` y `frontend/src/components/remuneraciones/RemuneracionesListado.tsx` — usar "Liquidación" para la liquidación; los pagos se muestran en una sección/tab separado del mismo módulo, SIN sugerir visualmente que están vinculados a un empleado o liquidación específica
- [x] T023 [US2] Agregar la entrada "Remuneraciones" al submenú "Otros movimientos" en `NavHeader.tsx`

**Checkpoint**: User Story 1 y 2 funcionan de forma independiente.

---

## Phase 5: User Story 3 - Consultar movimientos de Arrendamientos (Priority: P1)

**Goal**: Un usuario ve los contratos de arrendamiento con su detalle y cobros asociados.

**Independent Test**: Listar los arrendamientos de un contacto conocido y verificar que se muestran junto con sus cobros asociados.

### Tests for User Story 3

- [x] T024 [P] [US3] Contract test para `GET /api/arrendamientos` (incluye `cobros` anidados, caso sin cobros → lista vacía) en `backend/tests/contract/test_arrendamientos_api.py`

### Implementation for User Story 3

- [x] T025 [US3] Implementar en `backend/src/features/arrendamientos/repository.py`: `search_arrendamientos` (join `Alquileres` → `Contactos` por `IdContacto`) y `get_cobros_alquiler(id_alquiler)` (join directo `Detalle Cobro Alquiler` por `IdAlquiler`) (depende de T005)
- [x] T026 [US3] Implementar endpoint `GET /api/arrendamientos` en `backend/src/features/arrendamientos/router.py` (depende de T025)
- [x] T027 [US3] Registrar el router de arrendamientos en `backend/src/main.py`
- [x] T028 [P] [US3] Crear `frontend/src/services/arrendamientosApi.ts`
- [x] T029 [P] [US3] Crear `frontend/src/app/arrendamientos/page.tsx` y `frontend/src/components/arrendamientos/ArrendamientosListado.tsx` — usar "Arrendamiento" en toda etiqueta visible, nunca "Alquiler" (terminología per Nota UX de `plan.md`, aunque la tabla SQL se llame `Alquileres`)
- [x] T030 [US3] Agregar la entrada "Arrendamientos" al submenú "Otros movimientos" en `NavHeader.tsx`

**Checkpoint**: User Story 1, 2 y 3 funcionan de forma independiente.

---

## Phase 6: User Story 4 - Consultar movimientos de Ventas de Hacienda (Priority: P1)

**Goal**: Un usuario ve las ventas de hacienda con su detalle por comprador, y consulta por separado las retenciones de venta de hacienda.

**Independent Test**: Listar las ventas de hacienda de un período conocido, verificar que una venta con más de un comprador muestra cada línea con su propio comprador sin mezclarlos; listar por separado las retenciones de venta de hacienda de un contacto conocido.

### Tests for User Story 4

- [x] T031 [P] [US4] Contract test para `GET /api/ventas-hacienda` (líneas por comprador sin mezclar, `lineas` con al menos un elemento) en `backend/tests/contract/test_ventas_hacienda_api.py`
- [x] T032 [P] [US4] Contract test para `GET /api/ventas-hacienda/retenciones` (listado independiente, sin campo de venta) — combinado en `backend/tests/contract/test_ventas_hacienda_api.py` (un solo archivo por feature, mismo módulo que T031)

### Implementation for User Story 4

- [x] T033 [US4] Implementar `search_ventas_hacienda` en `backend/src/features/ventas_hacienda/repository.py`: join `Venta Hacienda` → `Contactos` (por `IdConsignatario`) + `Det_Ventas Hacienda` → `Contactos` (por `IdComprador`) → `Tipo Hacienda` (por `IdTipoProducto`); cada línea MUST incluir `[Precio unitario (A)]` y `[Precio unitario (B)]` tal cual (sin combinarlos en un único importe — ver `data-model.md`) (depende de T006)
- [x] T034 [US4] Implementar `search_retenciones_venta_hacienda` en `repository.py`: join `Retenciones Ventas Hacienda` → `Contactos` (por `IdContacto`) — **MUST NOT** intentar unir con `Venta Hacienda` (sin clave confiable, confirmado contra datos reales en `research.md`) (depende de T006)
- [x] T035 [US4] Implementar endpoints `GET /api/ventas-hacienda` y `GET /api/ventas-hacienda/retenciones` en `backend/src/features/ventas_hacienda/router.py` (depende de T033, T034)
- [x] T036 [US4] Registrar el router de ventas de hacienda en `backend/src/main.py`
- [x] T037 [P] [US4] Crear `frontend/src/services/ventasHaciendaApi.ts`
- [x] T038 [P] [US4] Crear `frontend/src/app/ventas-hacienda/page.tsx` y `frontend/src/components/ventas-hacienda/VentasHaciendaListado.tsx` — "Consignatario" a nivel de venta, "Comprador" por línea de detalle (terminología per Nota UX de `plan.md`); mostrar `precioUnitarioA` y `precioUnitarioB` como dos columnas separadas, sin calcular ni mostrar un total combinado
- [x] T039 [US4] Crear `frontend/src/components/ventas-hacienda/RetencionesVentaHaciendaListado.tsx` como listado independiente (NO anidado bajo una venta) e integrarlo en la página (depende de T038)
- [x] T040 [US4] Agregar la entrada "Ventas de Hacienda" al submenú "Otros movimientos" en `NavHeader.tsx` — completa las 4 entradas del submenú

**Checkpoint**: Las 4 historias de dominio (US1-US4) funcionan de forma independiente.

---

## Phase 7: User Story 5 - Navegar desde cuentas corrientes hacia estos orígenes (Priority: P1)

**Goal**: Un movimiento de cuenta corriente con `Origen` en los 5 valores cubiertos resuelve a una referencia real, no a `fuera_de_alcance`.

**Independent Test**: Tomar un movimiento de cuenta corriente con cada uno de los 5 valores de `Origen` cubiertos (usar los casos reales de `research.md`: contacto 72 para Impuestos) y verificar que el sistema muestra la referencia real; confirmar que `Ret. IVA Granos` sigue devolviendo `fuera_de_alcance`.

### Tests for User Story 5

- [x] T041 [P] [US5] Ampliar `backend/tests/contract/test_cc_origen.py` con los 5 nuevos casos (`impuesto`, `retencion`, `remuneracion`, `arrendamiento`, `venta_hacienda`) y un caso que confirme que `Ret. IVA Granos` sigue resolviendo `fuera_de_alcance`

### Implementation for User Story 5

- [x] T042 [US5] Ampliar `backend/src/features/cuentas_corrientes/schemas.py`: agregar a `Origen` los campos opcionales de los 5 nuevos tipos (`idImpuesto`, `tipoImpuesto`, `idRetencion`, `numeroCertificado`, `idSalario`, `periodoLiquidado`, `empleado`, `idAlquiler`, `contacto`, `importeTotalContrato`) per `data-model.md`
- [x] T043 [US5] Ampliar `backend/src/features/cuentas_corrientes/origen_resolver.py`: agregar el mapeo `Impuestos`→`impuesto`, `Retenciones`→`retencion`, `Remuneraciones`→`remuneracion`, `Alquileres`→`arrendamiento`, `Ret. Ventas Hacienda`→`venta_hacienda`. **Esta tarea incluye crear 5 funciones nuevas de lookup por clave primaria** (una por dominio, ej. `impuestos.repository.get_impuesto_referencia(id_impuesto)`, `remuneraciones.repository.get_remuneracion_referencia(id_salario)`, etc. — mismo patrón que `get_compra_referencia`/`get_bna_referencia` ya existentes en `cuentas_corrientes/repository.py`), distintas de las funciones de búsqueda paginada `search_*` (T009, T010, T018, T025, T034) de las que depende solo en el sentido de que ambas comparten el mismo módulo `repository.py` de cada dominio, no en que las reutilice directamente (una búsqueda paginada y un lookup por PK son consultas SQL distintas) (depende de T009, T010, T018, T025, T034 solo por existir esos módulos `repository.py`)
- [x] T044 [P] [US5] Ampliar `frontend/src/components/cuentas-corrientes/OrigenMovimiento.tsx` con 5 nuevos `case` explícitos (mismo patrón que `compra`/`tesoreria`, sin rama genérica)
- [x] T045 [US5] Ampliar el tipo `Origen` en `frontend/src/services/cuentasCorrientesApi.ts` con los 5 nuevos valores de `tipo` y sus campos asociados

**Checkpoint**: MVP completo — las 5 historias de usuario (P1) funcionan de forma independiente y en conjunto.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [x] T046 Reestructurar `frontend/src/components/layout/NavHeader.tsx` a 2 niveles: `Compras`/`Tesorería`/`Cuentas corrientes` como entradas top-level, y un submenú desplegable "Otros movimientos" agrupando Impuestos/Remuneraciones/Arrendamientos/Ventas de Hacienda (depende de T016, T023, T030, T040 — confirmar que las 4 entradas ya existen antes de reestructurar el contenedor)
- [x] T047 Reestructurar `frontend/src/app/page.tsx` en 2 niveles visuales: fila destacada (Tesorería, Cuentas Corrientes, Compras) y sección secundaria compacta para los 4 módulos nuevos, per Nota UX de `plan.md`
- [x] T048 Revisar que ningún endpoint nuevo (`impuestos`, `remuneraciones`, `arrendamientos`, `ventas_hacienda`) acepte `POST`/`PUT`/`DELETE`/`PATCH` (FR-008)
- [x] T049 Confirmar que ninguna respuesta de los 4 módulos nuevos expone imputación cruzada (rubro/centro de costo/destino) (FR-007) — revisión manual de los 4 `schemas.py`
- [x] T050 [P] Contract test de concurrencia para los 4 endpoints nuevos (`asyncio.gather` sobre varios `httpx.AsyncClient.get`) en `backend/tests/contract/test_egresos_concurrencia.py`, mismo patrón que `test_cc_concurrencia.py` (depende de T011, T019, T026, T035) per FR-011
- [x] T051 Ejecutar la validación completa de `quickstart.md` contra datos reales de solo lectura, incluyendo los casos ya confirmados en `research.md` (contacto 72 = Impuestos, 5 filas en `Alquileres`, venta de hacienda con múltiples compradores)
- [x] T052 [P] Escalar a `04-integrated-agro-management-engineer` la duda documentada en `plan.md` (Nota UX) sobre si "campaña" aplica a Ventas de Hacienda con el mismo sentido que en agricultura, antes de fijar el filtro por defecto de período en ese módulo — documentar la respuesta en `research.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; bloquea todas las historias.
- **User Stories (Phase 3-7)**: dependen de Foundational. US1-US4 son independientes entre sí (dominios sin relación estructural). US5 depende de que US1-US4 tengan sus funciones de `repository.py` implementadas (T009, T010, T018, T025, T034), pero no de que sus páginas de frontend estén completas.
- **Polish (Phase 8)**: T046/T047 dependen de que las 4 entradas de nav/dashboard existan (fin de Phase 6); T048-T052 dependen de que los endpoints correspondientes existan, pero no bloquean ninguna historia.

### Parallel Opportunities

- T002 en paralelo con T001.
- T004, T005, T006 en paralelo entre sí (y con T003).
- T007, T008 en paralelo al iniciar US1.
- T013, T014 en paralelo una vez exista el contrato (T011).
- T017 en paralelo con el inicio de US2; T021, T022 en paralelo una vez exista T019.
- T024 en paralelo con el inicio de US3; T028, T029 en paralelo una vez exista T026.
- T031, T032 en paralelo al iniciar US4; T037, T038 en paralelo una vez exista T035.
- T041 en paralelo con el inicio de US5; T044 en paralelo con T042/T043.
- T050, T052 en paralelo con el resto de Polish.

---

## Parallel Example: User Story 1

```bash
Task: "Contract test para GET /api/impuestos en backend/tests/contract/test_impuestos_api.py"
Task: "Crear frontend/src/services/impuestosApi.ts"
```

---

## Implementation Strategy

### MVP First

Las 5 historias son P1 — no hay una historia "opcional" en este spec, a diferencia de 004 (donde US3 era P2). El MVP es **Setup + Foundational + US1 + US2 + US3 + US4 + US5** completo, porque el valor de negocio (cerrar 5 de 6 `fuera_de_alcance`) solo se entrega cuando las 4 fuentes de datos existen Y la navegación desde cuentas corrientes las resuelve.

1. Completar Phase 1 (Setup) y Phase 2 (Foundational).
2. Completar Phase 3 a 6 (US1-US4) — cada una entrega valor de forma independiente y puede validarse por separado contra `quickstart.md`.
3. Completar Phase 7 (US5) — cierra el círculo de trazabilidad, es el objetivo final del spec.
4. Completar Phase 8 (Polish) — incluye la reestructuración de navegación (T046/T047), que requiere que las 4 entradas ya existan.

### Cierre de brechas de cuentas corrientes

Con este spec completo, 5 de los 6 estados `fuera_de_alcance` de `specs/004-cuentas-corrientes` quedan resueltos. Solo `Ret. IVA Granos` permanece pendiente, para la futura spec de Agricultura (fase 3 del roadmap, ver plan de migración completo).
