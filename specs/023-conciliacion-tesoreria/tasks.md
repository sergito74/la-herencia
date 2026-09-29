---

description: "Task list for 023-conciliacion-tesoreria"
---

# Tasks: Conciliación de Tesorería

**Input**: Design documents from `specs/023-conciliacion-tesoreria/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/conciliacion-tesoreria-api.md, quickstart.md

**Tests**: incluidos — el resto del sistema (022, 021) ya usa tests de contrato/repository para este tipo de escrituras financieras, y la Constitución (Principio V) exige el chequeo automatizado más acotado para cada cambio.

**Organización**: por historia de usuario (spec.md). US1 y US3 son ambas P1 (MVP real = las dos juntas: conciliar sin duplicar no tiene sentido sin la guarda de duplicado). US2 (P2) agrega el reparto incremental sobre la misma base.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede hacerse en paralelo (archivos distintos, sin dependencia de una tarea no terminada)
- **[Story]**: US1 / US2 / US3, mapeado a spec.md

## Path Conventions (de plan.md)

- Backend: `backend/src/features/conciliacion_tesoreria/`, `backend/src/features/tesoreria/`, `backend/src/features/reasignacion_contacto/`, `backend/scripts/`, `backend/tests/`
- Frontend: `frontend/src/components/tesoreria/`, `frontend/src/components/cuentas-corrientes/`, `frontend/src/services/`

---

## Phase 1: Setup

**Propósito**: esqueleto del módulo backend nuevo, sin lógica todavía.

- [X] T001 Crear `backend/src/features/conciliacion_tesoreria/__init__.py`, `repository.py`, `schemas.py`, `router.py` vacíos, siguiendo la misma estructura que `backend/src/features/reasignacion_contacto/` (mismo patrón ya validado en 022).
- [X] T002 [P] Registrar el router nuevo (`conciliacion_tesoreria.router`) en `backend/src/main.py`, sin endpoints todavía (placeholder), para que el resto de las tareas puedan agregar rutas de forma incremental.

**Checkpoint**: el módulo existe y arranca sin romper el backend, sin funcionalidad aún.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Propósito**: el cambio de esquema en `WC` y la extensión de 022 que TODAS las historias necesitan. Ninguna historia puede implementarse (ni siquiera testearse) sin esto.

**⚠️ CRÍTICO**: `WC` es producción (Constitución, Principio II) — T004/T005 son un cambio de esquema real y requieren el backup verificado de T003 antes de ejecutarse.

- [X] T003 Confirmar y documentar un backup verificado de `WC` tomado antes de cualquier escritura de esta fase (Constitution Check del plan.md) — dejar constancia (fecha, método de verificación) en el propio `backend/scripts/crear_tabla_conciliaciones_tesoreria.py` como comentario, y pedir confirmación explícita del usuario antes de correr T006.
- [X] T004 En `backend/scripts/crear_tabla_conciliaciones_tesoreria.py`, escribir el DDL re-corrible (`IF NOT EXISTS`) de `dbo.ConciliacionesTesoreria` exactamente como en data-model.md: `IdConciliacion` int identity PK; `Medio` varchar(20) con `CHECK` en los 6 valores soportados (`bna`, `galicia`, `mercado-libre`, `efectivo`, `valores-propios`, `valores-recibidos` — nunca `tarjetas`, FR-002); `IdMovimiento` bigint; `IdContacto` int `FOREIGN KEY` → `Contactos.IdContacto`; `Importe` money con `CHECK (Importe > 0)`; `Usuario` varchar; `Fecha` datetime `DEFAULT getdate()`.
- [X] T005 En el mismo script, agregar el `ALTER VIEW dbo.vw_MovimientosCuenta_Base` aditivo (nueva rama `UNION ALL`, sin tocar las ramas existentes) que lee `ConciliacionesTesoreria`, resuelve `Origen = 'Conciliación Tesorería'`, `IdOrigen = IdConciliacion`, y el importe/fecha/signo original según `Medio` (data-model.md §Cambio de esquema) — un `CASE`/`JOIN` por medio para obtener el importe total original y decidir Deuda vs Crédito.
- [X] T006 Ejecutar `crear_tabla_conciliaciones_tesoreria.py` contra `WC` (solo después de T003 confirmado) y verificar: la tabla existe y está vacía; la vista sigue compilando; los saldos de una muestra de contactos conocidos (Compras/Impuestos/etc.) no cambiaron respecto de antes del `ALTER VIEW` (quickstart.md, "Verificación de no regresión").
- [X] T007 [P] En `backend/src/features/reasignacion_contacto/repository.py`, extender `ORIGENES_SOPORTADOS` para incluir `"Conciliación Tesorería"`, y `_contacto_original` para resolverlo con `SELECT IdContacto FROM dbo.ConciliacionesTesoreria WHERE IdConciliacion = ?` (FR-008a) — sin tocar el mecanismo de override (`OUTER APPLY`) ni la detección automática de candidatos (US2 de 022), que quedan sin cambios.
- [X] T008 [P] Test de repository: `backend/tests/test_reasignacion_contacto_repository.py` — caso nuevo que reasigna un origen `"Conciliación Tesorería"` y verifica que `_contacto_efectivo` refleja el override, igual que ya lo hace para Galicia/Banco Nación.

**Checkpoint**: esquema listo en `WC`, 022 sabe corregir este origen nuevo — recién ahora pueden empezar las historias.

---

## Phase 3: User Story 1 - Conciliar un movimiento con un único contacto (Priority: P1) 🎯 MVP

**Goal**: desde un listado de Tesorería, asignar un movimiento sin contacto a un único contacto, con efecto real en su cuenta corriente.

**Independent Test**: sobre uno de los 34 movimientos BNA sin contacto en `WC` real, conciliarlo a un contacto y verificar que aparece en su cuenta corriente con el importe correcto (quickstart.md, Escenario 1).

### Tests for User Story 1

- [X] T009 [P] [US1] Contract test `GET .../conciliacion` (estado `sin_conciliar`, `importeTotal`, `saldoPendiente` completo), `POST .../conciliacion` (caso simple, importe = saldo total), y `POST /api/tesoreria/tarjetas/movimientos/{id}/conciliacion` responde 400 con mensaje dirigiendo a 008/009 (FR-002), en `backend/tests/contract/test_conciliacion_tesoreria_api.py`, mockeando el repository (mismo patrón que `test_tesoreria_referencia.py`).
- [X] T010 [P] [US1] Test de repository: `aplicar_conciliacion` con importe igual al total dado de alta en `dbo.ConciliacionesTesoreria`, y `calcular_estado` devuelve `conciliado` después, en `backend/tests/test_conciliacion_tesoreria_repository.py`.

### Implementation for User Story 1

- [X] T011 [US1] En `backend/src/features/conciliacion_tesoreria/schemas.py`, definir `ConciliacionRequest` (`idContacto: int`, `importe: float`, `importe > 0`), `Conciliacion` (respuesta del POST/ítem del GET) y `EstadoConciliacion` (`estado`, `importeTotal`, `saldoPendiente`, `conciliaciones: list[Conciliacion]`) exactamente como en `contracts/conciliacion-tesoreria-api.md`.
- [X] T012 [US1] En `backend/src/features/conciliacion_tesoreria/repository.py`, implementar `calcular_estado(medio, id_movimiento)`: resuelve el importe total y el `IdContacto` original del movimiento según `medio` (consultando la tabla de origen correspondiente), calcula `saldo_pendiente = importe_total - SUM(Importe) FROM ConciliacionesTesoreria WHERE Medio=? AND IdMovimiento=?`, y devuelve `estado` = `ya_reconocido` si el `IdContacto` original (considerando el override vigente de 022) no es nulo, o `sin_conciliar`/`parcialmente_conciliado`/`conciliado` según el saldo pendiente (data-model.md).
- [X] T013 [US1] En el mismo `repository.py`, implementar `aplicar_conciliacion(medio, id_movimiento, id_contacto, importe, usuario)`: valida `medio` soportado (rechaza `tarjetas`, FR-002), `id_contacto` existe, `importe > 0`, movimiento no `ya_reconocido` (FR-008), e `importe` no excede el saldo pendiente recalculado dentro de la misma transacción (FR-010, research.md §5) antes del `INSERT`.
- [X] T014 [US1] En `backend/src/features/conciliacion_tesoreria/router.py`, implementar `GET /api/tesoreria/{medio}/movimientos/{id_movimiento}/conciliacion` y `POST` (mismo endpoint), devolviendo los códigos de error de `contracts/conciliacion-tesoreria-api.md` (400/404/409).
- [X] T015 [US1] En `backend/src/features/tesoreria/repository.py` y `schemas.py`, agregar `estadoConciliacion` (mismos 4 valores) a cada ítem de `get_movimientos` para los 5 medios cubiertos (no `tarjetas`), reutilizando `calcular_estado` (FR-009) — evita una llamada aparte por fila en el listado.
- [X] T016 [US1] Crear `frontend/src/services/conciliacionTesoreriaApi.ts`: `fetchEstadoConciliacion(medio, idMovimiento)` y `postConciliacion(medio, idMovimiento, {idContacto, importe})`, tipado según el contrato.
- [X] T017 [US1] Crear `frontend/src/components/tesoreria/ConciliarMovimiento.tsx`: acción/panel que busca contacto vía `ContactoSelect` (mismo componente reusado en todo el sistema), muestra la candidata de "Referencia de origen" como atajo si existe (FR-007, reusando `fetchReferenciaOrigen` ya existente), pide confirmación explícita antes del POST (FR-003).
- [X] T018 [US1] Integrar `ConciliarMovimiento` en `frontend/src/components/tesoreria/MovimientosPorMedio.tsx`: nueva columna/acción de conciliar visible solo para los 5 medios cubiertos (excluir `tarjetas`, FR-001/FR-002).
- [X] T019 [US1] En `MovimientosPorMedio.tsx`, mostrar el estado de conciliación por fila (`estadoConciliacion` de T015) con un badge, distinguiendo visualmente `sin_conciliar` de `conciliado` (FR-009; el estado `parcialmente_conciliado` se completa en Phase 5/US2).
- [X] T019a [US1] Test de integración: tras `aplicar_conciliacion(medio, id_movimiento, id_contacto, importe, usuario)`, consultar `cuentas_corrientes.repository.get_movimientos(id_contacto)` (o el endpoint equivalente) y verificar que aparece una fila nueva con `Origen = 'Conciliación Tesorería'`, el importe correcto en Debe/Haber según el signo del movimiento original, y que el saldo del contacto se actualiza en consecuencia — en `backend/tests/test_conciliacion_tesoreria_repository.py` o `backend/tests/test_cuentas_corrientes_saldos.py` (FR-005).

**Checkpoint**: un movimiento simple se puede conciliar de punta a punta y se ve reflejado en cuenta corriente — MVP parcial (falta la guarda de duplicado de US3 para ser seguro en producción).

---

## Phase 4: User Story 3 - Evitar conciliar dos veces el mismo movimiento (Priority: P1)

**Goal**: ningún movimiento ya reconocido por otro origen (o ya conciliado) puede volver a conciliarse desde cero, para no duplicar el efecto contable.

**Independent Test**: intentar conciliar un movimiento Galicia que YA tiene contacto (la mayoría de los 113 que no lo tienen son la excepción) y verificar que el sistema lo rechaza / no ofrece la acción (quickstart.md, Escenario 3).

### Tests for User Story 3

- [X] T020 [P] [US3] Test de repository: `aplicar_conciliacion` sobre un movimiento `ya_reconocido` (con `IdContacto` ya asignado en su tabla de origen) lanza el error correspondiente, sin insertar nada, en `backend/tests/test_conciliacion_tesoreria_repository.py`.
- [X] T021 [P] [US3] Test de repository: dos llamadas a `aplicar_conciliacion` sobre el mismo movimiento cuya suma excede el importe total — la segunda falla con el saldo pendiente recalculado, no con el que tenía al principio (FR-010).
- [X] T022 [P] [US3] Test de no regresión: `backend/tests/test_cuentas_corrientes_saldos.py` — agregar caso que compara el saldo de un contacto con movimientos de Compras/Impuestos antes y después de que exista la rama nueva del `UNION` (confirma que el `ALTER VIEW` de T005 no alteró ramas existentes, SC-003).

### Implementation for User Story 3

- [X] T023 [US3] Confirmar/ajustar `calcular_estado` (T012) para que la detección de `ya_reconocido` considere también el override vigente de 022 sobre el origen automático (no solo el `IdContacto` crudo de la tabla de origen) — mismo criterio que usa `vw_MovimientosCuenta_Base` con su `OUTER APPLY`.
- [X] T024 [US3] En `MovimientosPorMedio.tsx`/`ConciliarMovimiento.tsx`, cuando `estadoConciliacion` es `ya_reconocido`, no ofrecer la acción de conciliar — en su lugar, mostrar un link a la cuenta corriente del contacto ya asignado (mismo patrón de `OrigenMovimiento.tsx`) para corregirlo desde ahí vía 022 si hace falta.
- [X] T025 [US3] Verificar manualmente (quickstart.md, Escenario 3) que un `POST` directo contra un movimiento `ya_reconocido` responde `409`, no solo que la UI oculta el botón.

**Checkpoint**: MVP real completo — US1 + US3 juntas cubren "conciliar sin poder duplicar", que es el mínimo seguro para producción.

---

## Phase 5: User Story 2 - Repartir un movimiento entre varios contactos (Priority: P2)

**Goal**: repartir el importe de un movimiento entre varios contactos, de forma incremental (una parte ahora, el resto después).

**Independent Test**: sobre uno de los 75 movimientos de Mercado Libre sin contacto en `WC` real, conciliar la mitad a un contacto, confirmar que queda "parcialmente conciliado", y completar el resto en otra sesión (quickstart.md, Escenario 2).

### Tests for User Story 2

- [X] T026 [P] [US2] Contract test: dos `POST` sucesivos sobre el mismo movimiento (reparto incremental) en `backend/tests/contract/test_conciliacion_tesoreria_api.py` — el primero deja `parcialmente_conciliado` con el saldo pendiente correcto, el segundo lo completa a `conciliado`.
- [X] T027 [P] [US2] Test de repository: `calcular_estado` después de una única conciliación parcial devuelve `parcialmente_conciliado` con `saldoPendiente` = total − parcial (FR-006).

### Implementation for User Story 2

- [X] T028 [US2] Confirmar que `aplicar_conciliacion`/`calcular_estado` (T012/T013, ya insert-only y sin estado mutable) soportan el reparto incremental sin cambios adicionales — si algún supuesto de US1 asumía "una sola conciliación por movimiento", corregirlo acá.
- [X] T029 [US2] En `ConciliarMovimiento.tsx`, agregar el modo "repartir": permitir cargar un importe menor al saldo pendiente, dejando claro que el movimiento queda parcialmente conciliado y se puede retomar después.
- [X] T030 [US2] En `MovimientosPorMedio.tsx`, completar el badge de estado para `parcialmente_conciliado` con el saldo pendiente visible (FR-009, pendiente desde T019).
- [X] T031 [US2] Verificar manualmente (quickstart.md, Escenario 2) que el saldo pendiente persiste correctamente entre sesiones (recargar la página) antes de completar el reparto.

**Checkpoint**: las 3 historias de usuario funcionan de punta a punta, independientemente.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T032 [P] En `frontend/src/components/cuentas-corrientes/OrigenMovimiento.tsx`, agregar el caso `origen.tipo === "conciliacion_tesoreria"` (o el que corresponda del contrato de cuentas corrientes), con el mismo patrón de link que los demás orígenes.
- [X] T033 Ejecutar los 4 escenarios de `quickstart.md` manualmente contra `WC`, incluida la verificación de no regresión.
- [X] T034 Correr `pytest` completo en `backend/` y `tsc --noEmit` en `frontend/` para confirmar que no se rompió nada fuera de este feature.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup. BLOQUEA todas las historias — nadie puede escribir ni leer `ConciliacionesTesoreria` sin T004-T006, ni 022 puede corregir este origen sin T007.
- **User Story 1 (Phase 3)**: depende de Foundational.
- **User Story 3 (Phase 4)**: depende de Foundational y de la lógica base de US1 (`calcular_estado`/`aplicar_conciliacion` de T012/T013) — no puede probarse la guarda de duplicado sin el mecanismo de conciliar ya existiendo.
- **User Story 2 (Phase 5)**: depende de Foundational y de US1 (reutiliza `aplicar_conciliacion` sin cambios estructurales).
- **Polish (Phase 6)**: depende de las 3 historias.

### Parallel Opportunities

- T001/T002 (Setup) en paralelo.
- T007/T008 (extensión de 022) en paralelo con T004-T006 (esquema) — son archivos distintos, aunque T008 solo tiene sentido después de T007.
- Dentro de cada historia, las tareas marcadas [P] (tests, y tareas de archivos distintos) pueden ir en paralelo.

## Implementation Strategy

### MVP real

Setup → Foundational → US1 → US3. Recién ahí el sistema es seguro para producción (conciliar sin poder duplicar). US2 (reparto) es una mejora incremental sobre esa base, no un requisito para el primer despliegue.
