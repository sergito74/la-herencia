---

description: "Task list for 022-reasignacion-contacto"
---

# Tasks: Reasignación de contacto en movimientos de cuenta corriente

**Input**: Design documents from `/specs/022-reasignacion-contacto/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: incluidos (Constitución, Principio V; mismo criterio que 004/019/020/021 — tests unitarios con monkeypatch, validación manual contra `WC` real para el flujo completo).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: US1 (reasignar un movimiento puntual, MVP), US2 (detección de candidatos), US3 (consultar historial general)

## Phase 1: Setup

**Purpose**: esquema nuevo compartido por todas las historias.

- [X] T001 Crear `backend/scripts/crear_tablas_reasignacion_contacto.py`: DDL idempotente para `dbo.ReasignacionesContacto` (`IdReasignacion int identity PK`, `Origen varchar(30) NOT NULL`, `IdOrigen bigint NOT NULL`, `IdContactoAnterior int NOT NULL FK→Contactos`, `IdContactoNuevo int NOT NULL FK→Contactos`, `CHECK (IdContactoNuevo <> IdContactoAnterior)` — FR-011, `Motivo nvarchar(500) NULL`, `Usuario nvarchar(100) NOT NULL`, `Fecha datetime2 NOT NULL DEFAULT SYSUTCDATETIME()`) y `dbo.CandidatosDescartados` (`IdDescarte int identity PK`, `Origen varchar(30) NOT NULL`, `IdOrigen bigint NOT NULL`, `IdContactoSugerido int NOT NULL`, `Usuario nvarchar(100) NOT NULL`, `Fecha datetime2 NOT NULL DEFAULT SYSUTCDATETIME()`, índice único `UX_CandidatosDescartados (Origen, IdOrigen, IdContactoSugerido)` — data-model.md)
- [X] T002 Agregar en el mismo script el índice `IX_ReasignacionesContacto_Origen (Origen, IdOrigen, IdReasignacion DESC)` (data-model.md)
- [X] T003 Tomar backup de `WC` (`backups/WC_pre_reasignacion_contacto_<fecha>.bak`) y ejecutar el script contra `WC` real; verificar con `INFORMATION_SCHEMA`/`sys.indexes` que las 2 tablas, sus columnas, el `CHECK` y los índices quedaron creados correctamente (Constitución, Principio II)
- [X] T004 [P] Crear estructura del módulo `backend/src/features/reasignacion_contacto/` (`__init__.py`, `repository.py`, `router.py`, `schemas.py`)
- [X] T005 [P] Registrar `reasignacion_contacto.router` en `backend/src/main.py`

**Checkpoint**: esquema listo, módulo montado — puede arrancar cualquier historia.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: el *override* debe aplicarse en la vista antes de que cualquier reasignación tenga efecto visible en la cuenta corriente (US1 no es demostrable sin esto), y el frontend necesita la clave `(Origen, IdOrigen)` cruda para poder ofrecer el botón "Reasignar" en cualquier movimiento (research.md §4).

- [X] T006 Crear `backend/scripts/aplicar_override_reasignacion_en_vista.py`: `ALTER VIEW dbo.vw_MovimientosCuenta_Base` envolviendo el `UNION ALL` existente (sin modificar ninguna rama) en una subconsulta `base`, agregando `OUTER APPLY` a `dbo.ReasignacionesContacto` (`TOP 1 ... ORDER BY IdReasignacion DESC` por `(Origen, IdOrigen)`) + `LEFT JOIN dbo.Contactos` para el contacto nuevo, y `COALESCE` en `IdContacto`/`[Razon Social]` de salida (research.md §3) — reutilizar el cuerpo actual del script `agregar_tarjetas_a_vista_cuenta_corriente.py` como base para no reescribir las ramas
- [X] T007 Tomar backup de `WC` (`backups/WC_pre_override_reasignacion_vista_<fecha>.bak`) y ejecutar T006 contra `WC` real; verificar que una consulta de control (`SELECT TOP 5 * FROM vw_MovimientosCuenta_Base WHERE Origen IN ('Galicia','Banco Nacion','Tarjetas')`) sigue devolviendo los mismos resultados que antes del cambio (sin ninguna fila en `ReasignacionesContacto` todavía, el `COALESCE` no debe alterar nada)
- [X] T008 [P] `backend/tests/test_reasignacion_contacto_vista.py`: test de integración contra `WC` real (mismo criterio que `test_cuentas_corrientes_saldos.py`) que inserta una fila de prueba en `ReasignacionesContacto` para un `(Origen, IdOrigen)` real conocido, verifica que `vw_MovimientosCuenta_Base` refleja el contacto nuevo, y la borra al final (no debe quedar dato de prueba permanente)
- [X] T009 [US-transversal] Exponer `origenTipo`/`idOrigen` crudos (los valores reales de `vw_MovimientosCuenta_Base.Origen`/`IdOrigen`) como campos adicionales de `MovimientoCuentaCorriente` en `backend/src/features/cuentas_corrientes/repository.py`/`schemas.py`, sin quitar el objeto `origen` ya resuelto (research.md §4) — actualizar `frontend/src/services/cuentasCorrientesApi.ts` con los dos campos nuevos
- [X] T009a [P] Test en `backend/tests/test_cuentas_corrientes_saldos.py` (o archivo de movimientos existente): `listar_movimientos` incluye `origenTipo`/`idOrigen` sin alterar el resto de la forma de respuesta ya cubierta por 004

**Checkpoint**: la vista aplica el override de forma transparente y el frontend tiene la clave que necesita — US1 puede implementarse.

---

## Phase 3: User Story 1 - Corregir un movimiento puntual desde la cuenta corriente (Priority: P1) 🎯 MVP

**Goal**: reasignar un movimiento visible en la cuenta corriente de un proveedor a otro contacto, con confirmación explícita y trazabilidad completa.

**Independent Test**: sobre el caso real ya conocido (o uno de prueba equivalente), reasignar vía API y verificar que el movimiento pasa del saldo de un proveedor al del otro, con el registro correspondiente en `ReasignacionesContacto`.

### Tests for User Story 1

- [X] T010 [P] [US1] `test_reasignar_inserta_fila_con_contacto_anterior_y_nuevo` en `backend/tests/test_reasignacion_contacto_repository.py` (monkeypatch, sin escribir en `WC` real)
- [X] T011 [P] [US1] `test_reasignar_rechaza_si_contacto_nuevo_es_igual_al_efectivo_actual` (FR-011) — cubrir el caso de que ya exista una reasignación previa vigente, no solo el contacto original
- [X] T012 [P] [US1] `test_reasignar_rechaza_origen_no_soportado` (FR-007) — mensaje exacto `"El origen '{origen}' todavía no admite reasignación."`
- [X] T013 [P] [US1] `test_listar_historial_de_un_movimiento_devuelve_todas_las_reasignaciones_no_solo_la_ultima` (FR-013)
- [X] T014 [P] [US1] Tests de endpoints en `backend/tests/test_reasignacion_contacto_endpoints.py`: `POST /api/reasignacion-contacto/reasignar` (201/409/400/404) y `GET /api/reasignacion-contacto/historial` (con y sin filtro `origen`/`idOrigen`) — mockeados sobre `repository`
- [X] T014a [P] [US1] `test_reasignar_vinculo_tarjeta_no_modifica_compras` (FR-014, remediación E1 de `/speckit-analyze`): con monkeypatch sobre `execute_write_transaction`/`fetch_one`, verificar que ninguna sentencia SQL generada por `reasignar(origen='Tarjetas', ...)` referencia la tabla `Compras` — solo debe escribir en `ReasignacionesContacto`
- [X] T014b [P] [US1] `test_reasignar_concurrente_conserva_ambas_reasignaciones` (FR-012, remediación E2 de `/speckit-analyze`): simular dos llamadas a `reasignar()` sobre el mismo `(Origen, IdOrigen)` (dos inserts sucesivos con distinto `idContactoNuevo`) y verificar que ambas filas quedan en `ReasignacionesContacto` y que `_contacto_efectivo` devuelve la de mayor `IdReasignacion`, no la primera

### Implementation for User Story 1

- [X] T015 [US1] Implementar `_contacto_efectivo(origen, idOrigen) -> int` en `repository.py`: última fila vigente de `ReasignacionesContacto` para ese `(Origen, IdOrigen)`, o el contacto original de la tabla de origen si no hay ninguna (usado por FR-011)
- [X] T016 [US1] Implementar `reasignar(origen, idOrigen, idContactoNuevo, usuario, motivo=None)` en `repository.py`: valida `origen` contra la lista soportada (`{'Galicia', 'Banco Nacion', 'Tarjetas'}`, FR-007), valida `idContactoNuevo != contacto_efectivo` (FR-011), inserta en `ReasignacionesContacto`
- [X] T017 [US1] Implementar `listar_historial(origen=None, idOrigen=None)` en `repository.py`
- [X] T018 [US1] Schemas Pydantic (`ReasignarRequest`, `Reasignacion`, `HistorialResponse`) en `schemas.py` según `contracts/api.md`
- [X] T019 [US1] Endpoints `POST /api/reasignacion-contacto/reasignar` y `GET /api/reasignacion-contacto/historial` en `router.py`, registrados en `src/main.py`
- [X] T020 [US1] Crear `frontend/src/services/reasignacionContactoApi.ts` con los tipos y funciones `reasignarMovimiento`, `fetchHistorial`
- [X] T021 [US1] Crear `frontend/src/components/cuentas-corrientes/ReasignarMovimientoButton.tsx` (botón "Reasignar" + buscador de contacto + confirmación explícita, reutilizando el patrón de búsqueda de contacto ya existente en `CuentaCorriente.tsx`) e integrarlo como columna/acción en la tabla de movimientos de `CuentaCorriente.tsx`, usando los campos `origenTipo`/`idOrigen` de T009
- [X] T022 [US1] Manejar en el frontend el caso "origen sin soporte" (FR-007, 400): deshabilitar o explicar el botón "Reasignar" cuando `origenTipo` no está en la lista soportada, en vez de dejar que falle el POST

**Validar contra `WC` real (con backup previo)**: ejecutar Escenarios 1-4 de `quickstart.md` (reasignación bancaria, rechazo de mismo contacto, origen sin soporte, reasignación de vínculo de tarjeta sin tocar la Compra — FR-014) y documentar resultado.

**Checkpoint**: el flujo completo de reasignar y consultar el historial de un movimiento funciona de punta a punta, en contexto, desde la cuenta corriente del proveedor.

---

## Phase 4: User Story 2 - Detectar sistemáticamente otros movimientos mal asignados (Priority: P2)

**Goal**: sugerir candidatos a reasignación sobre movimientos bancarios, sin escribir nunca por sí sola, descartando el ruido de términos genéricos ya demostrado.

**Independent Test**: ejecutar la detección sobre `WC` real y verificar que devuelve el caso ya conocido (o su equivalente si ya fue corregido) sin los ~35 falsos positivos de términos bancarios genéricos.

### Tests for User Story 2

- [X] T023 [P] [US2] `test_detectar_candidatos_excluye_terminos_de_ruido_bancario` en `test_reasignacion_contacto_repository.py`: usando la lista de términos de research.md §5 (`BANCO, GALICIA, NACION, ARGENTINA, BOLIVAR, BBVA, CREDICOOP, SOCIEDAD, ANONIMA, RESPONSABILIDAD, LIMITADA, COMPANIA, SRL, SA`), verificar que un contacto cuyo nombre se reduce a únicamente esos términos NO genera candidato
- [X] T024 [P] [US2] `test_detectar_candidatos_encuentra_el_caso_real_encode` — reproducir el caso real (contacto "Encode S.A." mencionado en el texto de un movimiento asignado a otro contacto) como fixture y verificar que aparece como candidato
- [X] T025 [P] [US2] `test_detectar_candidatos_excluye_ya_descartados` (FR-010)
- [X] T026 [P] [US2] `test_detectar_candidatos_excluye_si_contacto_sugerido_ya_es_el_efectivo` (considerando el override de US1 vigente, no solo el contacto original de la tabla de origen)
- [X] T027 [P] [US2] `test_descartar_candidato_es_idempotente` (descartar dos veces el mismo candidato no falla ni duplica)
- [X] T028 [P] [US2] Tests de endpoints: `GET /api/reasignacion-contacto/candidatos` y `POST /api/reasignacion-contacto/candidatos/descartar` (mockeados)

### Implementation for User Story 2

- [X] T029 [US2] Definir la constante `TERMINOS_DE_RUIDO` (lista de research.md §5) en `repository.py`
- [X] T030 [US2] Implementar `detectar_candidatos()` en `repository.py`: para cada movimiento de `Movimientos Galicia`/`Movimientos BNA` con contacto asignado, comparar palabras (>3 letras, excluyendo `TERMINOS_DE_RUIDO`) del nombre de otros contactos contra el texto de la descripción del movimiento (mismo algoritmo validado manualmente), excluyendo candidatos ya en `CandidatosDescartados` y los que ya coinciden con el contacto efectivo actual (usando `_contacto_efectivo` de T015)
- [X] T031 [US2] Implementar `descartar_candidato(origen, idOrigen, idContactoSugerido, usuario)` en `repository.py` (`INSERT` idempotente — ignorar si ya existe, no fallar)
- [X] T032 [US2] Schemas (`Candidato`, `CandidatosResponse`, `DescartarCandidatoRequest`) en `schemas.py`
- [X] T033 [US2] Endpoints `GET /api/reasignacion-contacto/candidatos` y `POST /api/reasignacion-contacto/candidatos/descartar` en `router.py`
- [X] T034 [US2] Crear `frontend/src/components/reasignacion-contacto/CandidatosReasignacion.tsx`: lista de candidatos con acción "Reasignar" (reutilizando `ReasignarMovimientoButton.tsx` de US1, pre-cargado con el contacto sugerido) y acción "Descartar"
- [X] T035 [US2] Crear página `frontend/src/app/finanzas/reasignacion-contacto/page.tsx` con la sección de candidatos, y su link de entrada desde el área de Finanzas

**Validar contra `WC` real**: ejecutar Escenarios 5-6 de `quickstart.md` (detección sin falsos positivos conocidos, descarte idempotente).

**Checkpoint**: US1 y US2 funcionan juntas — un candidato detectado se puede confirmar (pasa a Historia 1) o descartar, sin que la detección misma escriba nada.

---

## Phase 5: User Story 3 - Consultar el historial de reasignaciones (Priority: P3)

**Goal**: ver todas las reasignaciones aplicadas alguna vez, no solo las de un movimiento puntual.

**Independent Test**: con al menos una reasignación aplicada (de US1), consultar el historial general y verificar que aparece con movimiento afectado, contacto anterior, contacto nuevo, usuario y fecha.

### Tests for User Story 3

- [X] T036 [P] [US3] `test_listar_historial_sin_filtro_devuelve_todas_las_reasignaciones_ordenadas_por_fecha` en `test_reasignacion_contacto_repository.py` (ya cubierto en parte por T013/T017 de US1 — este test agrega el caso sin filtro, con más de un `(Origen, IdOrigen)` distinto)

### Implementation for User Story 3

- [X] T037 [US3] Agregar a `CandidatosReasignacion.tsx`/`page.tsx` (o un componente separado `HistorialReasignaciones.tsx`) una sección que liste `fetchHistorial()` sin filtro, con columnas: fecha, origen, movimiento, contacto anterior → contacto nuevo, usuario, motivo

**Checkpoint**: las 3 historias funcionan de forma independiente y en conjunto — reasignar, detectar/descartar, y auditar.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T038 [P] Ejecutar los 6 escenarios de `quickstart.md` contra datos reales de `WC` (con backup verificado) de punta a punta y documentar resultado
- [X] T039 Ejecutar `pytest backend/tests/test_reasignacion_contacto_*.py backend/tests/test_cuentas_corrientes_saldos.py backend/tests/test_compras_particular.py` y confirmar 100% en verde (los dos últimos, para confirmar que el `ALTER VIEW` de T006/T007 no rompió nada de 004/021)
- [X] T040 [P] Revisar formato de números y convenciones de UX (memoria `feedback_formato_numeros`) en las pantallas nuevas — `formatMoneda`, nunca `type=number`/`toLocaleString`
- [X] T041 Agregar el link de entrada a `/finanzas/reasignacion-contacto` en la home (`frontend/src/app/page.tsx`, tarjeta "Finanzas")
- [X] T042 `tsc --noEmit` y `eslint` sobre los archivos nuevos/modificados del frontend

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA US1 (sin el `ALTER VIEW` de T006/T007, una reasignación no se refleja en ninguna cuenta corriente) y también beneficia a US2 (mismo `_contacto_efectivo` de T015, que en realidad se implementa dentro de US1 pero es prerrequisito lógico de T026 de US2).
- **User Stories (Phase 3-5)**: todas dependen de Foundational. US2 depende de que `repository._contacto_efectivo` (T015, US1) exista para excluir candidatos ya resueltos — implementar US1 antes. US3 reutiliza `listar_historial` (T017, US1) sin filtro — implementar US1 antes.
- **Polish (Phase 6)**: depende de que las historias que se vayan a entregar estén completas.

### Parallel Opportunities

- T004/T005 (Setup) en paralelo con T001-T003 una vez decidido el esquema.
- Todos los tests marcados [P] de una misma historia en paralelo entre sí, antes de su implementación.
- T008/T009a (Foundational) en paralelo entre sí.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Setup + Foundational (esquema, `ALTER VIEW`, exposición de `origenTipo`/`idOrigen`).
2. US1 — demostrable: reasignar el caso real conocido (o uno equivalente) vía API/UI y ver el cambio reflejado en ambas cuentas corrientes.
3. **Parar y validar** con el usuario el resultado contra el caso real antes de construir la detección (US2) y el historial general (US3).

### Incremental Delivery

1. Setup + Foundational → esquema y vista con override listos.
2. US1 → reasignación puntual funcionando (backend + botón en cuenta corriente).
3. US2 → detección de candidatos + descarte.
4. US3 → historial general.
5. Polish → validación contra `quickstart.md` con datos reales, confirmar que 004/021 siguen sin regresiones.
