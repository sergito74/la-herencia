---

description: "Task list for 024-traspasos-internos-tesoreria"
---

# Tasks: Traspasos internos de Tesorería

**Input**: Design documents from `specs/024-traspasos-internos-tesoreria/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/traspasos-internos-api.md, quickstart.md

**Tests**: incluidos — mismo criterio que 023 (Principio V, escrituras financieras).

**Organización**: por historia de usuario. US1 y US2 son ambas P1 — el MVP real son las dos juntas (vincular sin poder duplicar resolución no es seguro sin la guarda).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions (de plan.md)

- Backend: `backend/src/features/traspasos_internos_tesoreria/`, `backend/src/features/conciliacion_tesoreria/`, `backend/src/features/tesoreria/`, `backend/scripts/`, `backend/tests/`
- Frontend: `frontend/src/components/tesoreria/`, `frontend/src/services/`

---

## Phase 1: Setup

- [X] T001 Crear `backend/src/features/traspasos_internos_tesoreria/__init__.py`, `repository.py`, `schemas.py`, `router.py` vacíos, mismo patrón que `conciliacion_tesoreria/`.
- [X] T002 [P] Registrar el router nuevo en `backend/src/main.py` (placeholder, sin endpoints aún).

**Checkpoint**: el módulo existe y arranca sin romper el backend.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRÍTICO**: cambio de esquema en `WC` (producción) — T004 requiere confirmar con el usuario si se reusa el backup del mismo día (023) o se toma uno nuevo, antes de ejecutar T005.

- [X] T003 Confirmar con el usuario y documentar el backup verificado de `WC` a usar para este cambio de esquema (Constitution Check del plan.md) — dejar constancia en `backend/scripts/crear_tabla_traspasos_internos_tesoreria.py`.
- [X] T004 En `backend/scripts/crear_tabla_traspasos_internos_tesoreria.py`, escribir el DDL re-corrible (`IF NOT EXISTS`) de `dbo.TraspasosInternosTesoreria` exactamente como en data-model.md: `IdEvento` int identity PK; `MedioA`/`MedioB` varchar(20) con `CHECK` en los 6 medios soportados (sin `tarjetas`, FR-002); `IdMovimientoA`/`IdMovimientoB` bigint; `Accion` varchar(10) con `CHECK (Accion IN ('Vincular', 'Deshacer'))`; `Usuario` varchar; `Fecha` datetime `DEFAULT getdate()`. Sin `ALTER VIEW` — este módulo no toca `vw_MovimientosCuenta_Base` (FR-004, plan.md).
- [X] T005 Ejecutar el script contra `WC` (solo después de T003 confirmado) y verificar que la tabla existe y está vacía.
- [X] T006 [P] En `backend/src/features/traspasos_internos_tesoreria/repository.py`, implementar `vinculo_activo(medio, id_movimiento) -> dict | None`: la fila de mayor `IdEvento` para ese movimiento (como `MedioA`/`IdMovimientoA` o como `MedioB`/`IdMovimientoB`), `None` si no existe o si es `Accion='Deshacer'` (data-model.md, "Vínculo activo de un movimiento").
- [X] T007 En `backend/src/features/tesoreria/estado_resolucion.py` (nuevo archivo), implementar `esta_resuelto(medio, id_movimiento) -> str`: llama primero a `conciliacion_tesoreria.repository.calcular_estado` (si devuelve `ya_reconocido`/`conciliado`/`parcialmente_conciliado`, ese es el resultado) y, si devuelve `sin_conciliar`, resuelve el vínculo activo con el mismo `SELECT` de data-model.md ("Vínculo activo de un movimiento") **inlineado directamente acá** (no importando `traspasos_internos_tesoreria.repository`) — si hay uno con `Accion='Vincular'` como más reciente, el resultado es `traspaso_interno`; si no, `sin_conciliar` (data-model.md, "Estado unificado", 5 valores). Evita a propósito un import de `traspasos_internos_tesoreria` acá: ese módulo sí necesita llamar a `esta_resuelto` (T026), y una dependencia circular entre ambos (aunque funcione con import diferido) es un acoplamiento evitable — remediación I1 de `/speckit-analyze`.
- [X] T008 [P] En `backend/src/features/tesoreria/router.py`, reemplazar la llamada a `conciliacion_repository.calcular_estado` en `list_movimientos` por `estado_resolucion.esta_resuelto`, manteniendo el mismo manejo defensivo (`try/except ValueError` → `None`) ya agregado en 023.
- [X] T009 [P] Test de repository: `esta_resuelto` devuelve `traspaso_interno` cuando `calcular_estado` es `sin_conciliar` y hay un vínculo activo, en `backend/tests/test_traspasos_internos_tesoreria_repository.py`.

**Checkpoint**: el estado unificado de 5 valores existe y el listado de Tesorería ya lo expone — recién ahora pueden empezar las historias.

---

## Phase 3: User Story 1 - Vincular dos movimientos como un mismo traspaso interno (Priority: P1) 🎯 MVP

**Goal**: desde un movimiento sin resolver, buscar/sugerir y vincular la contraparte, sin ningún efecto contable.

**Independent Test**: vincular ML `IdMovimiento=25` con Galicia `IdMovimiento=2151` (caso real verificado, quickstart.md Escenario 1) y confirmar que ambos quedan `traspaso_interno` sin cambio de saldo alguno.

### Tests for User Story 1

- [X] T010 [P] [US1] Contract test `GET`/`POST` de `traspaso-interno` (candidatas sugeridas, aplicar vínculo, 201) **y `POST /api/tesoreria/tarjetas/movimientos/{id}/traspaso-interno` → 400 (FR-002)** en `backend/tests/contract/test_traspasos_internos_tesoreria_api.py`, mockeando el repository.
- [X] T011 [P] [US1] Test de repository: `vincular(medioA, idA, medioB, idB, usuario)` inserta un evento `Accion='Vincular'` y `vinculo_activo` lo refleja para ambos lados (A y B); y `vincular("bna", 1, "bna", 1, "u")` rechaza con `ValueError` (FR-009, movimiento consigo mismo) — en `backend/tests/test_traspasos_internos_tesoreria_repository.py`.
- [X] T012 [P] [US1] Test de repository: `sugerir_candidatas(medio, id_movimiento)` con ventana ±5 días y tolerancia ±$1 (research.md §3) encuentra la contraparte cuando existe un movimiento de importe/fecha coincidente en otro medio.

### Implementation for User Story 1

- [X] T013 [US1] En `schemas.py`, definir `VincularRequest` (`medioB: str`, `idMovimientoB: int`), `MovimientoReferencia` (medio, idMovimiento, fecha, descripcion, importe) y `EstadoTraspasoInterno` (`vinculado: bool`, `contraparte: MovimientoReferencia | None`, `candidatas: list[MovimientoReferencia]`, `idEvento`, `usuario`, `fecha`) según `contracts/traspasos-internos-api.md`.
- [X] T014 [US1] En `repository.py`, implementar `sugerir_candidatas(medio, id_movimiento)`: resuelve fecha/importe del movimiento (reusando el mapeo de tablas de `conciliacion_tesoreria.repository._MEDIOS`, importado o replicado), busca en los otros 5 medios movimientos con `ABS(DATEDIFF(day, fecha, ?)) <= 5 AND ABS(ABS(importe) - ABS(?)) <= 1` (research.md §3), sin exigir coincidencia de signo.
- [X] T015 [US1] En `repository.py`, implementar `vincular(medioA, idA, medioB, idB, usuario)`: valida medios soportados (rechaza `tarjetas`), `(medioA,idA) != (medioB,idB)` (FR-009), ambos movimientos existen, e inserta el evento `Accion='Vincular'`.
- [X] T016 [US1] En `router.py`, implementar `GET` (candidatas si no vinculado, contraparte si vinculado) y `POST` de `/api/tesoreria/{medio}/movimientos/{id}/traspaso-interno`, con los códigos de error del contrato.
- [X] T017 [US1] Crear `frontend/src/services/traspasosInternosTesoreriaApi.ts`: `fetchEstadoTraspasoInterno`, `postTraspasoInterno`, `deleteTraspasoInterno`.
- [X] T018 [US1] Crear `frontend/src/components/tesoreria/VincularTraspasoInterno.tsx`: muestra candidatas sugeridas (FR-005), permite buscar manualmente por medio+id si no hay sugerencia, pide confirmación explícita (FR-003).
- [X] T019 [US1] Integrar `VincularTraspasoInterno` en `frontend/src/components/tesoreria/MovimientosPorMedio.tsx` (columna/acción, excluir `tarjetas`).
- [X] T020 [US1] En `MovimientosPorMedio.tsx`, agregar el badge `traspaso_interno` al mapeo de estados ya existente (junto a los 4 de 023).
- [X] T021 [US1] Test de integración: tras `vincular`, comparar `dbo.vw_MovimientosCuenta_Base` antes/después (mismo total de filas, mismos saldos) — confirma FR-004/SC-003 (ningún efecto contable), en `backend/tests/test_cuentas_corrientes_saldos.py` o `test_traspasos_internos_tesoreria_repository.py`.
- [X] T021a [US1] Verificación de SC-002 contra `WC` real: correr `sugerir_candidatas` sobre los 24 movimientos de Mercado Libre del patrón "Ingreso de dinero Cuenta Banco de Galicia" (research.md §3) y confirmar que al menos el 90% (≥22 de 24) encuentran la contraparte correcta de Galicia entre las candidatas — dejar el resultado documentado (script en `backend/scripts/` o anotado en este archivo).

**Checkpoint**: se puede vincular el caso real de punta a punta, sin efecto contable.

---

## Phase 4: User Story 2 - Evitar resolver un movimiento por más de una vía a la vez (Priority: P1)

**Goal**: ningún movimiento puede quedar conciliado Y vinculado como traspaso interno a la vez; la validación es simétrica (ambos lados del vínculo).

**Independent Test**: intentar vincular un movimiento ya conciliado (como iniciador y como contraparte elegida) y verificar rechazo en ambos casos; intentar conciliar (023) un movimiento ya vinculado y verificar rechazo.

### Tests for User Story 2

- [X] T022 [P] [US2] Test de repository: `vincular` rechaza si `esta_resuelto(medioA, idA) != "sin_conciliar"`, en `backend/tests/test_traspasos_internos_tesoreria_repository.py`.
- [X] T023 [P] [US2] Test de repository: `vincular` rechaza si `esta_resuelto(medioB, idB) != "sin_conciliar"` (la contraparte) — validación simétrica, Clarifications 2026-09-28.
- [X] T024 [P] [US2] Test de repository: `vincular` rechaza si `medioA/idA` ya tiene un vínculo activo con un tercer movimiento (FR-008) — el mensaje de error debe identificar cuál es esa contraparte actual, para que el usuario sepa que primero tiene que deshacer ese vínculo si quiere reemplazarlo.
- [X] T025 [P] [US2] Test de repository (en `conciliacion_tesoreria`): `aplicar_conciliacion` rechaza un movimiento con `vinculo_activo` de traspaso interno (FR-007), en `backend/tests/test_conciliacion_tesoreria_repository.py`.
- [X] T025a [P] [US2] Test de repository: dos `vincular` sucesivos sobre el mismo `(medioA, idA)` con distinta contraparte (`medioB`) — el segundo debe fallar viendo `esta_resuelto` ya actualizado a `traspaso_interno` (recalculado en el momento de escribir, no el estado que vio el cliente al abrir la pantalla), cubre FR-012.

### Implementation for User Story 2

- [X] T026 [US2] En `traspasos_internos_tesoreria/repository.py`, `vincular` usa `estado_resolucion.esta_resuelto` (import normal a nivel de módulo — con T007 resuelto según I1, `estado_resolucion` no depende de este módulo, no hay ciclo) para validar ambos lados antes del `INSERT` (FR-006).
- [X] T027 [US2] En `conciliacion_tesoreria/repository.py`, `aplicar_conciliacion` rechaza si hay un vínculo activo de traspaso interno para ese movimiento (FR-007) — resuelve esto con el mismo `SELECT` inlineado de data-model.md ("Vínculo activo de un movimiento"), **sin importar** `traspasos_internos_tesoreria.repository` ni `estado_resolucion` (mismo criterio que I1/T007: `conciliacion_tesoreria` es la pieza que las otras dos consultan, nunca al revés — evita un ciclo de 3 módulos: `conciliacion_tesoreria` → `traspasos_internos_tesoreria`/`estado_resolucion` → `conciliacion_tesoreria`).
- [X] T028 [US2] En `MovimientosPorMedio.tsx`/`VincularTraspasoInterno.tsx` y en `ConciliarMovimiento.tsx` (023), no ofrecer la acción contraria cuando el estado ya es `traspaso_interno` o `conciliado`/`ya_reconocido` respectivamente — mismo criterio visual que ya aplica 023 para `ya_reconocido`.
- [X] T029 [US2] Implementar `deshacer(id_evento, usuario)` en `repository.py`: valida que el vínculo sigue activo, inserta el evento `Accion='Deshacer'` (FR-010); `DELETE` en `router.py`.
- [X] T029a [US2] Botón "Deshacer" en `VincularTraspasoInterno.tsx` cuando el movimiento ya está vinculado, con confirmación explícita — movido acá desde Polish (remediación I2 de `/speckit-analyze`: FR-010 es parte del MVP de la Historia 2 P1, no una mejora opcional).
- [X] T030 [US2] Test de repository: deshacer y volver a vincular el mismo par no queda bloqueado por el vínculo viejo (quickstart.md Escenario 3); y ambos eventos (`Vincular` original y `Deshacer`) quedan con `Usuario`/`Fecha` poblados y consultables (FR-013/SC-004).
- [X] T031 [US2] Verificar manualmente contra `WC` (quickstart.md Escenario 2): un `POST` directo de conciliación (023) contra un movimiento con traspaso interno activo responde 409, y viceversa.

**Checkpoint**: MVP real completo — US1 + US2 cubren "vincular sin poder duplicar resolución".

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T033 Ejecutar los 3 escenarios de `quickstart.md` manualmente contra `WC`, incluida la verificación de no regresión de 023.
- [X] T034 Correr `pytest` completo en `backend/` y `tsc --noEmit` en `frontend/` para confirmar que no se rompió nada fuera de este feature.
- [X] T035 Reconstruir (`npm run build`) y reiniciar el frontend de producción (`next start` no tiene hot-reload — ver feedback del usuario, 2026-09-28).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup. BLOQUEA ambas historias — el estado unificado de 5 valores es prerequisito de todo lo demás.
- **User Story 1 (Phase 3)**: depende de Foundational.
- **User Story 2 (Phase 4)**: depende de Foundational y de la lógica base de US1 (`vincular`/`vinculo_activo` de T014-T015) — no puede probarse la guarda simétrica sin el mecanismo de vincular ya existiendo.
- **Polish (Phase 5)**: depende de ambas historias.

### Parallel Opportunities

- T001/T002 (Setup) en paralelo.
- T006/T009 en paralelo con T003-T005 (archivos distintos, aunque T009 depende conceptualmente de T006).
- Dentro de cada historia, tareas marcadas [P] en paralelo.

## Implementation Strategy

### MVP real

Setup → Foundational → US1 → US2. US1 sola no es segura para producción (falta la guarda simétrica de US2, misma prioridad P1) — mismo criterio que 023 con US1+US3.
